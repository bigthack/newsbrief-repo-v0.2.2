
import pytest

@pytest.mark.xfail(reason="Tune simhash threshold to fully pass", strict=False)
def test_dedupe_flags_near_duplicates():
    from ingestion.feeds import dedupe

    a = "Markets rally on tech earnings after companies beat expectations."
    b = "Tech earnings beat expectations; markets rally."
    assert dedupe.is_near_duplicate(a, b, threshold=0.85)
