"""Command-line entry point: python -m scraper --out books.xlsx"""

from __future__ import annotations

import argparse
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .export import export
from .fetch import Fetcher
from .parse import parse_book, parse_listing

BASE_URL = "https://books.toscrape.com/catalogue/page-1.html"
log = logging.getLogger("scraper")


def collect_links(fetcher: Fetcher, start_url: str, max_pages: int | None) -> list[str]:
    links: list[str] = []
    url: str | None = start_url
    page = 0
    while url and (max_pages is None or page < max_pages):
        found, url = parse_listing(fetcher.get(url), url)
        links.extend(found)
        page += 1
        log.info("Listing page %d: %d books (total %d)", page, len(found), len(links))
    return links


def scrape(start_url: str, max_pages: int | None, workers: int, delay: float) -> list[dict]:
    fetcher = Fetcher(delay=delay)
    links = collect_links(fetcher, start_url, max_pages)

    rows: list[dict] = []
    failed: list[str] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetcher.get, link): link for link in links}
        for i, fut in enumerate(as_completed(futures), start=1):
            link = futures[fut]
            try:
                rows.append(parse_book(fut.result(), link).to_dict())
            except Exception as exc:  # keep going; report failures at the end
                failed.append(link)
                log.warning("Failed %s: %s", link, exc)
            if i % 50 == 0:
                log.info("Parsed %d/%d", i, len(links))

    if failed:
        log.warning("%d pages failed, see warnings above", len(failed))
    # as_completed returns in arbitrary order; keep output stable.
    order = {link: i for i, link in enumerate(links)}
    rows.sort(key=lambda r: order[r["url"]])
    return rows


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Scrape books.toscrape.com into CSV, JSON or Excel.")
    p.add_argument("--out", type=Path, default=Path("output/books.xlsx"),
                   help="output file; format is taken from the extension (.csv, .json, .xlsx)")
    p.add_argument("--start-url", default=BASE_URL,
                   help="listing page to start from, e.g. a category page")
    p.add_argument("--max-pages", type=int, default=None, help="stop after N listing pages")
    p.add_argument("--workers", type=int, default=8, help="parallel downloads")
    p.add_argument("--delay", type=float, default=0.1, help="minimum seconds between requests")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")

    rows = scrape(args.start_url, args.max_pages, args.workers, args.delay)
    path = export(rows, args.out)
    log.info("Saved %d books to %s", len(rows), path)
    return 0 if rows else 1


if __name__ == "__main__":
    sys.exit(main())
