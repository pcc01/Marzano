# Marzano AI Assessment Tool

> AI-powered educational assessment grounded in **Marzano's New Taxonomy of Educational Objectives**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue)](https://docs.docker.com/compose/)

---

## What This Does

Traditional assessments test what students already know. This tool enables **personalized learning** — students meet core curriculum requirements by following their passions, and teachers receive structured AI feedback that explicitly maps student work to Marzano's taxonomy.

A student passionate about **photography** can explore depth-of-field geometry to demonstrate the same math standards as a student studying **barrel-making** (volume and surface area) or **astronomy** (scientific notation and scale). The AI assesses both using the same rigorous framework and cites the exact taxonomy level and sublevel in its feedback.

**Teachers remain in control.** The AI generates a draft. The teacher sees the AI's full reasoning, can edit any part of it, override the taxonomy level, add their own observations, and approve the final feedback before it goes anywhere.

---

## Marzano's New Taxonomy

Unlike Bloom's Taxonomy, Marzano's model recognises that **motivation and metacognition come before cognition**. Three systems engage in sequence:

```
┌─────────────────────────────────────────────────┐
│  SELF SYSTEM  (engages first)                   │
│  Importance · Efficacy · Emotion · Motivation   │
├─────────────────────────────────────────────────┤
│  METACOGNITIVE SYSTEM  (engages second)         │
│  Goal Setting · Process Monitoring · Accuracy   │
├─────────────────────────────────────────────────┤
│  COGNITIVE SYSTEM  (engages third)              │
│  Retrieval → Comprehension → Analysis           │
│              → Knowledge Utilization            │
└─────────────────────────────────────────────────┘
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
Browser (Teacher Dashboard)
        │
        ▼
   nginx :3000
   ├── /        → frontend/index.html  (single-page teacher UI)
   └── /api/    → backend:8000
                   │
                   ├── marzano_framework.py   Taxonomy definitions + prompt builder
                   ├── ai_provider.py         Pluggable AI (Anthropic ↔ Ollama)
                   ├── haystack_pipeline.py   RAG for Marzano book (optional)
                   └── main.py                FastAPI routes + artifact handling
```

### Multi-modal Artifact Support

| Input Type | Handling |
|---|---|
| Image (JPG, PNG, GIF, WebP) | Encoded and sent directly to vision-capable AI model |
| PDF | Text extracted via Haystack; fallback to description |
| Video | Frame extraction (roadmap) |
| Schematics / diagrams | Treated as images |
| Text description | Always supported — no file required |
| Student reflection notes | Parsed for metacognitive indicators |

---

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) or Docker + Compose
- An [Anthropic API key](https://console.anthropic.com/) **or** a local [Ollama](https://ollama.ai/) installation

### 1 · Clone and configure

```bash
git clone https://github.com/pcc01/Marzano.git
cd Marzano
cp .env.example .env
```

Open `.env` and add your API key:

```env
ANTHROPIC_API_KEY=your-key-here
```

### 2 · Launch

```bash
docker compose up --build
```

### 3 · Open the teacher dashboard

```
http://localhost:3000
```

The FastAPI interactive docs are at `http://localhost:8000/docs`.

---

## Switching to Ollama (Local AI — No API Key)

```bash
# 1. In .env:
AI_PROVIDER=ollama
OLLAMA_MODEL=llama3          # or llava (vision), mistral, gemma, etc.

# 2. Uncomment the ollama service in docker-compose.yml

# 3. Rebuild and start
docker compose up --build

# 4. Pull your chosen model (first run only)
docker compose exec ollama ollama pull llama3
```

For **vision tasks** (analysing student images and schematics), use `llava` or `bakllava`.

---

## Adding the Marzano Book via RAG

The RAG pipeline lets the AI ground its feedback directly in the Marzano book text.

```bash
# 1. Uncomment Haystack deps in backend/requirements.txt
# 2. Rebuild
docker compose build backend

# 3. Index your PDF (once — index persists in a Docker volume)
docker compose exec backend \
  python haystack_pipeline.py index /path/to/marzano_book.pdf
```

**Why RAG instead of sending the whole book?** A 200-page book is roughly 60,000–80,000 tokens. Sending it on every request is slow and expensive. Haystack chunks and embeds the book once, then retrieves only the 3–4 most relevant passages per assessment. This works identically with Anthropic or Ollama.

---

## Passion-to-Curriculum Mapping

| Student Passion | Math Concepts Covered | Marzano Entry Point |
|---|---|---|
| Architecture | Geometry, ratios, structural load, trigonometry | Knowledge Utilization |
| Astronomy | Scientific notation, scale, gravity, orbital mechanics | Analysis |
| Barrel Making | Volume, surface area, ratios, geometry | Comprehension |
| Photography | Ratios, fractions, depth-of-field geometry | Analysis |
| Music | Fractions, frequency, wave patterns, ratios | Matching |
| Cooking / Baking | Ratios, scaling, measurement, chemistry | Retrieval → Comprehension |

New passions are easy to add — edit `PASSION_MATH_CONNECTIONS` in `backend/marzano_framework.py`.

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Provider info, RAG status |
| `/taxonomy` | GET | Full Marzano taxonomy (used by frontend) |
| `/passions` | GET | Passion-to-concept mapping |
| `/assess` | POST | Submit artifact, receive AI feedback draft |
| `/assessments` | GET | List all assessments |
| `/assessments/{id}` | GET | Retrieve one assessment |
| `/assessments/{id}` | PATCH | Save teacher edits and approval |

---

## Project Structure

```
Marzano/
├── backend/
│   ├── main.py                  FastAPI application + routes
│   ├── marzano_framework.py     Taxonomy definitions, prompt builder
│   ├── ai_provider.py           Anthropic / Ollama abstraction layer
│   ├── haystack_pipeline.py     RAG indexing and retrieval
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   └── index.html               Single-page teacher dashboard
├── nginx/
│   └── default.conf             Reverse proxy config
├── docker-compose.yml
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

---

## Roadmap

- [ ] Video artifact support (frame extraction + transcript)
- [ ] PostgreSQL backend (replace JSON file store)
- [ ] Student-facing submission portal
- [ ] Standards alignment (Common Core, NGSS, provincial curricula)
- [ ] Batch assessment (upload a class set at once)
- [ ] Export to PDF (formatted feedback report)
- [ ] LMS integration (Canvas, Google Classroom)

---

## Contributing

Pull requests are welcome. For major changes, open an issue first.

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit: `git commit -m 'Add your feature'`
4. Push: `git push origin feature/your-feature`
5. Open a Pull Request

---

## References

- Marzano, R. J., & Kendall, J. S. (2007). *The New Taxonomy of Educational Objectives* (2nd ed.). Corwin Press.
- Marzano, R. J., & Kendall, J. S. (2008). *Designing and Assessing Educational Objectives*. Corwin Press.
- Irvine, J. (2020). Marzano's New Taxonomy as a framework for investigating student affect. *Journal of Instructional Pedagogies, 24*.

---

## License

[MIT](LICENSE) — free to use, modify, and distribute.
