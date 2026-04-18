# Marzano AI Assessment Tool

> AI-powered educational assessment grounded in **Marzano's New Taxonomy of Educational Objectives**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.2.0-blue)](https://github.com/pcc01/Marzano/releases)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ed)](https://docs.docker.com/compose/)

---

## What This Does

Traditional assessments test what students already know. This tool enables **personalized learning** — students meet core curriculum requirements by following their passions, and teachers receive AI-generated draft feedback that explicitly maps every observation to a named Marzano taxonomy level and sublevel.

A student passionate about **photography** demonstrates the same geometry standards as a student studying **barrel-making** (volume and surface area) or **astronomy** (scientific notation). The AI assesses any artifact — written description, photo, diagram, PDF, or video — using the same rigorous framework, cites the exact taxonomy level for every finding, and shows the teacher its full reasoning.

**Teachers stay in control.** The AI generates a draft. Teachers see the reasoning, can override any level, add their own observations, and must explicitly approve before feedback is final. Student submissions come in through a separate portal and appear in the teacher dashboard with a clear badge.

---

## Features

| Feature | Status |
|---|---|
| Marzano taxonomy — all 6 levels, 22 sublevels | ✅ |
| Multi-modal artifacts: image, PDF, video, text | ✅ |
| Video frame extraction (ffmpeg) + optional Whisper transcript | ✅ |
| Haystack RAG — index Marzano books as PDFs | ✅ |
| Real-time SSE notifications with progress bars | ✅ |
| Teacher dashboard — review, edit, approve | ✅ |
| Student submission portal — 3-step wizard + tracking ID | ✅ |
| PostgreSQL — full async persistence | ✅ |
| Pluggable AI — Anthropic API or local Ollama | ✅ |
| Passion-to-curriculum mapping | ✅ |
| Standards alignment (Common Core, NGSS) | 🔜 |
| Batch assessment upload | 🔜 |
| PDF export of approved feedback | 🔜 |
| LMS integration (Canvas, Google Classroom) | 🔜 |

---

## Marzano's New Taxonomy

Unlike Bloom's Taxonomy, Marzano's model recognises that **motivation and metacognition fire before cognition**. The three systems engage in sequence, and the AI models this ordering in every assessment:

```
┌──────────────────────────────────────────────────────┐
│  SELF SYSTEM  (engages first — decides to engage)    │
│  Examining Importance · Efficacy · Emotional         │
│  Response · Overall Motivation                       │
├──────────────────────────────────────────────────────┤
│  METACOGNITIVE SYSTEM  (engages second — plans)      │
│  Goal Specification · Process Monitoring ·           │
│  Monitoring Clarity · Monitoring Accuracy            │
├──────────────────────────────────────────────────────┤
│  COGNITIVE SYSTEM  (engages third — does the work)   │
│  Retrieval → Comprehension → Analysis                │
│           → Knowledge Utilization                    │
└──────────────────────────────────────────────────────┘
```

| Level | Sublevels | Bloom's Equivalent |
|---|---|---|
| **Self System** | Importance, Efficacy, Emotional Response, Motivation | — (unique to Marzano) |
| **Metacognitive** | Goal Specification, Process Monitoring, Clarity, Accuracy | — (unique to Marzano) |
| **Retrieval** | Recognizing, Recalling, Executing | Remember |
| **Comprehension** | Integrating, Symbolizing | Understand |
| **Analysis** | Matching, Classifying, Analyzing Errors, Generalizing, Specifying | Analyze / Evaluate |
| **Knowledge Utilization** | Decision Making, Problem Solving, Experimenting, Investigating | Create (partial) |

---

## Architecture

