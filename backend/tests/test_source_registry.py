"""
Test Source Registry and Seeding
"""
from backend.app.database import init_db
from backend.app.engines.source_registry import seed_source_registry, get_all_sources

def test_registry():
    init_db()
    seed_source_registry()
    sources = get_all_sources()
    print(f"Total registered sources: {len(sources)}")
    assert len(sources) > 0, "Source registry should not be empty"
    for s in sources[:5]:
        print(f" - [{s['country']}] {s['name']} -> {s['default_category']}")
    print("Source Registry Verification PASSED!")

if __name__ == "__main__":
    test_registry()
