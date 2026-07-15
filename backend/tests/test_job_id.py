from backend.app.infrastructure.crawler_cache import compute_job_id, normalize_url


def test_job_id_is_deterministic_and_16_hex() -> None:
    url = "https://www.wildberries.ru/catalog/12345678/detail.aspx"
    job_id = compute_job_id(url)
    assert job_id == compute_job_id(url)
    assert len(job_id) == 16
    assert all(c in "0123456789abcdef" for c in job_id)


def test_tracking_params_and_case_do_not_change_job_id() -> None:
    """Same product, different tracking noise -> same job_id (free dedup)."""
    base = "https://www.wildberries.ru/catalog/12345678/detail.aspx"
    variants = [
        base,
        base + "?utm_source=telegram&utm_campaign=x",
        base + "/",
        "https://WWW.Wildberries.RU/catalog/12345678/detail.aspx",  # host case
        base + "?from=share_link",
    ]
    ids = {compute_job_id(v) for v in variants}
    assert len(ids) == 1


def test_different_products_get_different_job_ids() -> None:
    a = compute_job_id("https://www.wildberries.ru/catalog/111/detail.aspx")
    b = compute_job_id("https://www.wildberries.ru/catalog/222/detail.aspx")
    assert a != b


def test_meaningful_query_is_preserved() -> None:
    """Non-tracking query params still distinguish URLs."""
    a = normalize_url("https://ozon.ru/search/?text=phone")
    b = normalize_url("https://ozon.ru/search/?text=laptop")
    assert a != b
