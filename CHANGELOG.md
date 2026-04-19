# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [0.4.1] — 2026-04-18

### Fixed

**Bug 1 — `build_international_context()` wrong parameter used (`international.py`)**
The second parameter was named `marzano_level` but `main.py` was passing `resolved_band`
(a grade-band ID like `"middle_6_8"`). The Marzano framework lookup silently produced
empty strings for every international assessment because no Marzano level key
matched a grade-band string. Fixed: parameter renamed to accept `country_code` as
the second positional arg and `marzano_target` as an optional keyword arg. The call
site in `main.py` now fetches the subject's Marzano target from the curriculum registry
and passes it correctly.

**Bug 2 — `/student/submit` silent data loss (`main.py`)**
The student submission endpoint was missing `grade_band`, `student_state`,
`country_code`, and `local_grade` form fields. It delegated to `create_assessment`
without forwarding them, so student submissions never received curriculum context
injection, standards RAG filtering, or international context — all silently dropped.
Fixed: all four fields added to the signature and forwarded to `create_assessment`.

**Bug 3 — Country fields missing from `/assessments` list (`main.py`)**
The list endpoint response omitted `country_code` and `local_grade` from each row.
The teacher dashboard therefore could not show the international badge (🌐) in the
assessment list — only in the individual review panel. Fixed: both fields added.

**Bug 4 — `created_at.isoformat()` crash on None (`main.py`)**
When `session.commit()` is mocked (and in some edge cases where the ORM hasn't
populated the default), `record.created_at` can be `None`, causing an `AttributeError`.
Exposed by the new `TestStudentSubmitFields` e2e tests. Fixed: fallback to
`datetime.utcnow().isoformat()` when the field is None.

### Changed

- `tests/test_international.py`: `TestBuildInternationalContext` updated to match
  corrected `build_international_context(us_grade, country_code, marzano_target=None)`
  signature; four new tests added (with/without marzano_target, marzano_target=retrieval)
- `tests/test_api_e2e.py`: three new test classes added:
  `TestInternationalConsistency` (curriculum grades covered by grade map, taxonomy
  levels covered by Marzano international map, all countries present for Grade 9),
  `TestStudentSubmitFields` (422 regression tests for grade_band, country_code,
  student_state), `TestAssessmentsListFields` (country_code shape validation)
- Test count: 177 → 187

---

## [0.4.0] — 2026-04-18

### Added

**International classroom UI — fully wired**

- Country selector on both teacher dashboard and student portal (10 countries:
  US, UK, Australia, Canada, France, Germany, Japan, IB, New Zealand, Singapore)
- Local grade designation field auto-populates from the `/international/grades/{grade}`
  API when a country is selected (e.g. selecting "UK" + "Grade 9" pre-fills "Year 10")
- International panel in teacher dashboard: grade level lookup table, Marzano ↔
  international framework equivalency table, country cards
- `🌐 GB (Year 10)` badge shown in review panel metadata for international assessments
- `country_code` and `local_grade` fields added to `Assessment` DB model
- `POST /assess` and `POST /student/submit` accept `country_code` and `local_grade`
- `build_international_context()` injected into AI system prompt when country provided;
  AI instructed to map Marzano level to student's national framework equivalent
- New API endpoints: `GET /international/grades/{us_grade}`,
  `GET /international/marzano/{level}`

**Test suite — 177 tests, 100% pass rate**

- `tests/test_marzano_framework.py` — 29 unit tests covering taxonomy structure,
  passion mapping, prompt generation, and JSON extraction
- `tests/test_curriculum.py` — 40 unit tests covering grade bands, subject registry,
  lookup helpers, context builder, and API response shape
- `tests/test_international.py` — 54 unit tests covering country registry, grade map
  completeness, Marzano framework mapping, all helper functions
- `tests/test_haystack_pipeline.py` — 20 unit tests covering metadata filter
  (`_build_mask`), store loading, retrieval with filter, and index persistence
- `tests/test_api_e2e.py` — 34 end-to-end tests using FastAPI TestClient covering
  health, taxonomy, passions, curriculum, international, ingest, and assessments
  endpoints; database and AI fully mocked
- `pytest.ini` — test configuration with asyncio_mode=auto and short traceback format

**Bug fixes found by tests**

- `grade_band_for_level("Grade 12")` returned `elementary_k2` due to substring
  collision: "grade 1" matched "grade 12". Fixed with exact equality matching.
- `curriculum_block` and `standards_block` were constructed in `build_system_prompt()`
  but never interpolated into the returned f-string. Fixed — both now appear in
  the CONTEXT section of the system prompt.

---

## [0.3.0] — 2026-04-18

### Fixed

**Haystack ingestion — three root-cause bugs resolved**

