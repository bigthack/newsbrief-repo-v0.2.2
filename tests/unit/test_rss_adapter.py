
import pathlib
import pytest

@pytest.mark.xfail(reason="Implement GenericRSSAdapter.fetch_feed to fully pass", strict=False)
def test_generic_rss_adapter_parses_items():
    from ingestion.feeds.adapters.generic import GenericRSSAdapter

    rss_path = pathlib.Path(__file__).parent.parent / "fixtures" / "rss" / "bbc.xml"
    items = GenericRSSAdapter().fetch_feed(rss_path.as_uri())
    assert len(items) >= 2
    assert items[0].title
    assert items[0].url.startswith("http")
