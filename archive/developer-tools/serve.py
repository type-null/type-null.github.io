#!/usr/bin/env python3
"""Rebuild content and serve it locally: python scripts/serve.py [--port 8000]."""
import argparse
import functools
import http.server
from pathlib import Path

from build import build


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    build(root, root / '_site', check=True)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root / '_site'))
    with http.server.ThreadingHTTPServer(('127.0.0.1', args.port), handler) as server:
        print(f'Preview: http://127.0.0.1:{args.port} (run again after editing content)')
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
