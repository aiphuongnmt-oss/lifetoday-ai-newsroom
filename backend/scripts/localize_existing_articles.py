"""
Localize & Fix Foreign Articles in Database (Batch Mode)
"""
from backend.app.database import get_db_connection
from backend.app.engines.translator import translate_headline_rule_based
from backend.app.engines.fact_checker import verify_facts_and_compliance

def localize_articles():
    conn = get_db_connection()
    sources = {s["id"]: s["reliability_score"] for s in conn.execute("SELECT id, reliability_score FROM sources").fetchall()}
    rows = conn.execute("SELECT id, title, summary, source_id, language, status, hard_block_reason FROM articles WHERE language != 'vi'").fetchall()
    data = [dict(r) for r in rows]
    conn.close()

    print(f"Loaded {len(data)} foreign articles into memory...")

    updates = []
    for r in data:
        title = r["title"]
        if not title.startswith("[Dịch]") and not title.startswith("[Quốc tế]"):
            vi_title = translate_headline_rule_based(title)
            if vi_title != title:
                new_title = f"[Dịch] {vi_title}"
            else:
                new_title = f"[Quốc tế] {title}"
        else:
            new_title = title

        rel = sources.get(r["source_id"], 0.95)
        fact_status, fact_meta = verify_facts_and_compliance(new_title, r["summary"] or "", rel)
        new_status = r["status"]
        new_reason = r["hard_block_reason"]

        if r["status"] == "HOLD" and "độ tin cậy trung bình" in (r["hard_block_reason"] or ""):
            if fact_status == "VERIFIED":
                new_status = "NEW"
                new_reason = ""

        updates.append((new_title, new_status, new_reason, r["id"]))

    conn = get_db_connection()
    conn.executemany("UPDATE articles SET title = ?, status = ?, hard_block_reason = ? WHERE id = ?", updates)
    conn.commit()
    conn.close()
    print(f"Successfully updated {len(updates)} articles in database!")

if __name__ == "__main__":
    localize_articles()
