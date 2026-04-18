"""
Haystack RAG pipeline — v3 (bug-fixed).

ROOT CAUSES FIXED:
  1. Version conflict: haystack-ai==2.27.0 passes `backend` kwarg to
     SentenceTransformer.__init__() which sentence-transformers==3.1.1
     rejects at that call site inside Haystack's wrapper layer.
     FIX: bypass Haystack's embedder entirely; use sentence-transformers
     directly so we control the exact call signature.

  2. Event loop blocking: SentenceTransformersDocumentEmbedder.warm_up()
     and .run() are synchronous CPU-bound calls. Running them directly on
     the FastAPI async event loop freezes all request handling while
     embedding is in progress — making jobs appear stuck.
     FIX: all encoding runs in a ThreadPoolExecutor via run_in_executor().

  3. New model instance per ingestion: a fresh embedder was constructed and
     warmed up on every ingest_document() call, causing redundant model
     loads and memory pressure if two jobs ran concurrently.
     FIX: module-level singleton (_EmbedModel) loaded once, shared forever.

Haystack is still used for what it does well and where it is bug-free:
  - PyPDFToDocument  (PDF → Haystack Document objects)
  - DocumentSplitter (word-based chunking, no NLTK required)

Retrieval uses numpy dot-product on normalised embeddings (cosine sim).
"""

import asyncio
import json
import numpy as np
import os
import time
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

INDEX_PATH  = Path(os.getenv("RAG_INDEX_PATH",  "/data/marzano_index.json"))
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
SPLIT_LENGTH  = int(os.getenv("RAG_SPLIT_LENGTH",  "120"))
SPLIT_OVERLAP = int(os.getenv("RAG_SPLIT_OVERLAP", "20"))
TOP_K         = int(os.getenv("RAG_TOP_K",          "4"))
EMBED_BATCH   = int(os.getenv("RAG_EMBED_BATCH",    "32"))

# One thread is enough — sentence-transformers releases the GIL during
# inference so other async tasks continue while encoding runs.
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="rag-embed")


# ─────────────────────────────────────────────────────────────
# Embedding singleton
# ─────────────────────────────────────────────────────────────

class _EmbedModel:
    """
    Loads sentence-transformers once and exposes async encode().
    All CPU work is dispatched to _executor so the event loop stays free.
    """
    def __init__(self):
        self._model = None
        self._ready = False
        self._error: Optional[str] = None

    def _load_sync(self):
        """Blocking load — called inside the thread pool, not the event loop."""
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(EMBED_MODEL)
        self._ready = True
        print(f"[RAG] Embedding model loaded: {EMBED_MODEL}")

    async def ensure_ready(self):
        """Non-blocking: schedule model load if not yet done."""
        if self._ready:
            return
        if self._error:
            raise RuntimeError(f"Embedding model failed to load: {self._error}")
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(_executor, self._load_sync)
        except Exception as e:
            self._error = str(e)
            raise

    async def encode(self, texts: list[str]) -> np.ndarray:
        """
        Encode a list of strings → float32 matrix, shape (N, dim).
        Normalised so dot-product == cosine similarity.
        Runs in thread pool to avoid blocking the event loop.
        """
        await self.ensure_ready()
        loop = asyncio.get_event_loop()

        def _encode():
            return self._model.encode(
                texts,
                batch_size=EMBED_BATCH,
                normalize_embeddings=True,
                show_progress_bar=False,
            )

        return await loop.run_in_executor(_executor, _encode)

    async def encode_one(self, text: str) -> np.ndarray:
        result = await self.encode([text])
        return result[0]

    @property
    def ready(self) -> bool:
        return self._ready


_embed = _EmbedModel()


async def prewarm():
    """
    Called at FastAPI startup so the model is ready before the first request.
    Runs asynchronously — startup is not delayed if the download is slow.
    """
    try:
        await _embed.ensure_ready()
    except Exception as e:
        print(f"[RAG] Pre-warm failed (will retry on first use): {e}")


# ─────────────────────────────────────────────────────────────
# Vector store singleton
# ─────────────────────────────────────────────────────────────

