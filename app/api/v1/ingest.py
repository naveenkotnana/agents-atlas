"""Document Ingestion & Knowledge Base Management Endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from app.core.database import get_db
from app.models.db_models import Document, DocumentChunk
from app.models.schema import DocumentIngestRequest, DocumentResponse
from app.services.ingestion import ingestion_service

router = APIRouter(prefix="/documents", tags=["Knowledge Ingestion"])


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def ingest_document(
    payload: DocumentIngestRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Ingest a new enterprise document.
    Executes recursive chunking, dense vectorization, and inverted index updates.
    """
    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="Document content cannot be empty.")

    doc, chunk_count = await ingestion_service.ingest_document(
        db=db,
        title=payload.title,
        content=payload.content,
        source_type=payload.source_type,
        source_uri=payload.source_uri,
        metadata=payload.metadata
    )

    return DocumentResponse(
        id=doc.id,
        title=doc.title,
        source_type=doc.source_type,
        source_uri=doc.source_uri,
        chunk_count=chunk_count,
        created_at=doc.created_at,
        metadata=doc.metadata_ or {}
    )


@router.get("", response_model=List[DocumentResponse])
async def list_documents(db: AsyncSession = Depends(get_db)):
    """List all ingested documents in the enterprise knowledge base."""
    query = select(Document).order_by(Document.created_at.desc())
    res = await db.execute(query)
    docs = res.scalars().all()

    response = []
    for d in docs:
        c_query = select(DocumentChunk).where(DocumentChunk.document_id == d.id)
        c_res = await db.execute(c_query)
        chunks = c_res.scalars().all()
        response.append(DocumentResponse(
            id=d.id,
            title=d.title,
            source_type=d.source_type,
            source_uri=d.source_uri,
            chunk_count=len(chunks),
            created_at=d.created_at,
            metadata=d.metadata_ or {}
        ))
    return response


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(document_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a document and cascade remove all its indexed chunks."""
    query = select(Document).where(Document.id == document_id)
    res = await db.execute(query)
    doc = res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    await db.delete(doc)
    await db.commit()
    return None
