import pytest

from backend.app.infrastructure.marketplace_adapters import (
    detect_marketplace,
    get_adapter,
)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.wildberries.ru/catalog/12345678/detail.aspx", "wb"),
        ("https://wildberries.ru/catalog/1/detail.aspx", "wb"),
        ("https://card.wb.ru/cards/v2/detail?nm=1", "wb"),
        ("https://kaspi.kz/shop/p/some-slug-123456/", "kaspi"),
        ("https://www.ozon.ru/product/some-slug-987654/", "ozon"),
        ("https://ozon.ru/product/x-1/", "ozon"),
    ],
)
def test_detect_known_marketplaces(url: str, expected: str) -> None:
    assert detect_marketplace(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/product/1",
        "https://amazon.com/dp/B000",
        "not a url",
        "",
        # A host that merely *contains* a marketplace domain must not match.
        "https://wildberries.ru.evil.com/catalog/1",
    ],
)
def test_detect_unknown_returns_none(url: str) -> None:
    assert detect_marketplace(url) is None


def test_get_adapter_returns_matching_name() -> None:
    for mp in ("wb", "kaspi", "ozon"):
        adapter = get_adapter(mp)
        assert adapter.name == mp
