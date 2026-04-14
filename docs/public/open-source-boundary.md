# Open Source Boundary

This repository is structured for an open-core split.

## Public

- `src/hexmind/`: orchestration engine, API, auth, archive, knowledge, and CLI
- `web/src/`: product UI and interaction patterns
- `tests/`: regression coverage
- `open_source_assets/`: sample personas and prompt assets used to seed the public export
- `scripts/prepare_public_repo.py`: exports a clean GitHub-ready repo snapshot

## Private

- `prompts/library/`: the full curated production prompt library
- `personas/raw/`: source material and scraped prompt corpora
- `.env`, runtime databases, logs, local archives, and deployment secrets
- future billing, growth, analytics, and production operations assets

## Recommended Product Strategy

- Publish the engine, UI shell, and sample assets on GitHub.
- Keep the commercial moat in the hosted asset library, managed prompt curation, and operational tooling.
- Treat the public repo as a trust and distribution channel, not as the full SaaS payload.
