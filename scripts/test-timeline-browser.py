#!/usr/bin/env python3
"""Verify the artwork calendar against the built site, including mobile and no-JS.

Build first: python scripts/build.py --check
Run: python scripts/test-timeline-browser.py --output /tmp/timeline-qa
Install requirements-dev.txt and `python -m playwright install chromium` first.
Set PLAYWRIGHT_CHROMIUM_EXECUTABLE to use an existing browser installation.
"""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import tempfile
import threading
from urllib.parse import unquote, urljoin

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def copyfile(self, source, outputfile):
        try:
            super().copyfile(source, outputfile)
        except (BrokenPipeError, ConnectionResetError):
            pass  # Navigation can cancel in-flight lazy image requests.


def wait_for_visible_art(page):
    page.wait_for_function('''() => {
        const images = Array.from(document.querySelectorAll('.timeline-chart .set-art img'));
        const visible = images.filter(image => {
            const rect = image.getBoundingClientRect();
            return rect.width && rect.height && rect.bottom > 0 && rect.top < innerHeight && rect.right > 0 && rect.left < innerWidth;
        });
        return visible.length && visible.every(image => image.complete && image.naturalWidth > 0);
    }''')


def measure_pack_scale(page):
    ids = ['2025-06-sv-sv11b', '2025-06-sv-sv11w',
           '2025-08-m-m1l', '2025-08-m-m1s', '2025-09-m-m2', '2025-11-m-m2a']
    packs = page.evaluate('''async ids => {
        const images = ids.map(id => document.querySelector(`[data-set-id="${id}"] img`));
        // Mobile's horizontal calendar can leave these real releases lazy.
        images.forEach(image => { image.loading = 'eager'; });
        await Promise.all(images.map(image => image.decode()));
        return Object.fromEntries(images.map((image, index) => {
            const box = image.getBoundingClientRect();
            const scale = Math.min(box.width / image.naturalWidth, box.height / image.naturalHeight);
            return [ids[index], {naturalWidth: image.naturalWidth, naturalHeight: image.naturalHeight,
                containedHeight: scale * image.naturalHeight}];
        }));
    }''', ids)
    june = max(packs[identifier]['containedHeight'] for identifier in ids[:2])
    august = min(packs[identifier]['containedHeight'] for identifier in ids[2:4])
    september = packs[ids[4]]['containedHeight']
    november = packs[ids[5]]['containedHeight']
    ratios = {'august_to_june': august / june, 'september_to_november': september / november}
    assert ratios['august_to_june'] >= .9, f'August paired artwork is undersized: {packs}'
    assert ratios['september_to_november'] >= .9, f'September artwork is undersized: {packs}'
    return {'packs': packs, **ratios}


