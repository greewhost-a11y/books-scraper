import pytest

from scraper.parse import parse_book, parse_listing, parse_price

LISTING_URL = "https://books.toscrape.com/catalogue/page-1.html"
LISTING_HTML = """
<ol>
  <li><article class="product_pod">
    <p class="star-rating Three"></p>
    <h3><a href="a-light-in-the-attic_1000/index.html" title="A Light in the Attic">A Light in the ...</a></h3>
  </article></li>
  <li><article class="product_pod">
    <h3><a href="tipping-the-velvet_999/index.html" title="Tipping the Velvet">Tipping the Velvet</a></h3>
  </article></li>
</ol>
<ul class="pager"><li class="current">Page 1 of 50</li><li class="next"><a href="page-2.html">next</a></li></ul>
"""

BOOK_URL = "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
BOOK_HTML = """
<ul class="breadcrumb">
  <li><a href="../../index.html">Home</a></li>
  <li><a href="../category/books_1/index.html">Books</a></li>
  <li><a href="../category/books/poetry_23/index.html">Poetry</a></li>
  <li class="active">A Light in the Attic</li>
</ul>
<div id="product_gallery"><img src="../../media/cache/fe/72/fe72.jpg" alt=""></div>
<div class="col-sm-6 product_main">
  <h1>A Light in the Attic</h1>
  <p class="price_color">£51.77</p>
  <p class="instock availability"><i class="icon-ok"></i> In stock (22 available)</p>
  <p class="star-rating Three"></p>
</div>
<div id="product_description"><h2>Product Description</h2></div>
<p>It's hard to imagine a world without A Light in the Attic.</p>
<table class="table table-striped">
  <tr><th>UPC</th><td>a897fe39b1053632</td></tr>
  <tr><th>Availability</th><td>In stock (22 available)</td></tr>
</table>
"""


def test_parse_listing_returns_absolute_links_and_next_page():
    links, nxt = parse_listing(LISTING_HTML, LISTING_URL)
    assert links == [
        "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
        "https://books.toscrape.com/catalogue/tipping-the-velvet_999/index.html",
    ]
    assert nxt == "https://books.toscrape.com/catalogue/page-2.html"


def test_parse_listing_last_page_has_no_next():
    html = LISTING_HTML.replace('<li class="next"><a href="page-2.html">next</a></li>', "")
    _, nxt = parse_listing(html, LISTING_URL)
    assert nxt is None


def test_parse_book_extracts_all_fields():
    book = parse_book(BOOK_HTML, BOOK_URL)
    assert book.title == "A Light in the Attic"
    assert book.price == 51.77
    assert book.currency == "£"
    assert book.in_stock == 22
    assert book.rating == 3
    assert book.category == "Poetry"
    assert book.upc == "a897fe39b1053632"
    assert book.description.startswith("It's hard to imagine")
    assert book.image_url == "https://books.toscrape.com/media/cache/fe/72/fe72.jpg"


def test_parse_book_out_of_stock_and_no_rating():
    html = (BOOK_HTML
            .replace("In stock (22 available)", "Out of stock")
            .replace('<p class="star-rating Three"></p>', ""))
    book = parse_book(html, BOOK_URL)
    assert book.in_stock == 0
    assert book.rating == 0


def test_parse_book_rejects_non_product_page():
    with pytest.raises(ValueError):
        parse_book("<html><body>404</body></html>", BOOK_URL)


@pytest.mark.parametrize("text, expected", [
    ("£51.77", (51.77, "£")),
    ("$1,299.00", (1299.0, "$")),
    (" 12.5 ", (12.5, "")),
])
def test_parse_price(text, expected):
    assert parse_price(text) == expected