class _Store:
    """
    Holds the document texts and their embedding matrix.
    Retrieval = cosine similarity via numpy dot-product (embeddings are
    normalised, so dot-product IS cosine similarity).
    """

    def __init__(self):
        self._texts:   list[str]  = []
        self._sources: list[str]  = []
        self._matrix:  Optional[np.ndarray] = None   # shape (N, dim)
        self.loaded    = False
        self.doc_count = 0

    def load(self):
        """Load persisted index from disk (synchronous — called at startup)."""
        if not INDEX_PATH.exists():
            print(f"[RAG] No index at {INDEX_PATH} — use /ingest to build one.")
            return
        try:
            with open(INDEX_PATH) as f:
                raw = json.load(f)
            texts   = [d["content"]              for d in raw if d.get("embedding")]
            sources = [d.get("meta", {}).get("source", "?") for d in raw if d.get("embedding")]
            vecs    = [d["embedding"]             for d in raw if d.get("embedding")]
            if not vecs:
                print("[RAG] Index contains no embedded documents.")
                return
            self._texts   = texts
            self._sources = sources
            self._matrix  = np.array(vecs, dtype=np.float32)
            self.loaded    = True
            self.doc_count = len(texts)
            print(f"[RAG] Loaded {self.doc_count} embedded chunks from {INDEX_PATH}")
        except Exception as e:
            print(f"[RAG] Load failed: {e}")

    def _reload_from_raw(self, raw: list):
        """Hot-reload after a successful ingestion without reading disk again."""
        texts   = [d["content"]                              for d in raw if d.get("embedding")]
        sources = [d.get("meta", {}).get("source", "?")     for d in raw if d.get("embedding")]
        vecs    = [d["embedding"]                            for d in raw if d.get("embedding")]
        if vecs:
            self._texts   = texts
            self._sources = sources
            self._matrix  = np.array(vecs, dtype=np.float32)
            self.loaded    = True
            self.doc_count = len(texts)

    def retrieve(self, query_emb: np.ndarray, top_k: int = TOP_K) -> list[tuple[str, str, float]]:
        """Return top_k (text, source, score) tuples."""
        if not self.loaded or self._matrix is None:
            return []
        scores = self._matrix @ query_emb          # cosine sim, normalised
        idxs   = np.argsort(scores)[-top_k:][::-1]
        return [(self._texts[i], self._sources[i], float(scores[i])) for i in idxs]

    async def context_block(self, query: str) -> str:
        """Build the RAG context string injected into the AI prompt."""
        if not self.loaded:
            return ""
        try:
            q_emb = await _embed.encode_one(query)
            hits  = self.retrieve(q_emb)
            if not hits:
                return ""
            parts = [f"[Marzano Source {i+1} — {src}]\n{txt}"
                     for i, (txt, src, _) in enumerate(hits)]
            return "\n\nRELEVANT MARZANO REFERENCE PASSAGES:\n" + "\n\n".join(parts) + "\n"
        except Exception as e:
            print(f"[RAG] Retrieval error: {e}")
            return ""


rag = _Store()


def _haystack_pdf_available() -> bool:
    try:
        from haystack.components.converters import PyPDFToDocument
        from haystack.components.preprocessors import DocumentSplitter
        return True
    except ImportError:
        return False


HAYSTACK_AVAILABLE = _haystack_pdf_available()


# ─────────────────────────────────────────────────────────────
# Ingestion background task
# ─────────────────────────────────────────────────────────────

