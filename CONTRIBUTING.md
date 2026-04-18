# Contributing to Marzano AI Assessment Tool

Thank you for your interest in contributing. This project aims to make 
Marzano's taxonomy practical and accessible for real classrooms.

## Ways to Contribute

- **New passion domains** — add entries to `PASSION_MATH_CONNECTIONS` in `backend/marzano_framework.py`
- **Bug reports** — open a GitHub Issue with steps to reproduce
- **Feature requests** — open an Issue describing the use case
- **Code** — fork, branch, and open a Pull Request

## Development Setup

```bash
git clone https://github.com/pcc01/Marzano.git
cd Marzano
cp .env.example .env   # add your ANTHROPIC_API_KEY
docker compose up --build
```

Backend live-reloads on file save (uvicorn `--reload` is on by default).  
Frontend is plain HTML/JS — just refresh the browser.

## Code Style

- Python: follow PEP 8, use type hints where practical
- Keep `marzano_framework.py` as the single source of truth for taxonomy definitions
- New AI providers go in `ai_provider.py` — add a new branch in `call_ai()`, don't fork the file
- All feedback JSON must include `ai_reasoning` so teachers can see why the AI said what it said

## Pull Request Checklist

- [ ] Code runs with `docker compose up --build`
- [ ] No secrets or `.env` files committed
- [ ] README updated if behaviour changes
- [ ] New passion domains include `concepts`, `marzano_entry_point`, and `sample_prompt`
