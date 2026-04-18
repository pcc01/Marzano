"""
Haystack RAG pipeline — fully activated.
Indexes Marzano PDFs/docs into a persistent vector store.
Emits SSE notifications on progress so the browser shows a live progress bar.

Embedding: sentence-transformers/all-MiniLM-L6-v2 (runs locally, no API key)
Split: word-based (no NLTK required)
Store: InMemoryDocumentStore (persisted to JSON on disk)
       Swap to QdrantDocumentStore for production scale.
"""

import asyncio
import json
import os
import time
import tempfile
from pathlib import Path
from typing import Optional

INDEX_PATH = Path(os.getenv("RAG_INDEX_PATH", "/data/marzano_index.json"))
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
SPLIT_LENGTH = int(os.getenv("RAG_SPLIT_LENGTH", "120"))
SPLIT_OVERLAP = int(os.getenv("RAG_SPLIT_OVERLAP", "20"))
TOP_K = int(os.getenv("RAG_TOP_K", "4"))


def _haystack_available() -> bool:
    try:
        from haystack.components.converters import PyPDFToDocument
        from haystack.components.preprocessors import DocumentSplitter
        from haystack.components.embedders import (
            SentenceTransformersDocumentEmbedder,
            SentenceTransformersTextEmbedder,
        )
        from haystack.document_stores.in_memory import InMemoryDocumentStore
        from haystack.components.retrievers.in_memory import InMemoryEmbeddingRetriever
        return True
    except ImportError:
        return False


HAYSTACK_AVAILABLE = _haystack_available()


class _Store:
    """Singleton holding the loaded vector store and embedder."""

    def __init__(self):
        self.store = None
        self.text_embedder = None
        self.retriever = None
        self.loaded = False
        self.doc_count = 0

    def load(self):
        if not HAYSTACK_AVAILABLE:
            print("[RAG] Haystack not installed — RAG disabled.")
            return
        if not INDEX_PATH.exists():
            print(f"[RAG] No index at {INDEX_PATH} — use /ingest to build one.")
            return
        self._init_from_file()

    def _init_from_file(self):
        from haystack.document_stores.in_memory import InMemoryDocumentStore
        from haystack.components.retrievers.in_memory import InMemoryEmbeddingRetriever
        from haystack.components.embedders import SentenceTransformersTextEmbedder
        from haystack import Document

        try:
            self.store = InMemoryDocumentStore()
            with open(INDEX_PATH) as f:
                raw = json.load(f)
            docs = []
            for d in raw:
                doc = Document(content=d["content"], meta=d.get("meta", {}))
                if d.get("embedding"):
                    doc.embedding = d["embedding"]
                docs.append(doc)
            self.store.write_documents(docs)
            self.text_embedder = SentenceTransformersTextEmbedder(model=EMBED_MODEL)
            self.text_embedder.warm_up()
            self.retriever = InMemoryEmbeddingRetriever(document_store=self.store)
            self.loaded = True
            self.doc_count = len(docs)
            print(f"[RAG] Loaded {len(docs)} chunks from {INDEX_PATH}")
        except Exception as e:
            print(f"[RAG] Load failed: {e}")

    def retrieve(self, query: str, top_k: int = TOP_K) -> str:
        if not self.loaded:
            return ""
        try:
            result = self.text_embedder.run(text=query)
            docs = self.retriever.run(
                query_embedding=result["embedding"], top_k=top_k
            )["documents"]
            parts = [f"[Marzano Source {i+1}]\n{d.content}" for i, d in enumerate(docs)]
            return "\n\n".join(parts)
        except Exception as e:
            print(f"[RAG] Retrieval error: {e}")
            return ""

    def context_block(self, query: str) -> str:
        passages = self.retrieve(query)
        if not passages:
            return ""
        return "\n\nRELEVANT MARZANO REFERENCE PASSAGES:\n" + passages + "\n"


rag = _Store()


