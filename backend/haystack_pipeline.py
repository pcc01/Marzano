"""
Haystack RAG pipeline for the Marzano book.
Run `python haystack_pipeline.py index` to ingest a PDF.
In production queries, retrieved passages are injected into the AI prompt.

Requires: pip install haystack-ai sentence-transformers faiss-cpu pypdf
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Optional


# ---------------------------------------------------------------------------
# Lazy imports — Haystack is optional; the app runs without it
# ---------------------------------------------------------------------------
def _import_haystack():
    try:
        from haystack import Document, Pipeline
        from haystack.components.converters import PyPDFToDocument
        from haystack.components.preprocessors import DocumentSplitter
        from haystack.components.embedders import SentenceTransformersDocumentEmbedder, SentenceTransformersTextEmbedder
        from haystack.components.writers import DocumentWriter
        from haystack.document_stores.in_memory import InMemoryDocumentStore
        from haystack.components.retrievers.in_memory import InMemoryEmbeddingRetriever
        return True
    except ImportError:
        return False


HAYSTACK_AVAILABLE = _import_haystack()
INDEX_PATH = Path(os.getenv("RAG_INDEX_PATH", "/data/marzano_index.json"))
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")


class MarzanoRAG:
    """
    Thin wrapper around Haystack for Marzano book retrieval.
    Falls back to empty context if Haystack is not configured.
    """

    def __init__(self):
        self.store = None
        self.retriever = None
        self.text_embedder = None
        self._loaded = False

        if HAYSTACK_AVAILABLE and INDEX_PATH.exists():
            self._load_index()

    def _load_index(self):
        try:
            from haystack.document_stores.in_memory import InMemoryDocumentStore
            from haystack.components.retrievers.in_memory import InMemoryEmbeddingRetriever
            from haystack.components.embedders import SentenceTransformersTextEmbedder
            from haystack import Document

            self.store = InMemoryDocumentStore()
            with open(INDEX_PATH) as f:
                docs_data = json.load(f)
            docs = [Document(**d) for d in docs_data]
            self.store.write_documents(docs)

            self.text_embedder = SentenceTransformersTextEmbedder(model=EMBED_MODEL)
            self.text_embedder.warm_up()

            self.retriever = InMemoryEmbeddingRetriever(document_store=self.store)
            self._loaded = True
            print(f"[RAG] Loaded {len(docs)} Marzano chunks from {INDEX_PATH}")
        except Exception as e:
            print(f"[RAG] Failed to load index: {e}")

    def retrieve(self, query: str, top_k: int = 4) -> str:
        """Return relevant Marzano book passages as a formatted string."""
        if not self._loaded:
            return ""

        try:
            result = self.text_embedder.run(text=query)
            docs = self.retriever.run(
                query_embedding=result["embedding"], top_k=top_k
            )["documents"]

            passages = []
            for i, doc in enumerate(docs, 1):
                passages.append(f"[Marzano Source {i}]\n{doc.content}")
            return "\n\n".join(passages)
        except Exception as e:
            print(f"[RAG] Retrieval failed: {e}")
            return ""

    def format_context_block(self, query: str) -> str:
        """Return a prompt-ready context block, or empty string."""
        passages = self.retrieve(query)
        if not passages:
            return ""
        return (
            "\n\nRELEVANT MARZANO BOOK PASSAGES (use these to ground your assessment):\n"
            + passages
            + "\n"
        )


# Singleton
rag = MarzanoRAG()


# ---------------------------------------------------------------------------
# Indexing CLI  (python haystack_pipeline.py index /path/to/marzano.pdf)
# ---------------------------------------------------------------------------
def index_pdf(pdf_path: str):
    if not HAYSTACK_AVAILABLE:
        print("ERROR: Install haystack-ai first: pip install haystack-ai sentence-transformers faiss-cpu pypdf")
        sys.exit(1)

    from haystack import Pipeline
    from haystack.components.converters import PyPDFToDocument
    from haystack.components.preprocessors import DocumentSplitter
    from haystack.components.embedders import SentenceTransformersDocumentEmbedder
    from haystack.document_stores.in_memory import InMemoryDocumentStore
    from haystack.components.writers import DocumentWriter

    print(f"Indexing {pdf_path}...")
    store = InMemoryDocumentStore()

    pipeline = Pipeline()
    pipeline.add_component("converter", PyPDFToDocument())
    pipeline.add_component("splitter", DocumentSplitter(split_by="sentence", split_length=8, split_overlap=2))
    pipeline.add_component("embedder", SentenceTransformersDocumentEmbedder(model=EMBED_MODEL))
    pipeline.add_component("writer", DocumentWriter(document_store=store))

    pipeline.connect("converter", "splitter")
    pipeline.connect("splitter", "embedder")
    pipeline.connect("embedder", "writer")

    pipeline.run({"converter": {"sources": [pdf_path]}})

    docs = store.filter_documents()
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(INDEX_PATH, "w") as f:
        json.dump([{"content": d.content, "meta": d.meta, "embedding": d.embedding} for d in docs], f)

    print(f"Indexed {len(docs)} chunks → {INDEX_PATH}")


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "index":
        index_pdf(sys.argv[2])
    else:
        print("Usage: python haystack_pipeline.py index /path/to/marzano.pdf")