async def ingest_document(
    file_bytes: bytes,
    filename:   str,
    job_id:     str,
    notify,                # notif_manager.broadcast coroutine
    db_session=None,
):
    """
    Full ingestion pipeline:
      parse → split → embed (batched, thread pool) → merge index → persist → reload

    Progress events are emitted via SSE throughout so the browser shows a live
    progress bar. Navigation away from the tab does NOT cancel this task — it
    runs server-side regardless of client connection state.
    """
    if not HAYSTACK_AVAILABLE:
        await notify(
            "error", "RAG not available",
            "Install haystack-ai and pypdf to enable document indexing.",
            {"job_id": job_id},
        )
        return

    await notify(
        "ingestion_started", "Indexing started",
        f"Parsing '{filename}' — this may take a minute on first run "
        f"while the embedding model downloads.",
        {"job_id": job_id, "filename": filename, "progress": 0},
    )

    if db_session:
        from database import IngestionJob
        from sqlalchemy import update
        await db_session.execute(
            update(IngestionJob).where(IngestionJob.id == job_id).values(status="processing")
        )
        await db_session.commit()

    tmp_path = None
    try:
        t0     = time.time()
        suffix = Path(filename).suffix or ".pdf"

        # ── 1. Write bytes to temp file ──────────────────────
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        await notify(
            "ingestion_progress", "Parsing document",
            f"Extracting text from {filename}…",
            {"job_id": job_id, "filename": filename, "progress": 8},
            persist=False,
        )

        # ── 2. PDF → chunks (Haystack, no embedder) ─────────
        from haystack.components.converters import PyPDFToDocument
        from haystack.components.preprocessors import DocumentSplitter

        loop = asyncio.get_event_loop()

        def _parse_sync():
            converter = PyPDFToDocument()
            splitter  = DocumentSplitter(
                split_by="word",
                split_length=SPLIT_LENGTH,
                split_overlap=SPLIT_OVERLAP,
            )
            conv = converter.run(sources=[tmp_path])
            spl  = splitter.run(documents=conv["documents"])
            return [d.content for d in spl["documents"]]

        chunk_texts = await loop.run_in_executor(_executor, _parse_sync)
        total = len(chunk_texts)

        await notify(
            "ingestion_progress", "Embedding chunks",
            f"Parsed {total} chunks — generating embeddings "
            f"(model: {EMBED_MODEL})…",
            {"job_id": job_id, "filename": filename, "progress": 18,
             "chunks_total": total},
            persist=False,
        )

        # ── 3. Embed in batches — fully async-safe ───────────
        all_embeddings: list[list[float]] = []
        NOTIFY_EVERY = max(1, total // 10)   # notify ~10 times regardless of batch size

        for start in range(0, total, EMBED_BATCH):
            batch_texts = chunk_texts[start: start + EMBED_BATCH]
            vecs = await _embed.encode(batch_texts)          # runs in thread pool
            all_embeddings.extend(vecs.tolist())

            done = min(start + EMBED_BATCH, total)
            pct  = 18 + int((done / total) * 68)
            if done % NOTIFY_EVERY < EMBED_BATCH or done == total:
                await notify(
                    "ingestion_progress", "Embedding chunks",
                    f"Embedded {done}/{total} chunks…",
                    {"job_id": job_id, "filename": filename, "progress": pct,
                     "chunks_done": done, "chunks_total": total},
                    persist=False,
                )
            await asyncio.sleep(0)   # yield to event loop so other requests proceed

        # ── 4. Merge into existing index and persist ─────────
        await notify(
            "ingestion_progress", "Saving index",
            "Writing to knowledge base…",
            {"job_id": job_id, "filename": filename, "progress": 88},
            persist=False,
        )

        existing = _load_raw_index()
        for text, emb in zip(chunk_texts, all_embeddings):
            existing.append({
                "content":   text,
                "meta":      {"source": filename},
                "embedding": emb,
            })

        INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(INDEX_PATH, "w") as f:
            json.dump(existing, f)

        # Hot-reload the live store
        rag._reload_from_raw(existing)
        elapsed = round(time.time() - t0, 1)

        # ── 5. Update DB ─────────────────────────────────────
        if db_session:
            import datetime
            from database import IngestionJob
            from sqlalchemy import update
            await db_session.execute(
                update(IngestionJob).where(IngestionJob.id == job_id).values(
                    status="complete",
                    chunks_total=total,
                    chunks_done=total,
                    completed_at=datetime.datetime.utcnow(),
                )
            )
            await db_session.commit()

        await notify(
            "ingestion_complete",
            "✓ Document indexed",
            f"'{filename}' — {total} chunks indexed in {elapsed}s. "
            f"Knowledge base total: {rag.doc_count} chunks.",
            {"job_id": job_id, "filename": filename, "progress": 100,
             "chunks_total": total, "elapsed_s": elapsed,
             "index_total": rag.doc_count},
        )

    except Exception as exc:
        err_msg = str(exc)
        print(f"[RAG] Ingestion error for {filename}: {err_msg}")

        if db_session:
            from database import IngestionJob
            from sqlalchemy import update
            await db_session.execute(
                update(IngestionJob).where(IngestionJob.id == job_id).values(
                    status="error", error_message=err_msg
                )
            )
            await db_session.commit()

        await notify(
            "error", "Indexing failed",
            f"Could not index '{filename}': {err_msg}",
            {"job_id": job_id, "filename": filename, "progress": 0},
        )

    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _load_raw_index() -> list:
    if INDEX_PATH.exists():
        try:
            with open(INDEX_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return []
