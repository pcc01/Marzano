"""
Unit tests — haystack_pipeline.py
Tests the metadata filter (_build_mask), vector store loading,
and the embedding singleton without requiring actual model downloads.
Uses mock embeddings (random unit vectors) to test retrieval logic.
"""

import json
import numpy as np
import pytest
import tempfile
import os
from unittest.mock import patch, MagicMock


# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────

def _make_unit_vec(dim: int = 384) -> list[float]:
    """Random normalised vector for mock embeddings."""
    v = np.random.randn(dim).astype(np.float32)
    return (v / np.linalg.norm(v)).tolist()


def _make_raw_doc(content: str, source: str,
                  doc_type: str = "marzano_reference",
                  state: str = None,
                  grade_band: str = None,
                  subject_area: str = None) -> dict:
    meta = {"source": source, "doc_type": doc_type}
    if state:        meta["state"]        = state
    if grade_band:   meta["grade_band"]   = grade_band
    if subject_area: meta["subject_area"] = subject_area
    return {"content": content, "meta": meta, "embedding": _make_unit_vec()}


@pytest.fixture()
def sample_raw_index():
    """Mix of Marzano reference docs and tagged standards docs."""
    return [
        _make_raw_doc("Marzano self system content",        "marzano_book.pdf"),
        _make_raw_doc("Marzano cognitive analysis content", "marzano_verbs.pdf"),
        _make_raw_doc("California Grade 6 Math standards",  "ca_math_6.pdf",
                      doc_type="standards", state="California",
                      grade_band="middle_6_8", subject_area="Mathematics"),
        _make_raw_doc("California Grade 9 Math standards",  "ca_math_9.pdf",
                      doc_type="standards", state="California",
                      grade_band="high_9_10", subject_area="Mathematics"),
        _make_raw_doc("Texas Grade 6 Science standards",    "tx_sci_6.pdf",
                      doc_type="standards", state="Texas",
                      grade_band="middle_6_8", subject_area="Science"),
        _make_raw_doc("New York ELA standards all grades",  "ny_ela.pdf",
                      doc_type="standards", state="New York",
                      grade_band=None, subject_area="ELA"),
    ]


# ─────────────────────────────────────────────────────────────
# Import _Store (only the class, not the singleton or embed model)
# ─────────────────────────────────────────────────────────────

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))


class TestStoreMask:
    """_Store._build_mask() metadata filtering."""

    def _make_store(self, raw_index):
        from haystack_pipeline import _Store
        store = _Store()
        store._load_from_raw(raw_index)
        return store

    def test_no_filter_returns_all_docs(self, sample_raw_index):
        store = self._make_store(sample_raw_index)
        mask = store._build_mask()
        assert mask.sum() == len(sample_raw_index)

    def test_reference_docs_always_pass(self, sample_raw_index):
        store = self._make_store(sample_raw_index)
        # Filter to California Grade 6 Math — reference docs should still pass
        mask = store._build_mask(state="California", grade_band="middle_6_8",
                                  subject_area="Mathematics")
        # Reference docs (index 0, 1) + CA G6 Math (index 2) + NY ELA (no grade_band, index 5)
        assert mask[0] == True   # marzano_book — reference
        assert mask[1] == True   # marzano_verbs — reference
        assert mask[2] == True   # CA G6 Math — exact match
        assert mask[3] == False  # CA G9 Math — grade mismatch
        assert mask[4] == False  # TX G6 Science — state + subject mismatch
        assert mask[5] == False  # NY ELA — state="New York" ≠ "California", excluded

    def test_state_filter_excludes_other_states(self, sample_raw_index):
        store = self._make_store(sample_raw_index)
        mask = store._build_mask(state="Texas")
        # Reference docs always pass; TX standards pass; CA and NY standards don't
        assert mask[0] == True   # reference
        assert mask[1] == True   # reference
        assert mask[2] == False  # CA Math — state mismatch
        assert mask[3] == False  # CA Math G9 — state mismatch
        assert mask[4] == True   # TX Science — state match
        assert mask[5] == False  # NY ELA — state mismatch

    def test_grade_band_filter(self, sample_raw_index):
        store = self._make_store(sample_raw_index)
        mask = store._build_mask(grade_band="high_9_10")
        assert mask[0] == True   # reference
        assert mask[2] == False  # CA G6 Math — grade mismatch
        assert mask[3] == True   # CA G9 Math — grade match

    def test_subject_filter(self, sample_raw_index):
        store = self._make_store(sample_raw_index)
        mask = store._build_mask(subject_area="Science")
        assert mask[0] == True   # reference
        assert mask[2] == False  # CA Math — subject mismatch
        assert mask[4] == True   # TX Science — match
        assert mask[5] == False  # NY ELA — subject mismatch

    def test_untagged_standards_always_pass(self):
        """A standards doc with no state/grade tags is treated as universal."""
        raw = [
            _make_raw_doc("Universal standards", "universal.pdf",
                          doc_type="standards"),  # no state/grade/subject tags
        ]
        from haystack_pipeline import _Store
        store = _Store()
        store._load_from_raw(raw)
        mask = store._build_mask(state="California", grade_band="middle_6_8")
        assert mask[0] == True


