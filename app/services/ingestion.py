"""Enterprise Document Ingestion, Recursive Chunking and Vectorization Service."""
import uuid
import re
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.db_models import Document, DocumentChunk
from app.services.ollama_client import ollama_client
from app.core.logging import logger


class DocumentIngestionService:
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 150):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str) -> List[str]:
        """Recursive character chunking respecting paragraph and sentence boundaries."""
        if not text or not text.strip():
            return []

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 <= self.chunk_size:
                current_chunk = (current_chunk + "\n\n" + para).strip()
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                # If paragraph itself is larger than chunk size, split by sentences
                if len(para) > self.chunk_size:
                    sentences = re.split(r"(?<=[.!?]) +", para)
                    sub_chunk = ""
                    for s in sentences:
                        if len(sub_chunk) + len(s) + 1 <= self.chunk_size:
                            sub_chunk = (sub_chunk + " " + s).strip()
                        else:
                            if sub_chunk:
                                chunks.append(sub_chunk)
                            sub_chunk = s
                    if sub_chunk:
                        current_chunk = sub_chunk
                else:
                    current_chunk = para

        if current_chunk:
            chunks.append(current_chunk)

        # Apply overlap between chunks if more than 1 chunk
        overlapped_chunks = []
        for i, c in enumerate(chunks):
            if i > 0 and len(chunks[i - 1]) >= self.chunk_overlap:
                overlap_text = chunks[i - 1][-self.chunk_overlap:]
                c = f"...{overlap_text}\n{c}"
            overlapped_chunks.append(c)

        return overlapped_chunks or [text]

    async def ingest_document(
        self,
        db: AsyncSession,
        title: str,
        content: str,
        source_type: str = "text",
        source_uri: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Document:
        """Ingests a document, creates chunks, computes embeddings, and persists to DB."""
        metadata = metadata or {}
        doc = Document(
            title=title,
            source_type=source_type,
            source_uri=source_uri,
            metadata_=metadata
        )
        db.add(doc)
        await db.flush()

        raw_chunks = self.chunk_text(content)
        for idx, chunk_content in enumerate(raw_chunks):
            # Compute embedding
            embedding = await ollama_client.get_embeddings(chunk_content)
            token_count = len(chunk_content.split())

            chunk = DocumentChunk(
                document_id=doc.id,
                chunk_index=idx,
                content=chunk_content,
                token_count=token_count,
                embedding=embedding,
                metadata_={**metadata, "chunk_index": idx, "document_title": title}
            )
            db.add(chunk)

        doc_id = doc.id or str(uuid.uuid4())
        doc.id = doc_id
        await db.commit()
        logger.info(f"Successfully ingested document '{title}' (ID: {doc_id}) with {len(raw_chunks)} chunks.")
        return doc, len(raw_chunks)

    async def get_all_chunks(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """Fetch all chunks with document titles for hybrid search."""
        query = select(DocumentChunk, Document.title).join(Document, DocumentChunk.document_id == Document.id)
        result = await db.execute(query)
        rows = result.all()

        formatted_chunks = []
        for chunk, doc_title in rows:
            formatted_chunks.append({
                "id": chunk.id,
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "document_title": doc_title,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "embedding": chunk.embedding,
                "metadata": chunk.metadata_ or {}
            })
        return formatted_chunks


ingestion_service = DocumentIngestionService()
