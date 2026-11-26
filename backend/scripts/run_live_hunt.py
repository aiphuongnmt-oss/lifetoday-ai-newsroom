"""
Live News Hunter & Full Pipeline Execution Script
"""
import asyncio
from backend.app.database import init_db, get_db_connection
from backend.app.engines.source_registry import seed_source_registry
from backend.app.engines.hunter import run_news_hunter
from backend.app.engines.automation_worker import run_pipeline_for_article

async def main():
    print("=" * 60)
    print("EXECUTING LIVE NEWS HUNT & PIPELINE")
    print("=" * 60)
    init_db()
    seed_source_registry()

    # 1. Run live hunt
    print("Step 1: Hunting news from all active sources...")
    hunt_res = await run_news_hunter()
    print(f"Sources scanned: {hunt_res['sources_scanned']}")
    print(f"New articles found: {hunt_res['new_articles_count']}")

    # 2. Process through pipeline
    articles = hunt_res.get("articles", [])
    print(f"\nStep 2: Processing {len(articles)} articles through 12-step pipeline...")
    processed_count = 0
    held_count = 0
    rejected_count = 0

    for idx, art in enumerate(articles):
        print(f"\nProcessing [{idx+1}/{len(articles)}]: {art['title'][:60]}...")
        res = await run_pipeline_for_article(art["id"])
        if res.get("success"):
            processed_count += 1
            print(f" -> SUCCESS: Created Post #{res['post_id']} (Slot: {res.get('scheduling', {}).get('slot', 'N/A')})")
        else:
            if res.get("step") == "HARD_BLOCK":
                held_count += 1
                print(f" -> HARD BLOCK (HOLD): {res.get('reason')}")
            elif res.get("step") == "DEDUPLICATION":
                rejected_count += 1
                print(f" -> DUPLICATE (REJECTED): {res.get('reason')}")
            else:
                print(f" -> {res.get('step', 'FAILED')}: {res.get('reason', res.get('error'))}")

    print("\n" + "=" * 60)
    print("SUMMARY OF LIVE RUN:")
    print(f"- Total new articles hunted: {len(articles)}")
    print(f"- Successfully processed & scheduled: {processed_count}")
    print(f"- Held by Hard Block / Fact Check: {held_count}")
    print(f"- Rejected by Deduplication: {rejected_count}")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
