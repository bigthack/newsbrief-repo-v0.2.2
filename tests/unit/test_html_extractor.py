
import pathlib
import pytest

@pytest.mark.xfail(reason="Implement extractor.extract_main_text to fully pass", strict=False)
def test_readability_extractor_returns_clean_text():
    from ingestion.feeds import extractor

    html_path = pathlib.Path(__file__).parent.parent / "fixtures" / "html" / "article1.html"
    text = extractor.extract_main_text(html_path.read_text(encoding="utf-8"))
    assert "Stocks jumped" in text
    assert "cookie" not in text.lower()
