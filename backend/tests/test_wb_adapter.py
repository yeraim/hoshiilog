"""Unit tests for the Wildberries adapter's pure parsing helpers and the shared
query/similarity logic. No network access.
"""

import pytest

from backend.app.infrastructure.marketplace_adapters import base, wb
from backend.app.presentation.schemas.crawler import ProductInfo


def test_extract_nm_from_catalog_url() -> None:
    url = "https://www.wildberries.ru/catalog/159206280/detail.aspx"
    assert wb._extract_nm(url) == "159206280"


def test_extract_nm_raises_on_bad_url() -> None:
    with pytest.raises(base.AdapterError):
        wb._extract_nm("https://www.wildberries.ru/brands/nike")


def test_extract_products_handles_top_level_and_nested() -> None:
    # v18: products at the top level.
    assert wb._extract_products({"products": [{"id": 1}], "total": 1}) == [{"id": 1}]
    # legacy: nested under data.
    assert wb._extract_products({"data": {"products": [{"id": 2}]}}) == [{"id": 2}]
    # empty / missing.
    assert wb._extract_products({"data": {}}) == []
    assert wb._extract_products({}) == []


def test_price_from_sizes_converts_kopeks_and_takes_min() -> None:
    sizes = [
        {"price": {"basic": 1000000, "product": 999000}},  # 9990.0
        {"price": {"basic": 1200000, "product": 800000}},  # 8000.0 (min)
    ]
    assert wb._price_from_sizes(sizes) == 8000.0


def test_price_from_sizes_none_when_absent() -> None:
    assert wb._price_from_sizes([{"price": {}}]) is None
    assert wb._price_from_sizes([]) is None


def test_image_url_pattern() -> None:
    nm = 159206280
    url = wb._image_url(nm, wb._guess_shard(nm))
    assert url.startswith("https://basket-")
    assert "wbbasket.ru/vol1592/part159206/159206280/images/big/1.webp" in url


def test_product_from_search_json_maps_fields() -> None:
    item = {
        "id": 12345678,
        "name": "Кроссовки беговые",
        "brand": "Nike",
        "sizes": [{"price": {"product": 500000}}],
    }
    product = wb._product_from_search_json(item)
    assert product.marketplace == "wb"
    assert product.external_id == "12345678"
    assert product.title == "Кроссовки беговые"
    assert product.brand == "Nike"
    assert product.price == 5000.0
    assert product.currency == "RUB"
    assert product.raw == item  # raw retained internally


def test_build_search_query_strips_noise_and_prepends_brand() -> None:
    product = ProductInfo(
        marketplace="wb",
        url="https://www.wildberries.ru/catalog/1/detail.aspx",
        title="Набор для кухни с ножами 3 шт оригинал",
        brand="Tefal",
    )
    query = base.build_search_query(product)
    tokens = query.split()
    assert tokens[0] == "Tefal"  # brand anchors the query
    # Noise words dropped.
    for noise in ("для", "с", "шт", "набор", "оригинал"):
        assert noise not in tokens


def test_rank_matches_filters_below_threshold_and_sorts() -> None:
    def p(title: str) -> ProductInfo:
        return ProductInfo(
            marketplace="wb",
            url="https://www.wildberries.ru/catalog/1/detail.aspx",
            title=title,
        )

    source_title = "Nike Air Zoom Pegasus кроссовки"
    candidates = [
        p("Nike Air Zoom Pegasus кроссовки беговые"),  # very similar
        p("Nike Air Zoom Pegasus"),  # similar
        p("Стиральная машина Bosch"),  # unrelated -> dropped
    ]
    ranked = base.rank_matches(source_title, candidates, limit=5)
    assert len(ranked) == 2
    assert "Bosch" not in " ".join(r.title for r in ranked)
