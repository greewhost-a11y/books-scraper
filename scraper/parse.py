"""HTML parsing for books.toscrape.com. Pure functions, no network access."""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from urllib.parse import urljoin

from bs4 import BeautifulSoup

RATING_WORDS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
_PRICE_RE = re.compile(r"([^\d\s.,]*)\s*([\d.,]+)")
_STOCK_RE = re.compile(r"\((\d+) available\)")


@dataclass
class Book:
    title: str
    price: float
    currency: str
    in_stock: int
    rating: int
    category: str
    upc: str
    description: str
    image_url: str
    url: str

    def to_dict(self) -> dict:
        return asdict(self)


def parse_price(text: str) -> tuple[float, str]:
    """'£51.77' -> (51.77, '£')."""
    m = _PRICE_RE.search(text.strip())
    if not m:
        raise ValueError(f"Cannot parse price from {text!r}")
    return float(m.group(2).replace(",", "")), m.group(1)


def parse_rating(tag) -> int:
    if tag is None:
        return 0
    for cls in tag.get("class", []):
        if cls in RATING_WORDS:
            return RATING_WORDS[cls]
    return 0


def parse_listing(html: str, page_url: str) -> tuple[list[str], str | None]:
    """Return absolute product URLs on a listing page and the next page URL (or None)."""
    soup = BeautifulSoup(html, "lxml")
    links = [
        urljoin(page_url, a["href"])
        for a in soup.select("article.product_pod h3 a[href]")
    ]
    nxt = soup.select_one("li.next a[href]")
    return links, urljoin(page_url, nxt["href"]) if nxt else None


def parse_book(html: str, url: str) -> Book:
    soup = BeautifulSoup(html, "lxml")
    main = soup.select_one("div.product_main")
    if main is None:
        raise ValueError(f"Not a product page: {url}")

    price, currency = parse_price(main.select_one("p.price_color").get_text())

    stock_text = main.select_one("p.availability").get_text(" ", strip=True)
    stock_match = _STOCK_RE.search(stock_text)
    in_stock = int(stock_match.group(1)) if stock_match else 0

    crumbs = [li.get_text(strip=True) for li in soup.select("ul.breadcrumb li")]
    category = crumbs[-2] if len(crumbs) >= 2 else ""

    table = {
        row.th.get_text(strip=True): row.td.get_text(strip=True)
        for row in soup.select("table.table tr")
        if row.th and row.td
    }

    desc_tag = soup.select_one("#product_description + p")
    img = soup.select_one("#product_gallery img[src]")

    return Book(
        title=main.h1.get_text(strip=True),
        price=price,
        currency=currency,
        in_stock=in_stock,
        rating=parse_rating(main.select_one("p.star-rating")),
        category=category,
        upc=table.get("UPC", ""),
        description=desc_tag.get_text(strip=True) if desc_tag else "",
        image_url=urljoin(url, img["src"]) if img else "",
        url=url,
    )
