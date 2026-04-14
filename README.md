# HexMind

HexMind is a Six Hats multi-expert AI decision engine with a local-first CLI, a FastAPI backend, and a React web app.

This public repository is the open-core edition:

- It includes the orchestration engine, API layer, web UI, tests, and a small sample asset library.
- It excludes the full curated commercial prompt library, raw prompt source material, and SaaS-only operating assets.

## What Is Included

- `src/hexmind/`: core engine, auth, archive, API, knowledge, and CLI code
- `web/`: React frontend source and build config
- `tests/`: automated coverage for the engine and API
- `personas/` and `prompts/library/`: small sample assets for local demos

## What Stays Private In The Hosted Product

- Expanded prompt library and curated role packs
- Raw prompt collection and import pipelines
- SaaS operations, deployment, billing, analytics, and growth assets

## Open-Source Dependencies

This release uses capabilities from several GitHub-hosted open-source projects, including FastAPI, SQLAlchemy, LiteLLM, Instructor, React, Vite, Tailwind CSS, Recharts, Lucide React, Click, and Rich.

See `ATTRIBUTIONS.md` for a concise breakdown of what each project is used for in this repo.

## Install

```bash
pip install -e ".[dev]"
```

## Run The CLI

```bash
hexmind personas
hexmind prompts
hexmind ask "Should we launch an AI copiloted onboarding flow?" --model gpt-4o-mini
```

## Run The API

```bash
uvicorn hexmind.api.app:app --reload
```

## Run The Web App

```bash
cd web
npm install
npm run dev
```

## Asset Overrides

HexMind can switch persona and prompt roots through environment variables:

```bash
HEXMIND_PERSONAS_DIR=personas
HEXMIND_PROMPTS_DIR=prompts/library
```

That makes it easy to run the same codebase against a public sample asset set or a private SaaS asset set.

## Export A Public Repo From The Private Workspace

From the full private workspace, generate a clean GitHub-ready copy with:

```bash
python -X utf8 scripts/prepare_public_repo.py
```

The script writes an export to `exports/github-public/`.

## License

MIT
