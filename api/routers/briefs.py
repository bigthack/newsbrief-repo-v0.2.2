from fastapi import APIRouter
from datetime import date

router = APIRouter()

@router.get("/{day}", summary="Get brief for a date")
def get_brief(day: date):
    return {
        "date": str(day),
        "headline": "Sample Daily Brief",
        "stories": [
            {
                "headline": "Example story",
                "summary": [
                    {"sentence": "A factual sentence about an event.", "source": 1},
                    {"sentence": "Why it matters explained briefly.", "source": 2},
                ],
                "why_it_matters": "Shows how summaries will render.",
                "disputed": "",
                "sources": [
                    {"id": 1, "title": "Source A", "url": "https://example.com/a"},
                    {"id": 2, "title": "Source B", "url": "https://example.com/b"},
                ],
            }
        ],
    }

@router.post("/ingestion/run", summary="Trigger ingestion (admin)")
def run_ingestion():
    return {"status": "queued"}
