"""Bulk Loader: Ingest NovaCore Synthetic Enterprise Dataset directly into Atlas PostgreSQL / Database."""
import asyncio
import csv
from pathlib import Path
from app.core.database import AsyncSessionLocal, init_db
from app.services.ingestion import ingestion_service
from app.core.logging import setup_logging, logger

DATA_DIR = Path("data/novacore")

async def load_and_ingest_novacore(limit_docs: int = 25):
    setup_logging()
    await init_db()

    docs_file = DATA_DIR / "atlas_documents.csv"
    if not docs_file.exists():
        logger.error(f"Documents file {docs_file} not found.")
        return

    print(f"[*] Ingesting top {limit_docs} NovaCore Enterprise documents into Atlas...")

    with open(docs_file, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))

    async with AsyncSessionLocal() as session:
        for idx, row in enumerate(reader[:limit_docs]):
            print(f"  -> Ingesting [{idx+1}/{limit_docs}]: {row['title']} ({row['document_id']})...")
            await ingestion_service.ingest_document(
                db=session,
                title=f"[{row['document_id']}] {row['title']}",
                content=row["full_text"],
                source_type="markdown",
                source_uri=f"enterprise://novacore/{row['department'].lower()}/{row['document_id']}.md",
                metadata={
                    "document_id": row["document_id"],
                    "department": row["department"],
                    "document_type": row["document_type"],
                    "year": int(row["year"]),
                    "quarter": row["quarter"],
                    "region": row["region"],
                    "access_level": row["access_level"],
                    "version": row["version"]
                }
            )

    print("[+] Ingestion complete! Check Atlas Web Dashboard at http://localhost:8000")

if __name__ == "__main__":
    asyncio.run(load_and_ingest_novacore(limit_docs=25))