async def ingest_document(
    file_bytes: bytes,
    filename: str,
    job_id: str,
    notify,
    db_session=None,
):
    """
    Background ingestion pipeline with SSE progress events.
    notify = NotificationManager.broadcast (callable).
    """
    if not HAYSTACK_AVAILABLE:
        await notify(
            "error",
            "RAG not available",
            "Install haystack-ai and sentence-transformers to enable document indexing.",
            {"job_id": job_id},
        )
        return

    from haystack.components.converters import PyPDFToDocument
    from haystack.components.preprocessors import DocumentSplitter
    from haystack.components.embedders import SentenceTransformersDocumentEmbedder

    await notify(
        "ingestion_started",
        "Indexing started",
        f"Parsing '{filename}' — this may take a minute.",
        {"job_id": job_id, "filename": filename, "progress": 0},
    )

    if db_session:
        from database import IngestionJob
        from sqlalchemy import update
        await db_session.execute(
            update(IngestionJob).where(IngestionJob.id == job_id).values(status="processing")
        )
        await db_session.commit()

    try:
        t0 = time.time()
        suffix = Path(filename).suffix or ".pdf"

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        await notify(
            "ingestion_progress", "Parsing document",
            f"Extracting text from {filename}…",
            {"job_id": job_id, "filename": filename, "progress": 10},
            persist=False,
        )

        # Convert + split
        converter = PyPDFToDocument()
        splitter = DocumentSplitter(split_by="word", split_length=SPLIT_LENGTH, split_overlap=SPLIT_OVERLAP)
        conv_result = converter.run(sources=[tmp_path])
        split_result = splitter.run(documents=conv_result["documents"])
        chunks = split_result["documents"]
        total = len(chunks)

        await notify(
            "ingestion_progress", "Embedding chunks",
            f"Parsed {total} chunks. Generating embeddings…",
            {"job_id": job_id, "filename": filename, "progress": 20, "chunks_total": total},
            persist=False,
        )

        # Embed in batches
        embedder = SentenceTransformersDocumentEmbedder(model=EMBED_MODEL)
        embedder.warm_up()

        BATCH = 16
        embedded_docs = []
        for i in range(0, total, BATCH):
            batch = chunks[i: i + BATCH]
            result = embedder.run(documents=batch)
            embedded_docs.extend(result["documents"])
            done = min(i + BATCH, total)
            pct = 20 + int((done / total) * 65)
            await notify(
                "ingestion_progress", "Embedding chunks",
                f"Embedded {done}/{total} chunks…",
                {"job_id": job_id, "filename": filename, "progress": pct,
                 "chunks_done": done, "chunks_total": total},
                persist=False,
            )
            await asyncio.sleep(0)

        # Merge + save
        await notify(
            "ingestion_progress", "Saving index",
            "Writing to knowledge base…",
            {"job_id": job_id, "filename": filename, "progress": 88},
            persist=False,
        )

        existing = _load_raw_index()
        for d in embedded_docs:
            existing.append({
                "content": d.content,
                "meta": {**(d.meta or {}), "source": filename},
                "embedding": d.embedding,
            })

        INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(INDEX_PATH, "w") as f:
            json.dump(existing, f)

        rag.load()
        elapsed = round(time.time() - t0, 1)

        if db_session:
            import datetime
            from database import IngestionJob
            from sqlalchemy import update
            await db_session.execute(
                update(IngestionJob).where(IngestionJob.id == job_id).values(
                    status="complete", chunks_total=total, chunks_done=total,
                    completed_at=datetime.datetime.utcnow(),
                )
            )
            await db_session.commit()

        try:
            os.unlink(tmp_path)
        except Exception:
            pass

        await notify(
            "ingestion_complete",
            "✓ Document indexed",
            f"'{filename}' added — {total} chunks indexed in {elapsed}s. "
            f"Total knowledge base: {rag.doc_count} chunks.",
            {"job_id": job_id, "filename": filename, "progress": 100,
             "chunks_total": total, "elapsed_s": elapsed, "index_total": rag.doc_count},
        )

    except Exception as e:
        err = str(e)
        if db_session:
            from database import IngestionJob
            from sqlalchemy import update
            await db_session.execute(
                update(IngestionJob).where(IngestionJob.id == job_id).values(
                    status="error", error_message=err
                )
            )
            await db_session.commit()

        await notify(
            "error", "Indexing failed",
            f"Failed to index '{filename}': {err}",
            {"job_id": job_id, "filename": filename, "progress": 0},
        )


def _load_raw_index() -> list:
    if INDEX_PATH.exists():
        try:
            with open(INDEX_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return []