- **`SentenceTransformer.__init__() got an unexpected keyword argument 'backend'`**
  `haystack-ai==2.27.0` internally passes a `backend` kwarg to
  `SentenceTransformer.__init__()` that `sentence-transformers==3.1.1` rejects
  at that call site. The Haystack embedder wrapper and the pinned
  sentence-transformers version were incompatible.
  *Fix:* downgraded to `haystack-ai==2.9.0` (pre-dates the `backend` kwarg) and
  bypassed Haystack's embedder entirely. `sentence-transformers` is now called
  directly, giving full control over the call signature.
  Haystack is still used for PDF conversion (`PyPDFToDocument`) and text
  splitting (`DocumentSplitter`) where it works correctly.

- **Event loop blocking caused jobs to appear stuck**
  `SentenceTransformersDocumentEmbedder.warm_up()` and `.run()` are synchronous
  CPU-bound calls. Running them on FastAPI's async event loop froze all HTTP
  request handling while embedding was in progress. A second upload attempt
  queued another blocking call behind the first, making both appear hung.
  *Fix:* all encoding is dispatched to a `ThreadPoolExecutor` via
  `asyncio.run_in_executor()`. The event loop remains responsive throughout.

- **New model instance created per ingestion call**
  A fresh `SentenceTransformersDocumentEmbedder` was constructed and
  `warm_up()`-ed on every call to `ingest_document()`, reloading the model
  from disk each time and consuming duplicate memory when two jobs ran
  concurrently.
  *Fix:* module-level `_EmbedModel` singleton. The model loads once at startup
  via `asyncio.create_task(prewarm())` and is reused for all subsequent
  ingestion and retrieval calls.

### Added

- **Stuck job recovery at startup** — any `IngestionJob` left in `"processing"`
  state when the server restarts (e.g. after a crash) is automatically marked
  `"error"` with a descriptive message. Previously these jobs were permanently
  stuck with no way to recover them.

- **`POST /ingest/jobs/{id}/retry`** — resets a failed or stuck job's DB status
  to `"pending"` and emits a notification prompting the user to re-upload.

- **`DELETE /ingest/index`** — removes the entire vector index from disk and
  memory so the knowledge base can be rebuilt from scratch without restarting
  the server.

- **Async RAG context retrieval** — `rag.context_block()` is now properly
  `async` and awaited in the assessment pipeline, consistent with the rest of
  the codebase.

### Changed

- `requirements.txt`: `haystack-ai` pinned to `2.9.0`; `numpy>=1.24.0` added
  as an explicit dependency; comment added explaining why Haystack's embedder
  components are intentionally not used.

---

## [0.2.0] — 2026-04-18

### Added

- **PostgreSQL backend** — `database.py` with SQLAlchemy 2.0 async ORM.
  Tables: `assessments`, `ingestion_jobs`, `notifications`.
  `docker-compose.yml` updated with `postgres:16-alpine` service.

- **Video artifact support** — `video_handler.py` uses ffmpeg to extract up to
  8 evenly-spaced frames from uploaded video files. Frames are sent to the AI
  vision model alongside the text description. Optional Whisper transcription
  available by installing `faster-whisper`.

- **Student submission portal** — `frontend/student/index.html`, a 3-step
  wizard (student info → passion selector → work description + file upload).
  Students receive a tracking ID on submission and can check approval status.
  Accessible at `/student/`. Teacher dashboard shows a blue **Student** badge
  on student-submitted assessments.

- **Haystack RAG pipeline** — fully activated. Upload any PDF via the
  **Index Documents** panel in the teacher dashboard. Documents are chunked
  (word-based, 120-word windows with 20-word overlap), embedded, and persisted
  to a Docker volume. The index survives container restarts.

- **Server-Sent Events (SSE) notifications** — `notifications.py` implements an
  asyncio queue-based pub/sub system. One SSE connection per browser tab.
  Events: `ingestion_started`, `ingestion_progress`, `ingestion_complete`,
  `assessment_ready`, `assessment_approved`, `error`. All persisted to
  the `notifications` table with unread tracking.

- **Teacher dashboard** — full rewrite with SSE-powered toast notifications,
  live ingestion progress bar, video/student badges, notification history panel,
  taxonomy reference panel, and RAG status indicator.

### Changed

- Artifact assessment pipeline updated to support images, PDFs (text
  extracted via Haystack), video (frames extracted via ffmpeg), and text.
- nginx config updated: SSE proxy buffering disabled, `/student/` route added.
- Dockerfile updated: `ffmpeg` system package added.

---

## [0.1.0] — 2026-04-17

### Added

- Initial release.
- FastAPI backend with full Marzano taxonomy framework
  (`marzano_framework.py`): all 6 levels, 22 sublevels, verb lists,
  question stems, student indicators, and passion-to-curriculum mapping.
- Pluggable AI provider (`ai_provider.py`): Anthropic API by default,
  Ollama swap-in via `AI_PROVIDER` environment variable.
- Single-page teacher dashboard with artifact submission, assessment review,
  teacher edit/approve workflow, and taxonomy reference.
- Docker Compose stack: FastAPI backend + nginx frontend.
- MIT licence, `.gitignore`, `CONTRIBUTING.md`, GitHub issue templates.