def run_checks(url, output, executable):
    data = json.loads((ROOT / 'content/_data/card-sets.json').read_text())
    sets = data['sets']
    total = len(sets)
    years = sorted({item['year'] for item in sets})
    mega = [item for item in sets if item['era'] == 'M']
    scarlet = [item for item in sets if item['era'] == 'SV']
    year_2024 = [item for item in sets if item['year'] == 2024]
    black_white = [item for item in sets if item['era'] == 'BW']
    site_root = urljoin(url, '../../../')

    def asset_url(path):
        return unquote(urljoin(site_root, path.lstrip('/')))

    def status(items):
        count = len(items)
        count_years = len({item['year'] for item in items})
        text = f"{count} {'set' if count == 1 else 'sets'} · {count_years} {'year' if count_years == 1 else 'years'}"
        return text + (f' · {total} total' if count != total else '')

    results = {}
    with sync_playwright() as runtime:
        options = {'headless': True}
        if executable:
            options['executable_path'] = executable
        browser = runtime.chromium.launch(**options)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000}, device_scale_factor=1)
        errors, requests = [], []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('request', lambda request: requests.append(request.url))
        page.goto(url, wait_until='networkidle')
        expect(page.locator('h1')).to_have_text('Pokémon Card Set Timeline')
        expect(page.locator('#timeline-status')).to_have_text(status(sets))
        assert page.locator('.timeline-chart tbody tr').count() == len(years)
        assert page.locator('.set-art:visible').count() == total
        assert page.locator('.set-art img').count() == total
        assert page.locator('.set-art img:not([loading=lazy])').count() == 0
        assert page.locator('.set-art img').evaluate_all('(images)=>images.every(image=>image.src.includes("/images/timeline/") && image.width > 0 && image.height > 0)')
        # Resolve emitted relative URLs in the browser; keep the same original
        # artwork target for every set after making the build portable.
        artwork_targets = page.locator('.set-art').evaluate_all('(links)=>Object.fromEntries(links.map(link=>[link.dataset.setId,link.href]))')
        assert {key: unquote(value) for key, value in artwork_targets.items()} == {item['id']: asset_url(item['image']) for item in sets}
        assert page.locator('script[type=module]').count() == 0
        assert page.locator('.set-art').evaluate_all('(links)=>links.every(link=>!link.textContent.trim())')
        assert page.locator('[data-view], .timeline-views, .set-pill-code, [data-dialog-code]').count() == 0
        assert not any('/set-package-jp/' in request for request in requests)
        wait_for_visible_art(page)
        results['initial'] = {'requests': len(requests), 'artwork_elements': total, 'year_rows': len(years),
            'thumbnail_requests': sum('/images/timeline/' in request for request in requests),
            **page.evaluate('''({width:document.documentElement.scrollWidth,viewport:innerWidth,
                chartHeight:document.querySelector('.timeline-chart').clientHeight,
                chartScrollHeight:document.querySelector('.timeline-chart').scrollHeight,
                tableHeight:document.querySelector('.timeline-chart table').clientHeight,
                resourceTransferBytes:performance.getEntriesByType('resource').reduce((sum,r)=>sum+r.transferSize,0),
                documentTransferBytes:performance.getEntriesByType('navigation')[0].transferSize,
                domContentLoadedMs:performance.getEntriesByType('navigation')[0].domContentLoadedEventEnd,
                chartTop:Math.round(document.querySelector('.timeline-chart').getBoundingClientRect().top)})''')}
        assert abs(results['initial']['chartHeight'] - results['initial']['chartScrollHeight']) <= 1
        assert results['initial']['chartHeight'] > len(years) * 90
        # Exercise real lazy scrolling before capturing the entire long calendar.
        for index in list(range(0, len(years), 7)) + [len(years) - 1]:
            page.locator('.timeline-chart tbody tr').nth(index).evaluate('(element)=>element.scrollIntoView({block:"center",behavior:"instant"})')
            wait_for_visible_art(page)
        page.wait_for_function('Array.from(document.querySelectorAll(".set-art img")).every(image=>image.complete&&image.naturalWidth>0)')
        results['all_artwork_decoded'] = total
        results['pack_scale'] = {'desktop': measure_pack_scale(page)}
        page.evaluate('window.scrollTo({top:0,behavior:"instant"})')
        page.screenshot(path=str(output / 'artwork-desktop.png'), full_page=True)

        # Every artwork in a crowded real month remains within its cell, side by side.
        triple = page.locator('.timeline-chart [data-year="2019"] td[data-month="4"]')
        assert triple.locator('.set-art').count() >= 3
        triple.evaluate('(element)=>element.scrollIntoView({block:"center",behavior:"instant"})')
        wait_for_visible_art(page)
        geometry = triple.evaluate('''cell => {
            const bounds = cell.getBoundingClientRect();
            return {cell:{left:bounds.left,right:bounds.right}, images:Array.from(cell.querySelectorAll('img')).map(image => {
                const rect=image.getBoundingClientRect(); return {left:rect.left,right:rect.right,top:rect.top,bottom:rect.bottom,width:rect.width,height:rect.height};
            })};
        }''')
        assert all(image['left'] >= geometry['cell']['left'] and image['right'] <= geometry['cell']['right'] for image in geometry['images'])
        assert all(left['right'] <= right['left'] for left, right in zip(geometry['images'], geometry['images'][1:]))
        assert min(image['width'] for image in geometry['images']) >= 24
        results['triple_cell'] = geometry
        expect(page.locator('.timeline-floating-months')).to_be_visible()
        page.screenshot(path=str(output / 'three-packs-desktop.png'))

        page.locator('select[name=era]').select_option('M')
        expect(page.locator('#timeline-status')).to_have_text(status(mega))
        expect(page.locator('.set-art:visible')).to_have_count(len(mega))
        assert page.locator('.set-art img').count() == total
        page.locator('select[name=era]').select_option('SV')
        expect(page.locator('.set-art:visible')).to_have_count(len(scarlet))
        page.go_back()
        expect(page.locator('select[name=era]')).to_have_value('M')
        expect(page.locator('.set-art:visible')).to_have_count(len(mega))
        page.locator('.timeline-reset').click()
        page.locator('select[name="from"]').select_option('2024')
        page.locator('select[name="to"]').select_option('2024')
        expect(page.locator('#timeline-status')).to_have_text(status(year_2024))
        january = page.locator('.timeline-chart [data-year="2024"] td[data-month="1"]')
        assert january.locator('.set-art:visible').count() >= 2
        page.locator('.timeline-reset').click()
        search = page.locator('input[name=q]')
        search.fill('ワイルドフォース')
        expect(page.locator('.set-art:visible')).to_have_count(1)
        page.locator('.set-art:visible').click()
        expect(page.locator('[data-set-dialog]')).to_be_visible()
        expect(page.locator('#timeline-dialog-title')).to_have_text('ワイルドフォース')
        selected_set = next(item for item in sets if item['name'] == 'ワイルドフォース')
        assert unquote(page.locator('[data-dialog-art] img').evaluate('(image)=>image.src')) == asset_url(selected_set['image'])
        assert page.locator('[data-dialog-code]').count() == 0
        page.wait_for_function('document.querySelector("[data-dialog-art] img").naturalWidth > 0')
        page.screenshot(path=str(output / 'set-detail.png'))
        page.keyboard.press('Escape')
        expect(page.locator('[data-set-dialog]')).not_to_be_visible()
        # Native dialog.close queues its close event after clearing `open`.
        expect(page.locator('.set-art:visible')).to_be_focused()
        expect(page.locator('[data-dialog-art] img')).to_have_count(0)
        search.fill('zzzz-not-a-set')
        expect(page.locator('[data-timeline-empty]')).to_be_visible()
        page.locator('[data-reset-filters]').click()
        expect(search).to_be_focused()
        expect(page.locator('.set-art:visible')).to_have_count(total)
        search.fill('Black ')
        page.wait_for_timeout(250)
        expect(search).to_have_value('Black ')
        page.keyboard.type('& White')
        expect(page.locator('.set-art:visible')).to_have_count(len(black_white))
        page.locator('.timeline-reset').click()
        search.focus()
        search.dispatch_event('compositionstart')
        search.evaluate('(element)=>{element.value="ワイルドフォース";element.dispatchEvent(new InputEvent("input",{bubbles:true,isComposing:true}));}')
        page.wait_for_timeout(250)
        expect(page.locator('.set-art:visible')).to_have_count(total)
        search.dispatch_event('compositionend')
        expect(page.locator('.set-art:visible')).to_have_count(1)

        # Printing restores the complete illustrated archive even after filtering.
        page.evaluate('window.dispatchEvent(new Event("beforeprint"))')
        page.emulate_media(media='print')
        assert page.locator('.timeline-chart tbody tr:visible').count() == len(years)
        assert page.locator('.set-art img:visible').count() == total
        page.wait_for_function('Array.from(document.querySelectorAll(".set-art img")).every(image=>image.complete&&image.naturalWidth>0)')
        page.emulate_media(media='screen')
        page.evaluate('window.dispatchEvent(new Event("afterprint"))')
        for view in ('overview', 'list', 'artwork', 'broken'):
            page.goto(url + '?view=' + view, wait_until='networkidle')
            assert page.locator('.set-art img:visible').count() == total
        page.goto(url + '?era=notreal&from=oops&to=9999&q=%3Cscript%3E', wait_until='networkidle')
        expect(page.locator('[data-timeline-empty]')).to_be_visible()
        expect(page.locator('select[name=era]')).to_have_value('')
        expect(page.locator('select[name="from"]')).to_have_value(str(years[0]))
        expect(page.locator('select[name="to"]')).to_have_value(str(years[-1]))

        # Test mobile from a fresh visit, preserving the artwork calendar as default.
        mobile = browser.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=1)
        mobile.on('pageerror', lambda error: errors.append(str(error)))
        mobile.goto(url, wait_until='networkidle')
        wait_for_visible_art(mobile)
        assert mobile.locator('.set-art img:visible').count() == total
        results['mobile'] = mobile.evaluate('''({width:document.documentElement.scrollWidth,viewport:innerWidth,
            chartWidth:document.querySelector('.timeline-chart').clientWidth,
            tableWidth:document.querySelector('.timeline-chart table').clientWidth,
            chartHeight:document.querySelector('.timeline-chart').clientHeight,
            chartScrollHeight:document.querySelector('.timeline-chart').scrollHeight})''')
        assert results['mobile']['width'] <= 390
        assert abs(results['mobile']['chartHeight'] - results['mobile']['chartScrollHeight']) <= 1
        mobile.screenshot(path=str(output / 'artwork-mobile.png'))
        results['pack_scale']['mobile'] = measure_pack_scale(mobile)
        mobile.locator('.timeline-chart [data-year="2019"]').evaluate('(element)=>element.scrollIntoView({block:"center",behavior:"instant"})')
        mobile.locator('.timeline-chart').evaluate('(element)=>element.scrollLeft=element.scrollWidth')
        expect(mobile.locator('.timeline-floating-months')).to_be_visible()
        sticky = mobile.locator('.timeline-chart [data-year="2019"] th').bounding_box()
        chart = mobile.locator('.timeline-chart').bounding_box()
        assert abs(sticky['x'] - chart['x']) <= 2
        wait_for_visible_art(mobile)
        mobile.screenshot(path=str(output / 'months-mobile.png'))

        nojs = browser.new_context(java_script_enabled=False, viewport={'width':1280,'height':900})
        nojs_page = nojs.new_page()
        nojs_page.goto(url, wait_until='networkidle')
        assert nojs_page.locator('.set-art img').count() == total
        assert nojs_page.locator('.set-art').evaluate_all('(links)=>links.every(link=>!link.textContent.trim())')
        assert nojs_page.locator('.timeline-filters').is_hidden()
        wait_for_visible_art(nojs_page)
        results['nojs'] = {'artwork_elements':total, 'year_rows':nojs_page.locator('.timeline-chart tbody tr').count()}
        results['page_errors'] = errors
        assert not errors, errors
        browser.close()
    results['checks'] = 'passed'
    (output / 'results.json').write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))
    print('Screenshots:', output)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', help='An existing preview origin; starts a local server if omitted')
    parser.add_argument('--output', type=Path, help='Screenshot and measurement directory (default: a temporary directory)')
    parser.add_argument('--browser', default=os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE'), help='Optional Chromium executable path')
    args = parser.parse_args()
    output = args.output or Path(tempfile.mkdtemp(prefix='type-null-timeline-qa-'))
    output.mkdir(parents=True, exist_ok=True)
    server = None
    try:
        if args.url:
            origin = args.url.rstrip('/')
        else:
            if not (ROOT / '_site/index.html').exists():
                parser.error('Run python scripts/build.py --check first')
            server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT / '_site')))
            threading.Thread(target=server.serve_forever, daemon=True).start()
            origin = f'http://127.0.0.1:{server.server_port}'
        run_checks(origin + '/card/2024/02/timeline.html', output, args.browser)
    finally:
        if server:
            server.shutdown()
            server.server_close()


if __name__ == '__main__':
    main()