class TestStoreLoad:
    """_Store loading from raw index and hot-reload."""

    def test_load_from_raw_sets_doc_count(self, sample_raw_index):
        from haystack_pipeline import _Store
        store = _Store()
        store._load_from_raw(sample_raw_index)
        assert store.doc_count == len(sample_raw_index)
        assert store.loaded is True

    def test_load_from_raw_sets_matrix_shape(self, sample_raw_index):
        from haystack_pipeline import _Store
        store = _Store()
        store._load_from_raw(sample_raw_index)
        assert store._matrix is not None
        assert store._matrix.shape[0] == len(sample_raw_index)
        assert store._matrix.shape[1] == 384  # embedding dim

    def test_reload_from_raw_overwrites(self, sample_raw_index):
        from haystack_pipeline import _Store
        store = _Store()
        store._load_from_raw(sample_raw_index[:2])
        assert store.doc_count == 2
        store._reload_from_raw(sample_raw_index)
        assert store.doc_count == len(sample_raw_index)

    def test_empty_raw_index_does_not_set_loaded(self):
        from haystack_pipeline import _Store
        store = _Store()
        store._load_from_raw([])
        assert store.loaded is False

    def test_docs_without_embeddings_are_skipped(self):
        from haystack_pipeline import _Store
        raw = [
            {"content": "no embedding", "meta": {}, "embedding": None},
            _make_raw_doc("has embedding", "source.pdf"),
        ]
        store = _Store()
        store._load_from_raw(raw)
        assert store.doc_count == 1

    def test_load_from_disk(self, tmp_path):
        from haystack_pipeline import _Store, INDEX_PATH
        raw = [_make_raw_doc("test content", "test.pdf")]
        index_file = tmp_path / "test_index.json"
        with open(index_file, "w") as f:
            json.dump(raw, f)

        store = _Store()
        # Patch INDEX_PATH to point to our temp file
        with patch("haystack_pipeline.INDEX_PATH", index_file):
            store.load()
        assert store.loaded is True
        assert store.doc_count == 1


class TestStoreRetrieve:
    """_Store.retrieve() cosine similarity retrieval."""

    def test_retrieve_returns_top_k(self, sample_raw_index):
        from haystack_pipeline import _Store
        store = _Store()
        store._load_from_raw(sample_raw_index)
        query_emb = np.array(_make_unit_vec(), dtype=np.float32)
        results = store.retrieve(query_emb, top_k=3)
        assert len(results) == 3

    def test_retrieve_returns_tuples_of_three(self, sample_raw_index):
        from haystack_pipeline import _Store
        store = _Store()
        store._load_from_raw(sample_raw_index)
        query_emb = np.array(_make_unit_vec(), dtype=np.float32)
        results = store.retrieve(query_emb, top_k=2)
        for item in results:
            text, source, score = item
            assert isinstance(text, str)
            assert isinstance(source, str)
            assert isinstance(score, float)
            assert -1.0 <= score <= 1.0  # cosine similarity range

    def test_retrieve_with_filter_respects_mask(self, sample_raw_index):
        from haystack_pipeline import _Store
        store = _Store()
        store._load_from_raw(sample_raw_index)
        query_emb = np.array(_make_unit_vec(), dtype=np.float32)
        # Only Texas standards should pass (plus reference docs)
        results = store.retrieve(query_emb, top_k=10,
                                  state="Texas", grade_band="middle_6_8",
                                  subject_area="Science")
        sources = {r[1] for r in results}
        # Texas science doc should be retrievable
        assert "tx_sci_6.pdf" in sources
        # California docs should NOT be in results
        assert "ca_math_6.pdf" not in sources

    def test_retrieve_empty_store_returns_empty(self):
        from haystack_pipeline import _Store
        store = _Store()
        query_emb = np.array(_make_unit_vec(), dtype=np.float32)
        results = store.retrieve(query_emb, top_k=3)
        assert results == []

    def test_retrieve_normalised_scores(self, sample_raw_index):
        """Scores should be in [-1, 1] since embeddings are normalised."""
        from haystack_pipeline import _Store
        store = _Store()
        store._load_from_raw(sample_raw_index)
        query_emb = np.array(_make_unit_vec(), dtype=np.float32)
        results = store.retrieve(query_emb, top_k=len(sample_raw_index))
        for _, _, score in results:
            assert -1.01 <= score <= 1.01


class TestIndexPath:
    """INDEX_PATH constant and _load_raw_index helper."""

    def test_index_path_is_pathlib(self):
        from haystack_pipeline import INDEX_PATH
        from pathlib import Path
        assert isinstance(INDEX_PATH, Path)

    def test_load_raw_index_returns_empty_when_missing(self, tmp_path):
        from haystack_pipeline import _load_raw_index
        with patch("haystack_pipeline.INDEX_PATH", tmp_path / "nonexistent.json"):
            result = _load_raw_index()
        assert result == []

    def test_load_raw_index_returns_data(self, tmp_path):
        from haystack_pipeline import _load_raw_index
        raw = [_make_raw_doc("content", "source.pdf")]
        idx_path = tmp_path / "index.json"
        with open(idx_path, "w") as f:
            json.dump(raw, f)
        with patch("haystack_pipeline.INDEX_PATH", idx_path):
            result = _load_raw_index()
        assert len(result) == 1
        assert result[0]["content"] == "content"
