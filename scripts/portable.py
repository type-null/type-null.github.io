"""Make generated HTML navigable both on GitHub Pages and directly from disk.

Authored URLs stay relative to the site's public root. This final build pass
emits ordinary relative file references, including explicit directory indexes.
Referenced stylesheets are compiled into a separate generated directory so
publishing a local copy never overwrites the author's CSS sources.
"""
from html import escape, unescape
from html.parser import HTMLParser
from pathlib import Path
import posixpath
import re
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit


ATTRIBUTES = re.compile(r'''([^\s=/>]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?''')
CSS_URLS = re.compile(
    r'''/\*.*?\*/|(?:@import\s+)?url\(\s*(?:"(?P<double>[^"]*)"|'(?P<single>[^']*)'|(?P<bare>[^)\s]*))\s*\)|@import\s+(?:"(?P<import_double>[^"]*)"|'(?P<import_single>[^']*)')''',
    re.IGNORECASE | re.DOTALL,
)
URL_ATTRIBUTES = {'href', 'src', 'poster', 'data', 'action', 'formaction', 'xlink:href'}


def srcset_candidates(value):
    """Split candidates without treating a data URL's comma as a separator."""
    cursor = 0
    whitespace = ' \t\n\r\f'
    while cursor < len(value):
        while cursor < len(value) and value[cursor] in whitespace + ',':
            cursor += 1
        start = cursor
        while cursor < len(value) and value[cursor] not in whitespace:
            cursor += 1
        url = value[start:cursor]
        if not url:
            break
        if url.endswith(','):
            yield url.rstrip(','), ''
            continue
        start, parentheses = cursor, 0
        while cursor < len(value):
            char = value[cursor]
            if char == ',' and not parentheses:
                break
            if char == '(':
                parentheses += 1
            elif char == ')':
                parentheses = max(0, parentheses - 1)
            cursor += 1
        yield url, value[start:cursor].strip()
        cursor += 1


class PortableSite:
    def __init__(self, root):
        self.root = Path(root)
        self.stylesheets = {}

    def url(self, value, source, destination=None, *, stylesheet=False):
        """Resolve in the original document, then rebase to its emitted file."""
        parsed = urlsplit(value)
        if parsed.scheme or parsed.netloc or not parsed.path or value.startswith('//'):
            return value
        resolved = urlsplit(urljoin('/' + source.as_posix(), value))
        target = Path(unquote(resolved.path).lstrip('/'))
        if resolved.path.endswith('/') or (self.root / target).is_dir():
            target /= 'index.html'
        if stylesheet and (self.root / target).is_file():
            target = self.stylesheet(target)
        relative = posixpath.relpath(target.as_posix(), (destination or source).parent.as_posix())
        return urlunsplit(('', '', quote(relative, safe="/!$&'()*+,;=:@-._~"), parsed.query, parsed.fragment))

    def css(self, text, source, destination=None):
        def replace(match):
            if match.group().startswith('/*'):
                return match.group()
            value = next(value for value in match.groupdict().values() if value is not None)
            is_import = match.group().lower().startswith('@import')
            stylesheet = is_import or urlsplit(value).path.lower().endswith('.css')
            rewritten = self.url(value, source, destination, stylesheet=stylesheet)
            if rewritten == value:
                return match.group()
            # URL path quotes are percent-encoded; double quotes also cover spaces.
            return ('@import ' if is_import else 'url(') + '"' + rewritten.replace('"', '%22') + '"' + ('' if is_import else ')')
        return CSS_URLS.sub(replace, text)

    def stylesheet(self, source):
        if source not in self.stylesheets:
            target = Path('assets/generated/css') / source
            # Register before following imports, so circular imports terminate.
            self.stylesheets[source] = target
            text = self.css((self.root / source).read_text(encoding='utf-8'), source, target)
            output = self.root / target
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(text, encoding='utf-8')
        return self.stylesheets[source]


class PortableHTML(HTMLParser):
    def __init__(self, site, source, text):
        super().__init__(convert_charrefs=False)
        self.site, self.source = site, source
        self.text = text
        self.line_offsets = [0]
        for line in text.splitlines(keepends=True):
            self.line_offsets.append(self.line_offsets[-1] + len(line))
        self.parts = []
        self.in_style = False

    def start(self, tag, attrs):
        raw = self.get_starttag_text()
        attributes = dict(attrs)
        start = re.match(r'<[^\s/>]+', raw).end()
        def replace(match):
            key = match[1].lower()
            value = next((part for part in match.groups()[1:] if part is not None), None)
            if value is None:
                return match.group()
            value = unescape(value)
            if key in URL_ATTRIBUTES:
                value = self.site.url(value, self.source, stylesheet=(tag == 'link' and key == 'href' and 'stylesheet' in attributes.get('rel', '').lower().split()))
            elif key == 'srcset':
                value = ', '.join((self.site.url(url, self.source) + ' ' + descriptor).rstrip()
                                  for url, descriptor in srcset_candidates(value))
            elif key == 'style':
                value = self.site.css(value, self.source)
            else:
                return match.group()
            return f'{match[1]}="{escape(value, quote=True)}"'
        self.parts.append(raw[:start] + ATTRIBUTES.sub(replace, raw[start:]))
        self.in_style = tag == 'style'

    handle_starttag = start
    handle_startendtag = start

    def handle_endtag(self, tag):
        line, column = self.getpos()
        start = self.line_offsets[line - 1] + column
        self.parts.append(self.text[start:self.text.index('>', start) + 1])
        self.in_style = False

    def handle_data(self, data):
        self.parts.append(self.site.css(data, self.source) if self.in_style else data)

    def handle_entityref(self, name):
        self.parts.append(f'&{name};')

    def handle_charref(self, name):
        self.parts.append(f'&#{name};')

    def handle_comment(self, data):
        self.parts.append(f'<!--{data}-->')

    def handle_decl(self, decl):
        self.parts.append(f'<!{decl}>')

    def handle_pi(self, data):
        self.parts.append(f'<?{data}>')


def make_portable(root):
    site = PortableSite(root)
    for source in sorted(Path(root).rglob('*.html')):
        text = source.read_text(encoding='utf-8')
        parser = PortableHTML(site, source.relative_to(root), text)
        parser.feed(text)
        parser.close()
        source.write_text(''.join(parser.parts), encoding='utf-8')
