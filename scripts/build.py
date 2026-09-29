#!/usr/bin/env python3
"""Build the Markdown site. Usage: python scripts/build.py --check."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re
import shutil
import sys
import tempfile
import time
from urllib.parse import parse_qs, quote, unquote, urljoin, urlsplit
import xml.etree.ElementTree as ET

import jinja2
import markdown
from markupsafe import Markup
from PIL import Image, ImageOps
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from portable import make_portable, srcset_candidates
from post_dates import metadata_dates, publication_date
from publish_root import MANIFEST as ROOT_MANIFEST, PROTECTED as ROOT_PROTECTED, PublishError, plan_sync, read_manifest, sync_root


class BuildError(ValueError):
    """A content error that an author can fix without a Python traceback."""


TEMPLATES = {'article', 'feature', 'gallery', 'tool', 'timeline', 'landing', 'review'}
LEGACY_DIRS = ('card', 'sports', 'resume', 'florida')
MARKER = '.site-build.json'
RESERVED = {Path(name) for name in ('index.html', '404.html', 'posts/index.html', 'feed.xml', 'sitemap.xml', 'search-index.json', 'search-index.js', '.nojekyll', MARKER)}
ARTICLE_TAGS = set('a p h1 h2 h3 h4 h5 h6 div span img picture source table caption th td tbody thead tfoot tr strong em del code pre blockquote ol ul li dl dt dd details summary sup sub br hr figure figcaption kbd samp abbr time mark s small b i u ruby rt rp'.split())
GITHUB_ICON = ('<svg width="22" height="22" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true" focusable="false">'
               '<path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38'
               ' 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13'
               '-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66'
               '.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15'
               '-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.65 7.65 0 0 1 2-.27'
               'c.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12'
               '.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48'
               ' 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8'
               'c0-4.42-3.58-8-8-8Z"/></svg>')


def safe_url(value, *, field='URL', allow_anchor=False):
    if not isinstance(value, str) or not value.strip():
        raise BuildError(f'{field}: expected a non-empty URL')
    value = value.strip()
    decoded = unquote(value)
    parts = urlsplit(value)
    allowed = ('http', 'https', 'mailto', 'tel') if allow_anchor else ('http', 'https')
    if (parts.scheme and parts.scheme.lower() not in allowed) or value.startswith('//'):
        raise BuildError(f'{field}: use an https/http URL or a local path')
    if any(ord(char) < 32 for char in decoded) or '\\' in decoded:
        raise BuildError(f'{field}: control characters and backslashes are not allowed')
    if any(part == '..' for part in unquote(parts.path).split('/')):
        raise BuildError(f'{field}: parent-directory traversal is not allowed')
    if parts.scheme in ('http', 'https') and not parts.netloc:
        raise BuildError(f'{field}: external URL needs a hostname')
    return value


def slug(value):
    value = re.sub(r'[^\w-]+', '-', value.lower(), flags=re.UNICODE).strip('-_')
    if not value:
        raise BuildError('Folder and post names must contain letters or numbers')
    return quote(value, safe='-')


def page_path(url):
    safe_url(url, field='permalink')
    parsed = urlsplit(url)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment or not url.startswith('/'):
        raise BuildError(f'permalink must be a local absolute path: {url}')
    if not url.endswith('/') and not url.endswith('.html'):
        raise BuildError(f'permalink must end in / or .html: {url}')
    path = unquote(parsed.path).lstrip('/')
    if any(part.startswith('.') for part in path.split('/') if part):
        raise BuildError(f'permalink cannot use hidden paths: {url}')
    return Path(path + 'index.html' if url.endswith('/') else path)


def register_route(url, source, destinations):
    target = page_path(url)
    if target.parts[0] in ROOT_PROTECTED | {'assets'} or any(target == other or target in other.parents or other in target.parents for other in (*RESERVED, *destinations)):
        raise BuildError(f'Duplicate or reserved output URL: {url}')
    destinations[target] = source


def load_yaml(path):
    try:
        result = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    except (yaml.YAMLError, OSError) as exc:
        raise BuildError(f'{path}: {exc}') from exc
    if not isinstance(result, dict):
        raise BuildError(f'{path}: expected a YAML mapping')
    return result


class PostLoader(yaml.SafeLoader):
    """Preserve authored timestamps until their fields can validate them.

    PyYAML otherwise normalizes invalid offsets such as +01:99 and silently
    truncates fractional seconds before the date validator sees the input.
    """


PostLoader.add_constructor('tag:yaml.org,2002:timestamp', PostLoader.construct_scalar)


def read_post(path):
    text = path.read_text(encoding='utf-8-sig')
    match = re.match(r'\A---\s*\n(.*?)\n---\s*(?:\n|$)(.*)\Z', text, re.DOTALL)
    if not match:
        raise BuildError(f'{path}: begin with --- YAML front matter --- containing title and date')
    try:
        meta = yaml.load(match.group(1), Loader=PostLoader)
    except yaml.YAMLError as exc:
        raise BuildError(f'{path}: invalid YAML: {exc}') from exc
    if not isinstance(meta, dict):
        raise BuildError(f'{path}: front matter must be a mapping')
    return meta, match.group(2)


def required_text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise BuildError(f'{field}: expected non-empty text')
    return value.strip()


def optional_text(meta, field):
    value = meta.get(field, '')
    if not isinstance(value, str):
        raise BuildError(f'{field}: expected text')
    return value.strip()


def enrich_metadata(post, meta):
    for field in ('subtitle', 'eyebrow', 'author', 'cover_alt', 'cover_caption', 'lang'):
        post[field] = optional_text(meta, field)
    cover_images = meta.get('cover_images', [])
    if not isinstance(cover_images, list) or len(cover_images) > 6:
        raise BuildError('cover_images must be a list of at most 6 image URLs')
    post['cover_images'] = [media_url(value, post, 'cover_images') for value in cover_images]
    for field in ('hero_image', 'hero_mobile_image'):
        value = optional_text(meta, field)
        post[field] = media_url(value, post, field) if value else ''
    if post['lang'] and not re.fullmatch(r'[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*', post['lang']):
        raise BuildError('lang: expected a language tag such as en, ja, or zh-Hans')
    post.update(metadata_dates(meta, dt.date.fromisoformat(post['date'])))
    post['toc'] = meta.get('toc', False)
    if not isinstance(post['toc'], bool):
        raise BuildError('toc must be true or false')
    seo = meta.get('seo', {})
    if not isinstance(seo, dict):
        raise BuildError('seo must be a mapping with optional title, description, and image')
    post['seo'] = {field: optional_text(seo, field) for field in ('title', 'description')}
    seo_image = optional_text(seo, 'image')
    post['seo']['image'] = media_url(seo_image, post, 'seo.image') if seo_image else ''
    for field in ('links', 'facts', 'related'):
        if not isinstance(meta.get(field, []), list):
            raise BuildError(f'{field} must be a list')
    post['links'], post['facts'] = [], []
    for link in meta.get('links', []):
        if not isinstance(link, dict):
            raise BuildError('links: each entry needs label and url')
        style = link.get('style', 'primary')
        if style not in ('primary', 'secondary'):
            raise BuildError('links.style must be primary or secondary')
        post['links'].append({'label': required_text(link.get('label'), 'links.label'), 'url': media_url(link.get('url'), post, 'links.url'), 'style': style})
    for fact in meta.get('facts', []):
        if not isinstance(fact, dict):
            raise BuildError('facts: each entry needs label and value')
        value = fact.get('value')
        if (isinstance(value, int) and not isinstance(value, bool)) or (isinstance(value, float) and math.isfinite(value)):
            value = str(value)
        post['facts'].append({'label': required_text(fact.get('label'), 'facts.label'), 'value': required_text(value, 'facts.value')})
    if any(not isinstance(url, str) for url in meta.get('related', [])):
        raise BuildError('related must contain local post URLs')


def media_url(value, post, field):
    value = safe_url(value, field=field)
    return value if urlsplit(value).scheme or value.startswith('/') else urljoin(post['url'], quote(value, safe='/#?=&:%@+'))


def repository_link(repository, title):
    repository = required_text(repository, 'embed repository')
    match = re.fullmatch(r'https://github\.com/([A-Za-z0-9][A-Za-z0-9-]*)/([A-Za-z0-9_.-]+)/?', repository)
    if not match or match[2] in ('.', '..'):
        raise BuildError('embed repository: use https://github.com/owner/repository')
    label = html.escape(f'View {title} source on GitHub (opens in a new tab)', quote=True)
    return (f'<a class="embed-repository" href="{html.escape(repository, quote=True)}" '
            f'target="_blank" rel="noopener noreferrer" aria-label="{label}" '
            f'title="{label}">{GITHUB_ICON}</a>')


def render_project(embed, post, title):
    """Keep the offline preview local; optionally load a separately hosted app."""
    interactive = embed.get('interactive', False)
    if not isinstance(interactive, bool):
        raise BuildError('project interactive: must be true or false')
    if interactive and 'url' not in embed:
        raise BuildError('project interactive: requires a website URL')
    source = repository_link(embed.get('repository'), title)
    screenshot = media_url(embed.get('image'), post, 'project image')
    if urlsplit(screenshot).scheme:
        raise BuildError('project image: save the screenshot locally')
    destination = embed['repository'].strip()
    opening = ''
    if 'url' in embed:
        try:
            destination = safe_url(embed['url'], field='project URL')
            parts = urlsplit(destination)
            if (parts.scheme != 'https' or not parts.hostname or parts.username or parts.password
                    or any(char.isspace() for char in parts.netloc)):
                raise ValueError('expected an HTTPS website URL without credentials')
            _ = parts.port  # urlsplit defers malformed-port validation.
        except ValueError as exc:
            raise BuildError(f'project URL: {exc}') from exc
        opening = (f'<a class="button button-small embed-open" href="{html.escape(destination, quote=True)}" '
                   f'target="_blank" rel="noopener noreferrer" '
                   f'aria-label="{html.escape(f"Open {title} website in a new tab", quote=True)}">'
                   f'Open website <span aria-hidden="true">↗</span></a>')
    label = f'Open {title} ' + ('website' if opening else 'on GitHub') + ' in a new tab'
    alt = required_text(embed.get('image_alt', f'{title} website preview'), 'project image_alt')
    behavior = f' data-project-url="{html.escape(destination, quote=True)}"' if interactive else ''
    controls = ('<button class="button button-small project-load" type="button" data-project-load hidden>'
                'Use in this article <span aria-hidden="true">↗</span></button>'
                '<button class="button button-small button-outline" type="button" data-project-close hidden>'
                'Close preview</button>') if interactive else ''
    status = ('<p class="project-status" data-project-status role="status" aria-live="polite">'
              'Interactive preview requires an internet connection.</p>') if interactive else ''
    return (f'<figure class="embed embed--project"{behavior}><figcaption class="embed-toolbar">'
            f'<span class="embed-title">{html.escape(title)}</span>'
            f'<span class="embed-actions">{controls}{opening}{source}</span></figcaption>{status}'
            f'<div class="project-stage">'
            f'<a class="project-preview" href="{html.escape(destination, quote=True)}" '
            f'target="_blank" rel="noopener noreferrer" aria-label="{html.escape(label, quote=True)}">'
            f'<img src="{html.escape(screenshot, quote=True)}" alt="{html.escape(alt, quote=True)}" '
            f'loading="lazy" decoding="async"></a></div></figure>')


def render_embed(embed, post):
    if not isinstance(embed, dict):
        raise BuildError('embeds: each entry must be a mapping with type, url, and title')
    kind = embed.get('type')
    if 'repository' in embed and kind not in ('website', 'project'):
        raise BuildError('embed repository: supported only for website and project embeds')
    title = required_text(embed.get('title'), 'embed title')
    if kind == 'project':
        return render_project(embed, post, title)
    url = media_url(embed.get('url'), post, 'embed URL')
    escaped_url, escaped_title = html.escape(url, quote=True), html.escape(title, quote=True)
    if kind == 'youtube':
        parsed = urlsplit(url)
        host = parsed.hostname
        if host == 'youtu.be':
            video_id = parsed.path.strip('/')
        elif host in ('youtube.com', 'www.youtube.com', 'youtube-nocookie.com', 'www.youtube-nocookie.com'):
            video_id = parsed.path.split('/')[-1] if parsed.path.startswith(('/embed/', '/shorts/')) else parse_qs(parsed.query).get('v', [''])[0]
        else:
            raise BuildError('youtube embed: use a youtube.com or youtu.be URL')
        if not re.fullmatch(r'[\w-]{11}', video_id, flags=re.ASCII):
            raise BuildError('youtube embed: invalid video ID')
        element = f'<iframe src="https://www.youtube-nocookie.com/embed/{video_id}" title="{escaped_title}" loading="lazy" allow="fullscreen; picture-in-picture" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>'
    elif kind == 'video':
        poster = f' poster="{html.escape(media_url(embed["poster"], post, "video poster"), quote=True)}"' if embed.get('poster') else ''
        element = f'<video controls preload="metadata"{poster} aria-label="{escaped_title}"><source src="{escaped_url}">Your browser does not support this video.</video>'
    elif kind in ('pdf', 'website'):
        # First-party tools need their normal origin for browser-local records.
        sandbox = ' sandbox="allow-scripts allow-forms allow-popups"' if kind == 'website' and urlsplit(url).scheme else ''
        element = f'<iframe src="{escaped_url}" title="{escaped_title}" loading="lazy" referrerpolicy="no-referrer"{sandbox}></iframe>'
    else:
        raise BuildError(f'Unknown embed type {kind!r}; choose youtube, video, pdf, website, or project')
    if kind == 'website':
        source_link = ''
        if 'repository' in embed:
            source_link = repository_link(embed['repository'], title)
        return (f'<figure class="embed embed--website"><figcaption class="embed-toolbar">'
                f'<span class="embed-title">{escaped_title}</span>'
                f'<span class="embed-actions">'
                f'<a class="button button-small embed-open" href="{escaped_url}" target="_blank" '
                f'rel="noopener noreferrer" aria-label="Open {escaped_title} in a new tab">'
                f'Open in new tab <span aria-hidden="true">↗</span></a>{source_link}</span></figcaption>{element}</figure>')
    return f'<figure class="embed embed--{kind}">{element}<figcaption><a href="{escaped_url}" target="_blank" rel="noopener noreferrer">{escaped_title} ↗</a></figcaption></figure>'


class ContentHTML(HTMLParser):
    """Normalize Markdown links and fail visibly on executable author HTML."""
    def __init__(self, post, route_map, root):
        super().__init__(convert_charrefs=False)
        self.post, self.route_map, self.root, self.parts = post, route_map, root, []

    def handle_starttag(self, tag, attrs):
        if tag not in ARTICLE_TAGS:
            raise BuildError(f'Unsupported raw <{tag}> HTML; use Markdown or front-matter embeds')
        normalized = []
        for key, value in attrs:
            if key.startswith('on') or key in {'srcdoc', 'style', 'srcset'} or ':' in key:
                raise BuildError(f'Unsafe HTML attribute: {key}')
            if key in {'href', 'src', 'poster'} and value:
                parsed = urlsplit(value)
                if key == 'href' and not parsed.scheme and parsed.path.endswith('.md'):
                    target = (self.post['_source'].parent / unquote(parsed.path)).resolve() if not value.startswith('/') else (self.root / 'content' / unquote(parsed.path).lstrip('/')).resolve()
                    if target not in self.route_map:
                        raise BuildError(f'Markdown link points to an unpublished or missing post: {value}')
                    value = self.route_map[target] + (f'#{parsed.fragment}' if parsed.fragment else '')
                else:
                    value = safe_url(value, field=f'{tag} {key}', allow_anchor=(key == 'href'))
                if not urlsplit(value).scheme and not value.startswith(('/', '#')):
                    value = media_url(value, self.post, f'{tag} {key}')
            normalized.append((key, value))
        if tag == 'img':
            if not any(key == 'loading' for key, _ in normalized):
                normalized.append(('loading', 'lazy'))
            normalized.append(('decoding', 'async'))
        self.parts.append('<' + tag + ''.join(f' {key}="{html.escape(value, quote=True)}"' if value is not None else f' {key}' for key, value in normalized) + '>')

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        self.parts.append(f'</{tag}>')

    def handle_data(self, data):
        self.parts.append(data)

    def handle_entityref(self, name):
        self.parts.append(f'&{name};')

    def handle_charref(self, name):
        self.parts.append(f'&#{name};')

    def handle_comment(self, data):
        self.parts.append(f'<!--{data}-->')


def discover(root):
    topics, posts, destinations = [], [], {}
    content = root / 'content'
    if not content.resolve().is_relative_to(root.resolve()):
        raise BuildError(f'{content}: content symlink leaves the repository')
    for directory in sorted(content.iterdir()) if content.exists() else []:
        if not directory.is_dir() or directory.name.startswith(('_', '.')):
            continue
        if not directory.resolve().is_relative_to(content.resolve()):
            raise BuildError(f'{directory}: topic symlink leaves the content folder')
        topic_slug = slug(directory.name)
        config = load_yaml(directory / '_topic.yml') if (directory / '_topic.yml').exists() else {}
        topic = {'slug': topic_slug, 'label': directory.name.replace('-', ' ').replace('_', ' ').title(), 'color': '#489fe6', 'icon': '✦', 'description': '', 'order': 100, 'home_layout': 'gallery', **config, 'url': f'/{topic_slug}/'}
        topic['label'] = required_text(topic['label'], f'{directory}: topic label')
        if topic['home_layout'] not in ('gallery', 'feature', 'journal'):
            raise BuildError(f'{directory}: home_layout must be gallery, feature, or journal')
        if not isinstance(topic['order'], (int, float)):
            raise BuildError(f'{directory}: topic order must be numeric')
        if not isinstance(topic['color'], str) or not re.fullmatch(r'#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?', topic['color']):
            raise BuildError(f'{directory}: topic color must be a hex color')
        topic['slug'], topic['url'] = topic_slug, f'/{topic_slug}/'
        register_route(topic['url'], directory, destinations)
        topics.append(topic)
        for source in sorted(directory.rglob('*.md')):
            if any(part.startswith(('_', '.')) for part in source.relative_to(directory).parts):
                continue
            if source.is_symlink() or not source.resolve().is_relative_to(directory.resolve()):
                raise BuildError(f'{source}: symlink posts are not supported')
            meta, body = read_post(source)
            for flag in ('draft', 'featured', 'unlisted', 'announcement'):
                if flag in meta and not isinstance(meta[flag], bool):
                    raise BuildError(f'{source}: {flag} must be true or false')
            if meta.get('draft'):
                continue
            try:
                title = required_text(meta.get('title'), 'title')
                date = publication_date(meta.get('date'))
                template = meta.get('template', 'article')
                if template not in TEMPLATES:
                    raise BuildError(f'Unknown template {template!r}; choose {", ".join(sorted(TEMPLATES))}')
                relative = source.relative_to(directory).with_suffix('')
                parts = list(relative.parts)
                if parts[-1] == 'index':
                    parts.pop()
                if not parts:
                    raise BuildError('Place topic posts in <post>.md or <post>/index.md; topic/index.md conflicts with the topic landing page')
                url = meta.get('permalink', '/' + '/'.join([topic_slug, *(slug(part) for part in parts)]) + '/')
                register_route(url, source, destinations)
                tags = meta.get('tags', [])
                if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
                    raise BuildError('tags must be a list of text labels')
                post = {**meta, 'title': title, 'url': url, 'topic': topic, 'date': date.isoformat(), 'date_display': date.strftime('%b %d, %Y').replace(' 0', ' '), 'description': str(meta.get('description', '')), 'template': template, 'featured': meta.get('featured', False), 'unlisted': meta.get('unlisted', False), 'tags': tags, 'source': str(source.relative_to(root)), '_source': source, '_body': body, 'reading_time': max(1, math.ceil(len(re.findall(r'\w+', body)) / 200)), 'embeds': meta.get('embeds', []), 'gallery': meta.get('gallery', [])}
                post['cover'] = media_url(meta['cover'], post, 'cover') if meta.get('cover') else '/assets/images/type-null.png'
                enrich_metadata(post, meta)
                if not isinstance(post['embeds'], list) or not isinstance(post['gallery'], list):
                    raise BuildError('embeds and gallery must be lists')
                for item in post['gallery']:
                    if not isinstance(item, dict) or not isinstance(item.get('alt'), str):
                        raise BuildError('gallery entries require src and alt text')
                    item['src'] = media_url(item.get('src'), post, 'gallery src')
                    item.setdefault('caption', '')
                posts.append(post)
            except (BuildError, ValueError, TypeError) as exc:
                raise BuildError(f'{source}: {exc}') from exc
    topics.sort(key=lambda topic: (topic['order'], topic['label']))
    posts.sort(key=lambda post: (post['date'], post['url']), reverse=True)
    route_map = {post['_source'].resolve(): post['url'] for post in posts}
    for post in posts:
        try:
            parser = ContentHTML(post, route_map, root)
            md = markdown.Markdown(extensions=['extra', 'toc', 'sane_lists'], output_format='html')
            parser.feed(md.convert(post['_body']))
            rendered = ''.join(parser.parts)
            embeds = [render_embed(embed, post) for embed in post['embeds']]
            used = set()
            def replace(match):
                index = int(match.group(1)) - 1
                if not 0 <= index < len(embeds):
                    raise BuildError(f'Embed reference {index + 1} does not exist')
                used.add(index)
                return embeds[index]
            rendered = re.sub(r'<p>\[\[embed:(\d+)\]\]</p>', replace, rendered)
            post['html'] = Markup(rendered)
            post['embeds_html'] = Markup('\n'.join(embed for index, embed in enumerate(embeds) if index not in used))
            toc = ContentHTML(post, route_map, root)
            toc.feed(md.toc if post['toc'] else '')
            post['toc_html'] = Markup(''.join(toc.parts))
        except BuildError as exc:
            raise BuildError(f'{post["source"]}: {exc}') from exc
    for topic in topics:
        topic['count'] = sum(post['topic']['slug'] == topic['slug'] and not post['unlisted'] for post in posts)
    by_path = {page_path(post['url']): post for post in posts}
    for post in posts:
        post['related_posts'] = []
        if 'related' in post:
            for url in post['related']:
                try:
                    candidate = by_path.get(page_path(url))
                except BuildError as exc:
                    raise BuildError(f'{post["source"]}: invalid related URL: {exc}') from exc
                if not candidate or candidate['unlisted'] or candidate is post:
                    raise BuildError(f'{post["source"]}: related URL must name another listed, published post: {url}')
                if all(existing['url'] != candidate['url'] for existing in post['related_posts']):
                    post['related_posts'].append(candidate)
        else:
            candidates = [candidate for candidate in posts if candidate is not post and not candidate['unlisted'] and (candidate['topic']['slug'] == post['topic']['slug'] or set(candidate['tags']) & set(post['tags']))]
            candidates.sort(key=lambda candidate: (len(set(candidate['tags']) & set(post['tags'])), candidate['topic']['slug'] == post['topic']['slug'], candidate['date'], candidate['url']), reverse=True)
            post['related_posts'] = candidates[:3]
    return topics, posts


def copy_tree(source, target, root, exclude=()):
    if not source.exists():
        return
    for file in source.rglob('*'):
        if not file.is_file():
            continue
        if file.relative_to(root).as_posix() in exclude:
            continue
        if not file.resolve().is_relative_to(root.resolve()):
            raise BuildError(f'Refusing to copy a symlink outside the repository: {file}')
        destination = target / file.relative_to(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, destination)


def copy_post_media(post, output):
    source = post['_source']
    # Folder posts own their entire media folder; single-file posts share topic media.
    for file in source.parent.rglob('*'):
        relative = file.relative_to(source.parent)
        if not file.is_file() or file.suffix.lower() in ('.md', '.yml', '.yaml') or any(part.startswith(('_', '.')) for part in relative.parts):
            continue
        if any((parent / 'index.md').exists() for parent in file.parents if parent != source.parent and parent.is_relative_to(source.parent)):
            continue
        if not file.resolve().is_relative_to(source.parent.resolve()):
            raise BuildError(f'{source}: media symlink leaves the post folder: {file}')
        target = output / page_path(post['url']).parent / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_bytes() != file.read_bytes():
            raise BuildError(f'{source}: media file collides with another output: {target.relative_to(output)}')
        shutil.copy2(file, target)


def prepare_timeline(root, output):
    source = root / 'content' / '_data' / 'card-sets.json'
    if not source.exists():
        return {'sets': [], 'eras': [], 'years': []}
    try:
        dataset = json.loads(source.read_text(encoding='utf-8'))
    except (ValueError, OSError) as exc:
        raise BuildError(f'{source}: invalid JSON: {exc}') from exc
    if not isinstance(dataset, dict) or not isinstance(dataset.get('sets'), list):
        raise BuildError(f'{source}: expected an object containing a sets list')
    seen = set()
    for item in dataset['sets']:
        if not isinstance(item, dict):
            raise BuildError(f'{source}: each set must be an object')
        identifier = item.get('id')
        if not isinstance(identifier, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', identifier) or identifier in seen:
            raise BuildError(f'{source}: duplicate or invalid set id: {identifier!r}')
        seen.add(identifier)
        image_url = safe_url(item.get('image'), field=f'{source}: image for {identifier}')
        if not image_url.startswith('/assets/'):
            raise BuildError(f'{source}: timeline image must be under /assets/: {image_url}')
        original = root / unquote(image_url).lstrip('/')
        if not original.resolve().is_relative_to((root / 'assets').resolve()) or not original.is_file():
            raise BuildError(f'{source}: missing or unsafe timeline image: {image_url}')
        thumbnail = f'/assets/images/timeline/{identifier}.webp'
        target = output / thumbnail.lstrip('/')
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            with Image.open(original) as image:
                image = ImageOps.exif_transpose(image)
                # Pack scans can sit inside large transparent canvases. Fit the
                # visible artwork into the calendar; keep original files intact.
                if 'A' in image.getbands() or 'transparency' in image.info:
                    image = image.convert('RGBA')
                    bounds = image.getchannel('A').getbbox()
                    if bounds is None:
                        raise ValueError('image contains no visible pixels')
                    if bounds != (0, 0, image.width, image.height):
                        image = image.crop(bounds)
                image.thumbnail((160, 200), Image.Resampling.LANCZOS)
                if image.mode not in ('RGB', 'RGBA'):
                    image = image.convert('RGBA' if 'transparency' in image.info else 'RGB')
                image.save(target, 'WEBP', quality=78, method=4)
                item.update(thumbnail=thumbnail, thumbnailWidth=image.width, thumbnailHeight=image.height)
        except (OSError, ValueError) as exc:
            raise BuildError(f'{source}: cannot generate thumbnail for {image_url}: {exc}') from exc
    target = output / 'assets/data/card-sets.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(dataset, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    return dataset


def prepare_galleries(posts, output):
    """Keep original artwork downloadable while serving small raster previews."""
    for post in posts:
        for item in post['gallery']:
            parsed = urlsplit(item['src'])
            if parsed.scheme:
                continue
            source = output / unquote(parsed.path).lstrip('/')
            if not source.resolve().is_relative_to(output.resolve()) or not source.is_file():
                raise BuildError(f'{post["source"]}: missing or unsafe gallery image: {item["src"]}')
            # SVGs are already resolution independent and need no raster conversion.
            if source.suffix.lower() == '.svg':
                continue
            with source.open('rb') as file:
                digest = hashlib.file_digest(file, 'sha256').hexdigest()[:20]
            thumbnail = f'/assets/images/generated/gallery-{digest}.webp'
            target = output / thumbnail.lstrip('/')
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                if not target.exists():
                    with Image.open(source) as image:
                        image = ImageOps.exif_transpose(image)
                        image.thumbnail((600, 700), Image.Resampling.LANCZOS)
                        if image.mode not in ('RGB', 'RGBA'):
                            image = image.convert('RGBA' if 'transparency' in image.info else 'RGB')
                        image.save(target, 'WEBP', quality=82, method=4)
                with Image.open(target) as image:
                    item.update(thumbnail=thumbnail, thumbnailWidth=image.width, thumbnailHeight=image.height)
            except (OSError, ValueError) as exc:
                raise BuildError(f'{post["source"]}: cannot generate gallery preview for {item["src"]}: {exc}') from exc


class LinkCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ids, self.resources, self.stylesheets = [], set(), [], []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id'):
            self.ids.add(attrs['id'])
        key = {'a': 'href', 'img': 'src', 'script': 'src', 'link': 'href', 'iframe': 'src', 'source': 'src', 'video': 'poster', 'object': 'data'}.get(tag)
        if key and attrs.get(key):
            self.links.append(attrs[key])
        resource_keys = {'img': ('src',), 'script': ('src',), 'iframe': ('src',), 'source': ('src',), 'video': ('src', 'poster'), 'audio': ('src',), 'object': ('data',)}.get(tag, ())
        for key in resource_keys:
            if attrs.get(key):
                self.resources.append(attrs[key])
        if tag == 'link' and set(attrs.get('rel', '').lower().split()) & {'stylesheet', 'icon', 'preload', 'modulepreload', 'prefetch', 'preconnect', 'dns-prefetch'} and attrs.get('href'):
            self.resources.append(attrs['href'])
            if 'stylesheet' in attrs.get('rel', '').lower().split():
                self.stylesheets.append(attrs['href'])
        if tag in ('img', 'source') and attrs.get('srcset'):
            candidates = [url for url, _ in srcset_candidates(attrs['srcset'])]
            self.resources.extend(candidates)
            self.links.extend(candidates)


def check_offline(output, posts):
    """Reject remote runtime resources while retaining normal outbound links."""
    failures, seen_css = [], set()
    def inspect(value, location):
        if value.startswith('//') or urlsplit(value).scheme.lower() in ('http', 'https'):
            failures.append(f'{location}: {value}')
            return False
        return True
    def local_resource(value, base_url):
        parsed = urlsplit(value)
        if parsed.scheme or not parsed.path:
            return None
        path = output / unquote(urlsplit(urljoin(base_url, value)).path).lstrip('/')
        return path if path.resolve().is_relative_to(output.resolve()) else None
    def scan_css(text, base_url):
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
        resources = re.findall(r'url\(\s*[\"\']?([^\)\"\']+)', text, flags=re.IGNORECASE)
        imports = re.findall(r'@import\s+(?:url\(\s*)?[\"\']?([^\"\'\)\s;]+)', text, flags=re.IGNORECASE)
        for resource in set(resources + imports):
            resource = resource.strip()
            if not inspect(resource, base_url):
                continue
            path = local_resource(resource, base_url)
            if path and not path.is_file():
                raise BuildError(f'offline mode: missing local stylesheet resource {resource} in {base_url}')
            if resource in imports:
                scan_stylesheet(resource, base_url)
    def scan_stylesheet(resource, base_url):
        if not inspect(resource, base_url):
            return
        path = local_resource(resource, base_url)
        if path is not None and path.is_file() and path not in seen_css:
            seen_css.add(path)
            scan_css(path.read_text(encoding='utf-8'), '/' + path.relative_to(output).as_posix())
    for post in posts:
        for value in [post['cover'], post['seo'].get('image', ''), post['hero_image'], post['hero_mobile_image'], *post['cover_images'], *(item['src'] for item in post['gallery'])]:
            inspect(value, post['source'])
    for source in output.rglob('*.html'):
        document = LinkCollector()
        text = source.read_text(encoding='utf-8')
        document.feed(text)
        for resource in document.resources:
            inspect(resource, str(source.relative_to(output)))
        base_url = '/' + source.relative_to(output).as_posix()
        for resource in document.stylesheets:
            scan_stylesheet(resource, base_url)
        styles = re.findall(r'<style\b[^>]*>(.*?)</style>', text, flags=re.IGNORECASE | re.DOTALL)
        styles += re.findall(r'\bstyle=[\"\'](.*?)[\"\']', text, flags=re.IGNORECASE | re.DOTALL)
        for style in styles:
            scan_css(style, base_url)
    if failures:
        raise BuildError('offline mode: save media locally or use an outbound Markdown link\n' + '\n'.join(sorted(set(failures))))


def check_links(output, pages):
    documents = {}
    for url in pages:
        file = output / page_path(url)
        parser = LinkCollector()
        parser.feed(file.read_text(encoding='utf-8'))
        documents[url] = parser
    errors, checked = [], 0
    for url, document in documents.items():
        for link in document.links:
            resolved = urlsplit(urljoin(url, link))
            if resolved.scheme or resolved.netloc:
                continue
            checked += 1
            target = output / unquote(resolved.path).lstrip('/')
            if target.is_dir():
                target /= 'index.html'
            if not target.resolve().is_relative_to(output.resolve()) or not target.is_file():
                errors.append(f'{url}: missing local link {link}')
                continue
            if resolved.fragment:
                target_url = resolved.path
                if target_url.endswith('index.html'):
                    target_url = target_url[:-10]
                target_doc = documents.get(target_url)
                if target_doc and unquote(resolved.fragment) not in target_doc.ids:
                    errors.append(f'{url}: missing anchor {link}')
    if errors:
        raise BuildError('Internal link check failed:\n' + '\n'.join(sorted(set(errors))))
    return checked


def write_feeds(site, posts, pages, output):
    rss = ET.Element('rss', version='2.0')
    channel = ET.SubElement(rss, 'channel')
    for key, value in [('title', site['title']), ('link', site['url']), ('description', site['description'])]:
        ET.SubElement(channel, key).text = str(value)
    for post in posts[:30]:
        item = ET.SubElement(channel, 'item')
        for key, value in [('title', post['title']), ('link', site['url'] + post['url']), ('guid', site['url'] + post['url']), ('description', post['description']), ('pubDate', dt.date.fromisoformat(post['date']).strftime('%a, %d %b %Y 00:00:00 GMT'))]:
            ET.SubElement(item, key).text = value
    ET.ElementTree(rss).write(output / 'feed.xml', encoding='utf-8', xml_declaration=True)
    sitemap = ET.Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    revisions = {post['url']: post['updated'] for post in posts}
    for url in sorted(pages):
        if url == '/404.html':
            continue
        entry = ET.SubElement(sitemap, 'url')
        ET.SubElement(entry, 'loc').text = site['url'] + url
        if url in revisions:
            ET.SubElement(entry, 'lastmod').text = revisions[url]
    ET.ElementTree(sitemap).write(output / 'sitemap.xml', encoding='utf-8', xml_declaration=True)
    search = [{key: post[key] for key in ('title', 'url', 'description', 'date', 'created', 'updated', 'tags', 'cover')} | {'topic': post['topic']['label'], 'text': re.sub('<[^>]+>', ' ', str(post['html']))} for post in posts]
    (output / 'search-index.json').write_text(json.dumps(search, ensure_ascii=False), encoding='utf-8')
    (output / 'search-index.js').write_text('window.TYPE_NULL_SEARCH_INDEX = ' + json.dumps(search, ensure_ascii=False).replace('\u2028', '\\u2028').replace('\u2029', '\\u2029') + ';\n', encoding='utf-8')


def build(root, output=None, *, check=False, sync=False):
    started = time.perf_counter()
    root = Path(root).resolve()
    output = Path(output or root / '_site').resolve()
    if output == root or root.is_relative_to(output) or (output.is_relative_to(root) and output.relative_to(root).parts[0] in ('assets', 'content', 'templates', 'scripts', 'tests', 'docs', 'legacy', 'archive', '.git', '.github', '.venv')):
        raise BuildError(f'Refusing unsafe output directory: {output}')
    if output.exists() and (not output.is_dir() or (any(output.iterdir()) and not (output / MARKER).is_file())):
        raise BuildError(f'{output}: output is not empty and was not created by this builder; choose an empty directory')
    site = {'title': 'Type Null', 'url': 'https://type-null.github.io', 'description': 'A personal field guide to cards, games, and everyday discoveries.', 'author': 'Type Null', 'offline': False}
    if (root / 'site.yml').exists():
        site.update(load_yaml(root / 'site.yml'))
    if not isinstance(site['offline'], bool):
        raise BuildError('site.offline must be true or false')
    site['url'] = safe_url(site['url'], field='site.url').rstrip('/')
    site_parts = urlsplit(site['url'])
    if site_parts.scheme not in ('https', 'http') or site_parts.path or site_parts.query or site_parts.fragment:
        raise BuildError('site.url must be an absolute https/http origin without a path, query, or fragment')
    topics, posts = discover(root)
    listed_posts = [post for post in posts if not post['unlisted']]
    unlisted_urls = {post['url'] for post in posts if post['unlisted']}
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(root / 'templates'), autoescape=jinja2.select_autoescape(['html', 'xml']), undefined=jinja2.StrictUndefined)
    env.filters['absolute_url'] = lambda url: urljoin(site['url'] + '/', url)
    env.filters['urlencode'] = lambda value: quote(str(value), safe='')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.site-build-', dir=output.parent) as temporary:
        staging = Path(temporary)
        managed_files = read_manifest(root)['files']
        copy_tree(root / 'assets', staging / 'assets', root, exclude=managed_files)
        generated = {page_path(post['url']) for post in posts}
        legacy = root / 'legacy' if (root / 'legacy').is_dir() else (None if (root / ROOT_MANIFEST).exists() else root)
        for directory in LEGACY_DIRS:
            for source in (legacy / directory).rglob('*.html') if legacy and (legacy / directory).exists() else []:
                if not source.resolve().is_relative_to(root):
                    raise BuildError(f'{source}: legacy symlink leaves the repository')
                relative = source.relative_to(legacy)
                if relative not in generated:
                    target = staging / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
        for post in posts:
            copy_post_media(post, staging)
        prepare_galleries(posts, staging)
        timeline = prepare_timeline(root, staging)
        pages = []
        def render(template, page, selected_posts=listed_posts, post=None):
            url = page['url']
            page = {'description': site['description'], 'cover': '/assets/images/type-null.png', 'cover_images': [], 'hero_image': '', 'hero_mobile_image': '', 'template': template.removesuffix('.html'), 'date': None, 'topic': None, 'unlisted': False, 'seo': {}, 'links': [], 'facts': [], 'related_posts': [], 'lang': site.get('language', 'en'), 'author': '', 'updated': '', 'subtitle': '', 'eyebrow': '', 'cover_alt': '', 'cover_caption': '', 'toc': False, 'toc_html': '', **page}
            page['lang'] = page['lang'] or site.get('language', 'en')
            page['canonical_url'] = site['url'] + url
            page['image_url'] = urljoin(site['url'] + '/', page['cover'])
            page['seo_title'] = page['seo'].get('title') or page['title']
            page['seo_description'] = page['seo'].get('description') or page['description']
            page['seo_image_url'] = urljoin(site['url'] + '/', page['seo'].get('image') or page['cover'])
            target = staging / page_path(url)
            if target.exists():
                raise BuildError(f'{url}: generated page collides with a media file')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(env.get_template(template).render(site=site, topics=topics, posts=selected_posts, all_posts=listed_posts, featured_posts=[post for post in listed_posts if post['featured']], page=page, post=post, timeline=timeline), encoding='utf-8')
            pages.append(url)
        render('home.html', {'title': 'Home', 'url': '/'})
        render('archive.html', {'title': 'NEWS', 'url': '/posts/', 'description': 'All articles, projects, and field notes.'})
        for topic in topics:
            render('topic.html', {'title': topic['label'], 'url': topic['url'], 'topic': topic, 'description': topic['description']}, [post for post in listed_posts if post['topic']['slug'] == topic['slug']])
        for post in posts:
            template = f'{post["template"]}.html' if post['template'] in ('timeline', 'landing', 'review') else 'article.html'
            if post['template'] in ('landing', 'review') and not (root / 'templates' / template).is_file():
                template = 'article.html'
            render(template, post, post=post)
        render('404.html', {'title': 'Page not found', 'url': '/404.html'})
        write_feeds(site, listed_posts, [url for url in pages if url not in unlisted_urls], staging)
        (staging / '.nojekyll').touch()
        (staging / MARKER).write_text(json.dumps({'generator': 'type-null', 'pages': len(pages)}), encoding='utf-8')
        make_portable(staging)
        if site['offline']:
            check_offline(staging, posts)
        checked = check_links(staging, pages) if check or sync else 0
        if sync:
            plan_sync(root, staging)
        if output.exists():
            shutil.rmtree(output)
        staging.replace(output)
    mirror = sync_root(root, output) if sync else None
    summary = {'pages': len(pages), 'posts': len(posts), 'listed_posts': len(listed_posts), 'unlisted_posts': len(unlisted_urls), 'topics': len(topics), 'checked_links': checked, 'seconds': round(time.perf_counter() - started, 2), 'output': str(output)}
    if mirror is not None:
        summary['mirror'] = mirror
    print(f'Built {summary["pages"]} pages ({summary["posts"]} posts: {summary["listed_posts"]} listed, {summary["unlisted_posts"]} unlisted; {summary["topics"]} topics) in {summary["seconds"]}s → {output}' + (f'; checked {checked} local references' if check or sync else '') + ('; root pages synchronized' if sync else ''))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Output directory (default: _site); must be empty or a previous build')
    parser.add_argument('--check', action='store_true', help='Fail on broken generated local links, assets, and anchors')
    args = parser.parse_args()
    try:
        build(Path(__file__).resolve().parents[1], args.output, check=args.check, sync=args.output is None)
    except (BuildError, PublishError, jinja2.TemplateError) as exc:
        parser.exit(1, f'Build failed: {exc}\n')


if __name__ == '__main__':
    main()