```
┌────────────────────────────────────────────────┐
│  Browser                                       │
│  :3000/          Teacher dashboard             │
│  :3000/student/  Student portal                │
└───────────────────┬────────────────────────────┘
                    │ HTTP + SSE
                    ▼
              nginx :3000
              /api/ → backend:8000
                    │
        ┌───────────┼────────────────┐
        ▼           ▼                ▼
   main.py     haystack_pipeline  notifications.py
   FastAPI     RAG + ingestion    SSE event bus
   routes      Haystack + PDF     asyncio queues
        │           │
        ▼           ▼
   database.py  marzano_index.json
   SQLAlchemy   (persisted vector store)
   async ORM
        │
        ▼
   PostgreSQL:5432
   assessments | ingestion_jobs | notifications
        │
        ▼
   ai_provider.py
   Anthropic API  ←→  Ollama (swap via .env)
```

---

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker + Compose v2)
- An [Anthropic API key](https://console.anthropic.com/) **or** a local [Ollama](https://ollama.ai/) installation

### 1 · Clone and configure

```bash
git clone https://github.com/pcc01/Marzano.git
cd Marzano
cp .env.example .env
```

Edit `.env` and add your key:

```env
ANTHROPIC_API_KEY=your-key-here
```

### 2 · Launch

```bash
docker compose up --build
```

PostgreSQL tables are created automatically on first startup.

### 3 · Open the interfaces

| URL | Who uses it |
|---|---|
| `http://localhost:3000` | Teacher dashboard |
| `http://localhost:3000/student/` | Student submission portal |
| `http://localhost:8000/docs` | FastAPI interactive API docs |

---

## Teacher Dashboard

The teacher dashboard is a single-page app that connects to the backend via a live **Server-Sent Events** stream. Every significant event — a student submitting work, a PDF finishing indexing, an assessment being approved — arrives as a toast notification without requiring a page refresh.

**Panels:**

- **New Assessment** — submit student work directly (teacher-side). Supports drag-and-drop file upload for images, PDFs, video, and schematics.
- **All Assessments** — sortable list with badges for student-submitted work, video artifacts, taxonomy level, and approval status.
- **Review** — full Marzano breakdown per sublevel, evidence cited from the artifact, AI reasoning panel, teacher comment field, level override, draft save, and one-click approval.
- **Index Documents** — drag-and-drop PDF upload to the Haystack knowledge base. A live progress bar shows embedding progress chunk-by-chunk via SSE.
- **Notifications** — persisted history of all system events with unread count badge and mark-read on click.
- **Taxonomy Reference** — all six levels and 22 sublevels with associated verbs, for quick consultation while reviewing.

---

## Student Portal

Students access `http://localhost:3000/student/` without any login. The portal walks them through three steps:

1. **About you** — name, grade, subject
2. **Your passion** — visual card selector (architecture, astronomy, craft/making, photography, music, cooking, or custom)
3. **Your work** — description textarea, optional file upload (image, video, or PDF), reflection notes

On submission the student receives a **tracking ID**. They can paste it back into the portal at any time to check whether their teacher has reviewed and approved the feedback.

Submissions from the student portal appear in the teacher dashboard with a blue **Student** badge.

---

## Multi-modal Artifact Handling

| Artifact type | How it's processed |
|---|---|
| **Image** (JPG, PNG, GIF, WebP) | Base64-encoded and sent directly to the AI vision model |
| **PDF** | Text extracted via Haystack `PyPDFToDocument`; first 2,000 chars included in the AI prompt |
| **Video** (MP4, MOV, AVI, MKV, WebM) | ffmpeg extracts up to 8 evenly-spaced frames; frames sent as images to the vision model. Optional Whisper transcript if `faster-whisper` is installed |
| **Schematic / diagram** | Treated as an image |
| **Text description** | Always supported; no file required |
| **Student reflection** | Parsed alongside the artifact as a primary source of metacognitive evidence |

---

## Haystack RAG — Indexing the Marzano Book

The RAG pipeline lets the AI cite actual passages from the Marzano book in its feedback rather than relying solely on training data.

**Why RAG instead of sending the whole book?**  
A 200-page book is roughly 60,000–80,000 tokens. Sending it on every request is slow and expensive. Haystack chunks and embeds the book once (word-based splitting, 120-word chunks with 20-word overlap), then retrieves only the 3–4 most relevant passages per assessment. This works identically with Anthropic or Ollama.

**PDF parse results from test run (4 Marzano reference documents):**

| Document | Size | Chunks | Parse time |
|---|---|---|---|
| Marzano Verb List | 64 KB | 5 | 0.28 s |
| Marzano Overview | 49 KB | 27 | 0.05 s |
| Terms, Phrases & Products | 172 KB | 14 | 0.10 s |
| Irvine Journal Article | 1 MB | 131 | 2.51 s |
| **Total** | **1.3 MB** | **177** | **2.9 s** |

**How to index your documents:**

1. Open the teacher dashboard → **Index Documents**
2. Drag and drop any PDF
3. Watch the progress bar and SSE toasts as chunks are embedded
4. The index persists in a Docker volume across restarts
5. All subsequent assessments automatically include relevant retrieved passages

The embedding model is `sentence-transformers/all-MiniLM-L6-v2` (downloads on first use, cached locally). To use a different model, set `EMBED_MODEL` in `.env`.

---

## SSE Notification System

The backend emits Server-Sent Events on a persistent HTTP connection. The teacher dashboard subscribes on load and receives events without polling.

| Event type | Triggered by |
|---|---|
| `ingestion_started` | PDF upload begins processing |
| `ingestion_progress` | Each batch of 16 chunks embedded |
| `ingestion_complete` | Full index written and reloaded |
| `assessment_ready` | Any new assessment created (teacher or student) |
| `assessment_approved` | Teacher approves a feedback record |
| `error` | Any pipeline failure |

All events are also persisted to the `notifications` table in PostgreSQL and visible in the Notifications panel.

---

## Switching to Ollama (Local AI — No API Key)

```bash
# In .env:
AI_PROVIDER=ollama
OLLAMA_MODEL=llama3        # text only
# OLLAMA_MODEL=llava       # vision — required for image/video analysis

# Uncomment the ollama service block in docker-compose.yml, then:
docker compose up --build
docker compose exec ollama ollama pull llama3
```

For image and video artifact analysis, use a vision-capable model such as `llava` or `bakllava`. Text-only models will receive the artifact description but cannot interpret uploaded images or video frames.

---

## Passion-to-Curriculum Mapping

| Student Passion | Math Concepts Covered | Marzano Entry Point |
|---|---|---|
| Architecture | Geometry, ratios, structural load, trigonometry | Knowledge Utilization |
| Astronomy | Scientific notation, scale, gravity, orbital mechanics | Analysis |
| Barrel Making / Craft | Volume, surface area, ratios, geometry | Comprehension |
| Photography | Ratios, fractions, depth-of-field geometry | Analysis |
| Music | Fractions, frequency, wave patterns, ratios | Matching |
| Cooking / Baking | Ratios, scaling, measurement, chemistry | Retrieval → Comprehension |

To add a new passion domain, edit `PASSION_MATH_CONNECTIONS` in `backend/marzano_framework.py`. Each entry needs `concepts`, `marzano_entry_point`, and `sample_prompt`.

---

## API Reference

Full interactive docs at `http://localhost:8000/docs`.

### Assessments

| Endpoint | Method | Description |
|---|---|---|
| `/assess` | POST | Submit artifact (multipart form), receive AI feedback draft |
| `/assessments` | GET | List all assessments |
| `/assessments/{id}` | GET | Retrieve one assessment with full feedback |
| `/assessments/{id}` | PATCH | Save teacher edits and approval status |

### Student Portal

| Endpoint | Method | Description |
|---|---|---|
| `/student/submit` | POST | Student artifact submission (sets `submitted_by=student`) |
| `/student/status/{id}` | GET | Check whether a submission has been approved |

### Haystack Ingestion

| Endpoint | Method | Description |
|---|---|---|
| `/ingest` | POST | Upload a PDF to the knowledge base; returns `job_id` immediately |
| `/ingest/jobs` | GET | List all ingestion jobs with status and chunk counts |
| `/ingest/jobs/{id}` | GET | Get one ingestion job |
| `/ingest/status` | GET | RAG index status — loaded, doc count |

### Notifications

| Endpoint | Method | Description |
|---|---|---|
| `/notifications/stream` | GET | SSE stream — subscribe for live events |
| `/notifications` | GET | Notification history (persisted) |
| `/notifications/{id}/read` | PATCH | Mark one notification read |
| `/notifications/mark-all-read` | POST | Mark all notifications read |

### System

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | AI provider info, RAG status, SSE subscriber count |
| `/taxonomy` | GET | Full Marzano taxonomy |
| `/passions` | GET | Passion-to-concept mapping |

---

## Project Structure

```
Marzano/
├── backend/
│   ├── main.py                  FastAPI routes — all endpoints
│   ├── marzano_framework.py     Taxonomy definitions, prompt builder, passion mapping
│   ├── ai_provider.py           Anthropic / Ollama abstraction (swap via AI_PROVIDER env)
│   ├── haystack_pipeline.py     RAG indexing, retrieval, SSE progress events
│   ├── database.py              SQLAlchemy 2.0 async models — assessments, jobs, notifications
│   ├── notifications.py         SSE manager — asyncio.Queue per browser tab
│   ├── video_handler.py         ffmpeg frame extraction, optional Whisper transcript
│   ├── requirements.txt
│   └── Dockerfile               Python 3.12-slim + ffmpeg
├── frontend/
│   ├── index.html               Teacher dashboard — SSE toasts, ingestion panel, review UI
│   └── student/
│       └── index.html           Student portal — 3-step wizard, tracking ID, status checker
├── nginx/
│   └── default.conf             Reverse proxy, SSE buffering disabled, /student/ route
├── docker-compose.yml           postgres + backend + nginx (+ optional ollama)
├── .env.example                 All configurable environment variables
├── .gitignore
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `AI_PROVIDER` | `anthropic` | `anthropic` or `ollama` |
| `ANTHROPIC_API_KEY` | — | Required when `AI_PROVIDER=anthropic` |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | Anthropic model string |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Ollama service URL |
| `OLLAMA_MODEL` | `llama3` | Ollama model name |
| `DATABASE_URL` | `postgresql+asyncpg://marzano:marzano@postgres:5432/marzano` | PostgreSQL connection string |
| `RAG_INDEX_PATH` | `/data/marzano_index.json` | Persisted vector index location |
| `EMBED_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Sentence transformer for embeddings |
| `RAG_SPLIT_LENGTH` | `120` | Words per RAG chunk |
| `RAG_TOP_K` | `4` | Passages retrieved per assessment |
| `VIDEO_MAX_FRAMES` | `8` | Max frames extracted from video |
| `VIDEO_MAX_SECONDS` | `300` | Video duration cap (5 min) |

---

## Contributing

Pull requests are welcome. For major changes, open an issue first.

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit with a clear message
4. Push and open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for code style guidelines and the PR checklist.

---

## References

- Marzano, R. J., & Kendall, J. S. (2007). *The New Taxonomy of Educational Objectives* (2nd ed.). Corwin Press.
- Marzano, R. J., & Kendall, J. S. (2008). *Designing and Assessing Educational Objectives: Applying the New Taxonomy*. Corwin Press.
- Irvine, J. (2020). Marzano's New Taxonomy as a framework for investigating student affect. *Journal of Instructional Pedagogies, 24*.
- Irvine, J. (2017). A comparison of revised Bloom and Marzano's New Taxonomy of Learning. *Research in Higher Education Journal, 33*.

---

## License

[MIT](LICENSE) — free to use, modify, and distribute.
