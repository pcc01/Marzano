# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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
