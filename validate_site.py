"""Check corrected public pages and snapshot integrity; no network or sending."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.links, self.ids = [], set()
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.add(attrs['id'])
        if tag == 'a':
            self.links.append(attrs.get('href', ''))


def main():
    pages = [ROOT / 'index.html', *sorted((ROOT / 'sample').glob('*.html'))]
    assert len(pages) == 4
    parsed = {p: Page(p.read_text()) for p in pages}
    prohibited = [
        'Subscribers with a BaltPool alert received',
        'Alert fired this week', '3 t bagged', 'by bag size',
        'Get this every week', 'Buy dataset pack', 'Buy the dataset pack',
        'Subscribe —', '10-year monthly depth', 'One harmonized view',
        'Baltic utility-grade price',
    ]
    for path, page in parsed.items():
        text = path.read_text()
        for phrase in prohibited:
            assert phrase not in text, (path.name, phrase)
        assert 'Dated sample, corrected September 20, 2026.' in text
        assert 'automated subscriber delivery are unavailable' in text
        assert 'Sources and definitions' in text
        for href in page.links:
            parts = urlsplit(href)
            if parts.scheme == 'mailto':
                assert not re.search(r'subscribe|payment|buy|order', unquote(href), re.I)
            if parts.scheme or parts.netloc:
                continue
            target = (path.parent / unquote(parts.path)).resolve() if parts.path else path
            assert target in parsed, (path.name, href)
            if parts.fragment:
                assert parts.fragment in parsed[target].ids, (path.name, href)
    digest = (ROOT / 'sample/sample-digest.html').read_text()
    for value in ['931,315', '$191.61', '€399.74', '€383.40', '€29.46']:
        assert value in digest, value
    assert 'Lithuanian wood-chip SPOT' in digest
    assert 'customs value divided by net weight' in digest
    assert 'metric tonnes' in digest
    snapshot = ROOT / 'snapshot'
    for name, expected in json.loads((snapshot / 'manifest.json').read_text()).items():
        assert hashlib.sha256((snapshot / name).read_bytes()).hexdigest() == expected, name
    print('PASS: four pages, source definitions, historical values, unavailable-service claims, local links, and pinned input hashes.')


if __name__ == '__main__':
    main()
