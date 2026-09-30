# NOVA AI — Implementation Plan

> **Status:** Plan only. No phase has been started.
> **Read with:** `ARCHITECTURE.md` (the *what* and *why*) and `PROJECT_ANALYSIS.md` (the starting point).

---

## How This Plan Works

### Ground rules for every phase

1. **One small step = one Pull Request (PR).** Each numbered sub-step (e.g. *2.3*) is a separate, reviewable change.
2. **Nothing merges to `main` without passing checks and your approval.** `main` is what Lovable syncs; it must always work.
3. **Never rewrite pushed git history** (no force-push, rebase, or amend of pushed commits) — required by `AGENTS.md` to protect Lovable history.
4. **The UI is preserved.** No visual change to existing pages without your explicit approval. New pages reuse the existing design system and are shown to you before merging.
5. **Every phase ends with a demo you can check yourself** ("How you can test it") and a checklist ("Done when").
6. **Security and tests are built in every phase.** Phases 14 and 15 are audits and gap-filling, not the first time we think about them.
7. **No paid API calls in automated tests.** AI is replaced by a fake provider in CI.
8. **Stop points:** after each phase I summarise what changed, what was tested, and what's next — and wait for your go-ahead.

### Size legend

| Size | Meaning |
| --- | --- |
| **S** | Small — about 1–2 working sessions |
| **M** | Medium — several sessions |
| **L** | Large — split into many PRs over a longer period |

### Recommended execution order

The phase numbers below are kept as you requested. One adjustment is recommended so you see real results sooner and catch integration problems early:

```
0 → 1 → 2 → 3 → 12A (connect existing pages using seeded data)
  → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12B (new pages) → 13 → 14 → 15 → 16 → 17
```

Phase 12 is split into **12A** (connect *existing* pages — can happen right after the database exists) and **12B** (build the *new* pages once their data exists). Doing 12A early is optional but strongly recommended.

### Overview

| Phase | Name | Size | Depends on | Key result |
| --- | --- | --- | --- | --- |
| 0 | Project analysis | — | — | ✅ `PROJECT_ANALYSIS.md` done |
| 1 | Git and project safety | S | 0 | Safe workflow, CI, baseline screenshots |
| 2 | Backend foundation | S | 1 | ✅ FastAPI foundation, DB layer, migrations, tests |
| 3 | Database | M | 2 | ✅ Schema (27 tables) + seed data; read-only API still to do |
| 4 | News aggregation | M | 3 | Real AI news fetched and stored |
| 5 | Scientific research aggregation | M | 3 | arXiv papers fetched and stored |
| 6 | Courses and opportunities | M | 3 | Courses, 8 opportunity types incl. Jobs, AI tools |
| 7 | AI processing | L | 4–6 | Summaries, translations, classification, paper analysis |
| 8 | Search and semantic search | M | 7 | Hybrid search + related content |
| 9 | RAG | M | 8 | "Ask NOVA" answers with citations |
| 10 | Daily AI Brief | M | 7, 8 | Daily briefing + newsletter |
| 11 | Automation | M | 4–10 | Everything runs on schedule |
| 12 | Frontend integration | L | 3 (12A), 4–10 (12B) | UI shows real data; new pages |
| 13 | Authentication | M | 12A | Accounts, saved items, preferences |
| 14 | Security | M | 13 | Security audit and hardening |
| 15 | Testing | M | 13 | Full test suite, E2E, load tests |
| 16 | Deployment | M | 14, 15 | Production launch |
| 17 | Advanced features | L | 16 | Personalization, notifications, recommendations, deep paper analysis |

---

## Phase 0 — Project Analysis ✅

**Status:** Complete. See `PROJECT_ANALYSIS.md`.
**Result:** Frontend-only prototype; all data is mock; no backend, database, or auth; UI to be preserved.

---

## Phase 1 — Git and Project Safety

**Goal:** Make it impossible to lose work or break the live Lovable app while we build.

**Steps**
- **1.1 Baseline tag.** Create a git tag `v0-lovable-baseline` on the current `main` so we can always return to today's version.
- **1.2 Branch workflow.** Document: all work on branches → PR → checks → your approval → merge. Confirm with you how Lovable edits will be handled (decision D3). *Note:* strict GitHub branch-protection rules could block Lovable's own commits to `main`; we'll pick settings that don't.
- **1.3 Contributor docs.** Replace the Lovable prompt text in `README.md` with real project documentation (what it is, how to run it, where docs live). Add `.env.example` (names only, no values) and extend `.gitignore` for Python/backend files.
- **1.4 Frontend CI.** GitHub Actions workflow: install with Bun (`--frozen-lockfile`), type-check, build. *Known issue:* current files are not Prettier-formatted, so `lint` will likely fail; lint runs as **non-blocking** until 1.6 is approved.
- **1.5 Visual baseline.** Playwright screenshots of every existing page — English/Arabic × light/dark × mobile/desktop — stored as the reference for "the UI didn't change".
- **1.6 (Optional, needs your approval) Formatting-only cleanup.** Run the existing Prettier config on hand-written files. Zero behaviour change, verified by the screenshot comparison. Makes all later changes much safer to review.
- **1.7 Repository security settings.** Enable Dependabot alerts and secret scanning.

**Deliverables:** tag, updated README, `.env.example`, CI workflow, screenshot baseline.

**How you can test it**
- On GitHub, the *Tags* list shows `v0-lovable-baseline`.
- Open any PR → a green ✓ check appears.
- The Lovable preview still looks and works exactly as before.

**Done when**
- [ ] Baseline tag exists
- [ ] CI runs on every PR and passes on `main`
- [ ] Screenshot baseline committed
- [ ] Lovable editor still syncs normally

---

## Phase 2 — Backend Foundation ✅

**Status:** Complete. Delivered in `backend/` (see `backend/README.md`). At the owner's request this phase also includes the database connection layer (SQLAlchemy async), the migration system (Alembic, baseline migration `0001`), and the service/repository layers — i.e. step 3.2 of Phase 3 is already done. Verified: server runs with and without a database; 75 automated tests pass (including real-PostgreSQL tests); Docker image builds, runs as non-root, and passes its health check. The Dockerfile uses `pip install uv` rather than copying from `ghcr.io`, and the base image is overridable (`PYTHON_IMAGE`) for registry mirrors.


**Goal:** A minimal, well-structured FastAPI service that runs locally and in CI — no database or features yet.

**Steps**
- **2.1 Scaffold `backend/`** with `uv` (`pyproject.toml`, lockfile), the folder layout from ARCHITECTURE §5, Ruff (lint/format), mypy, pytest.
- **2.2 App skeleton:** app factory, settings from environment variables (`pydantic-settings`), structured JSON logging, request IDs, consistent error format, CORS allowlist.
- **2.3 Health endpoints:** `GET /health` (alive) and `GET /ready` (placeholder until DB exists). Auto docs at `/docs`.
- **2.4 Dockerfile** (small, non-root user) usable for both API and worker.
- **2.5 Backend CI job:** lint, type-check, tests on every PR touching `backend/`.
- **2.6 Security baseline:** security headers middleware, request size limit, `pip-audit` in CI.
- **2.7 `app/cli.py`** entry point (empty commands list) for later manual jobs.

**Deliverables:** runnable API, Dockerfile, CI job, first tests.

**How you can test it**
- Run one documented command, open `http://localhost:8000/docs` → the interactive API page appears.
- `http://localhost:8000/health` shows `{"status": "ok"}`.

**Done when**
- [ ] API starts locally and in Docker
- [ ] CI green (lint, types, tests, audit)
- [ ] No secrets committed; config documented in `.env.example`

---

## Phase 3 — Database ✅ (schema and seed)

**Status:** Schema, migrations and development seed data are complete — see `DATABASE.md`. The final design differs from the sketch below in a few places, for simplicity: `topics` became `categories` + `tags`; `ai_runs`/`job_runs`/`fetch_log` became `processing_logs`, `collection_jobs` and `error_logs`; paper analyses and article briefs share `ai_summaries`; RAG chunks share `embeddings`; `story_clusters` and `audit_log` are deferred (Phases 7 and 14). Verified: migrations apply, roll back and match the models (`alembic check`); seed loads idempotently; 219 automated tests pass against PostgreSQL 16 + pgvector.

**Not yet done (moved):** 3.1's Supabase project must be created by the owner (steps in `DATABASE.md` §7) and a least-privilege database role is deferred to Phase 14/16; the read-only API endpoints, response schemas and generated TypeScript types (3.6, 3.7, 3.9) move to the start of Phase 12A, where they're first used.


**Goal:** A real PostgreSQL database with the core schema, filled with today's mock content, served through read-only API endpoints.

**Steps**
- **3.1 Supabase project `nova-dev`** (decision D1). Enable `pgvector` and `pg_trgm`. Create schema `app`, a least-privilege app role, and keep `app` out of the public data API. Store connection strings as secrets.
- **3.2 SQLAlchemy + Alembic setup;** `/ready` now checks the database.
- **3.3 Migration 001 — content core:** `sources`, `topics`, `content_items`, `content_topics`, `articles`, `story_clusters`, `papers`, `paper_analyses`, `courses`, `learning_paths`, `learning_path_steps`, `opportunities`, `ai_tools`. RLS enabled, no public policies.
- **3.4 Migration 002 — operations:** `ai_runs`, `job_runs`, `fetch_log`, `audit_log`.
- **3.5 Seed script:** converts the current mock data (`src/data/*.ts` content) into seed JSON and loads it — so the database contains exactly what the site shows today.
- **3.6 Pydantic response schemas** matching the frontend's `NewsItem` / `Course` / `Opportunity` shapes (localized `{en, ar}` fields, ISO dates).
- **3.7 Read-only endpoints:** `/v1/home`, `/v1/news`, `/v1/news/{slug}`, `/v1/courses`, `/v1/learning-paths`, `/v1/opportunities`, `/v1/topics`, with cursor pagination.
- **3.8 Tests:** integration tests against a temporary Postgres+pgvector container in CI; migration up/down test.
- **3.9 OpenAPI → TypeScript types** generation script (types committed, not yet used by the UI).

**Deliverables:** schema migrations, seed data, read-only API, generated types.

**How you can test it**
- In the Supabase dashboard → Table Editor → `app.content_items` shows the 7 articles, 6 courses, 6 opportunities.
- `/docs` → try `GET /v1/news` → the same 7 stories the website shows.

**Done when**
- [ ] Migrations apply cleanly to an empty database and roll back
- [ ] Seeded content matches the mock data one-to-one
- [ ] All read endpoints tested; p95 < 150 ms locally
- [ ] Public data API cannot read `app` tables (verified by a test)

---

## Phase 4 — News Aggregation

**Goal:** Automatically collect real AI news from approved sources and store it (not yet summarised or published).

**Steps**
- **4.1 Source list:** propose ~10–15 initial sources for your approval (decision D8); check each one's terms and `robots.txt`; insert into `sources`.
- **4.2 Safe fetcher:** `httpx` client with timeouts, size limits, user-agent, conditional requests (ETag/Last-Modified), private-IP blocking (SSRF guard), per-host politeness delay.
- **4.3 RSS/Atom connector** (`feedparser`) → normalized items (title, URL, date, author, summary, image).
- **4.4 Normalization & de-duplication:** canonical URL, `url_hash` uniqueness, near-duplicate title detection.
- **4.5 Main-text extraction** (`trafilatura`) stored internally in `articles.body_text` with retention metadata.
- **4.6 Cheap relevance pre-filter** (keywords + source trust) to avoid spending AI money on off-topic items.
- **4.7 CLI:** `python -m app.cli ingest news [--source X]` + `fetch_log` records.
- **4.8 Tests:** saved sample feeds/pages as fixtures (no live internet in tests); re-running ingestion creates no duplicates.

**Deliverables:** news connector, fetch logs, ingested (unpublished) items.

**How you can test it**
- Run the ingest command → it prints e.g. "12 sources, 143 items found, 97 new".
- Run it again → "0 new" (no duplicates).
- Supabase Table Editor shows new rows with status `ingested`.

**Done when**
- [ ] ≥ 10 sources ingest successfully
- [ ] Zero duplicates on re-run
- [ ] Failing source doesn't stop others; error recorded in `fetch_log`
- [ ] Live website unchanged (items aren't published yet)

---

## Phase 5 — Scientific Research Aggregation

**Goal:** Collect new AI research papers with metadata, and full text for selected papers.

**Steps**
- **5.1 arXiv connector:** query categories `cs.AI`, `cs.LG`, `cs.CL`, `cs.CV`, `cs.RO`, `stat.ML`; respect the API rate limit (≤ 1 request / 3 s); store in `content_items` + `papers` (arXiv ID, versions, authors, abstract, categories, PDF link).
- **5.2 Enrichment (optional per source):** citation counts / venue from Semantic Scholar or OpenAlex.
- **5.3 Paper selection rules:** which papers get full-text processing (e.g. relevance score, author/lab lists, trending on enrichment sources, editor picks) to control cost.
- **5.4 PDF download + text extraction** (`pypdf`) for selected papers; section splitting where possible; licenses recorded.
- **5.5 Read endpoints:** `/v1/research`, `/v1/research/{id}`.
- **5.6 CLI + tests** with saved arXiv responses and sample PDFs.

**Deliverables:** research connector, papers in the database, research endpoints.

**How you can test it**
- Run `python -m app.cli ingest research --days 1` → "N new papers".
- `/docs` → `GET /v1/research` lists them with titles, authors, and abstracts.

**Done when**
- [ ] Daily arXiv fetch works and is idempotent
- [ ] Rate limits respected (verified in logs)
- [ ] Full text extracted for selected papers; failures recorded, not fatal

---

## Phase 6 — Courses and Opportunities

**Goal:** Real data for courses, learning paths, all opportunity types (scholarships, fellowships, internships, **jobs**, competitions, hackathons, bootcamps, research), and the AI tools directory.

**Steps**
- **6.1 Curation workflow v1 (no code for you):** documented spreadsheet/CSV templates per type + an import command, *or* direct entry in the Supabase Table Editor. Validation on import (required fields, valid URLs, real dates).
- **6.2 Opportunity model finalised:** `opportunity_type` covers all 8 types; real `deadline_at`; computed status (open / closing soon < 14 days / upcoming / closed); expired items auto-archived.
- **6.3 Jobs connectors:** public job-board endpoints (Greenhouse, Lever, Ashby) for a curated list of AI companies you approve; AI/ML role filter; de-duplication.
- **6.4 AI tools directory:** `ai_tools` data + import; pricing and use-case filters.
- **6.5 Endpoints with filters:** `/v1/opportunities?type=&remote=&closing_before=&country=`, `/v1/opportunities/{id}`, `/v1/tools`, `/v1/courses?level=&free=&topic=`.
- **6.6 Editor submission endpoint (admin-only, for later UI):** submit a URL → stored for AI extraction in Phase 7.
- **6.7 Tests:** import validation, status computation (deadline edge cases, time zones), connector fixtures.

**Deliverables:** curated + imported data for every content type, filterable endpoints.

**How you can test it**
- Fill the CSV template with 3 scholarships → run import → they appear in `GET /v1/opportunities?type=scholarship`.
- `GET /v1/opportunities?type=job&remote=true` returns remote AI jobs from the approved companies.

**Done when**
- [ ] All 8 opportunity types and AI tools are representable and filterable
- [ ] "Closing soon" computed from real dates
- [ ] Import rejects invalid rows with clear messages

---

## Phase 7 — AI Processing

**Goal:** Turn raw items into trustworthy, bilingual, structured content — with measured quality and controlled cost.

**Steps**
- **7.1 Provider abstraction:** `LLMProvider` and `EmbeddingProvider` interfaces; `FakeProvider` for tests; per-task configuration (provider, model, effort); `ai_runs` logging (tokens, cost, latency, prompt version).
- **7.2 Claude adapter:** official `anthropic` SDK; structured outputs with Pydantic schemas; prompt-caching layout; refusal handling (+ server-side fallback on the standard API); streaming for long outputs; typed error handling with retries.
- **7.3 Budget guard:** `AI_DAILY_BUDGET_USD`; non-urgent tasks pause when reached; alert logged.
- **7.4 Task: `classify`** (AI relevance, topics, importance) → wired after the Phase 4 pre-filter.
- **7.5 Task: `summarize_article`** producing every field the Article page shows (TL;DR, takeaways, why it matters, what happened, metrics, quote, timeline).
- **7.6 Quality guards:** schema validation, numbers-appear-in-source check, verbatim-quote check, confidence thresholds → `needs_review`.
- **7.7 Task: `translate`** EN→AR (and AR→EN for Arabic sources) with an AI-terminology glossary.
- **7.8 Task: `extract_opportunity`** for editor-submitted URLs (Phase 6.6).
- **7.9 Task: `analyze_paper`** (problem, method, results, limitations, beginner explanation, key terms) via the Batches API.
- **7.10 Story clustering:** group articles about the same event; `cluster_title` task.
- **7.11 Pipeline runner:** status transitions per ARCHITECTURE §7; CLI `python -m app.cli process --limit 20`.
- **7.12 Review queue API:** list/approve/edit/reject (`/v1/admin/review-queue`), audit-logged. Until an admin UI exists, you can review in the Supabase Table Editor.
- **7.13 Local model adapter (Ollama)** + evaluation comparison for translation/classification (optional, if you want local models).
- **7.14 Evaluation sets:** ~20 articles and ~10 papers with human ratings (accuracy, completeness, Arabic quality); a script that re-runs them and reports scores and cost. Used before any model/prompt change (decision D5).

**Deliverables:** AI pipeline, review queue, cost dashboard data, evaluation reports.

**How you can test it**
- Run `process --limit 10` → 10 items move to `published` or `needs_review`.
- Open one in `/docs` (`GET /v1/news/{slug}`) → English and Arabic summaries present.
- Read the evaluation report: quality scores and "cost per article".

**Done when**
- [ ] ≥ 90% of evaluation articles rated accurate; no fabricated numbers/quotes pass the guards
- [ ] Cost per article measured and within the agreed budget
- [ ] Refusals and failures land in `needs_review`, never on the site
- [ ] CI uses only `FakeProvider`

---

## Phase 8 — Search and Semantic Search

**Goal:** Fast, bilingual keyword + meaning-based search across all content types, and related-content suggestions.

**Steps**
- **8.1 Full-text search:** generated `search_en` / `search_ar` columns + GIN indexes (verify the `arabic` configuration exists; else `simple`).
- **8.2 Fuzzy matching:** `pg_trgm` index on titles.
- **8.3 Embeddings:** embedding provider adapter (cloud default, local optional — decision D6); `embed_pending` job; HNSW index; `embedding_model` recorded; re-embed command for model changes.
- **8.4 Hybrid ranking** (Reciprocal Rank Fusion + recency/importance boost) in `/v1/search?q=&type=&lang=`, results grouped by type.
- **8.5 Search understanding (optional flag):** natural-language filters ("remote internships closing this month").
- **8.6 Related content:** vector neighbours excluding same cluster; `related_items` cache; `/v1/content/{id}/related`.
- **8.7 Rate limiting** on search.
- **8.8 Search quality set:** ~30 queries (EN + AR) with expected results; automated check + latency measurement.

**Deliverables:** search and related-content endpoints, quality report.

**How you can test it**
- `/docs` → `GET /v1/search?q=robots learning from one demonstration` finds the robotics story even without exact words.
- Search in Arabic (`q=الروبوتات`) returns relevant English and Arabic items.

**Done when**
- [ ] ≥ 80% of quality-set queries return an expected item in the top 5
- [ ] p95 search latency < 400 ms
- [ ] Related items shown for every published item

---

## Phase 9 — RAG ("Ask NOVA")

**Goal:** Users can ask questions and get answers grounded in NOVA's content, with citations.

**Steps**
- **9.1 Chunking** of articles and papers into `content_chunks` (paragraph-aware, ~500–800 tokens, overlap) + chunk embeddings.
- **9.2 Retrieval function:** hybrid search over chunks, filters (type, date, paper-scoped), diversity (≤ 2 chunks per item).
- **9.3 Answer generation:** `answer_with_sources` — Claude citations on the cloud provider; numbered-source prompting on local; "not found" behaviour.
- **9.4 Safety:** untrusted-content isolation, no side-effecting tools, output length limits.
- **9.5 Endpoint `POST /v1/ask`** with Server-Sent Events streaming; per-user quota (enforced for real once auth exists in Phase 13; temporarily admin/dev-key only).
- **9.6 Paper-scoped Q&A:** "Ask about this paper".
- **9.7 RAG evaluation set:** ~30 questions with expected sources; checks citation correctness and "I don't know" cases.

**Deliverables:** `/v1/ask`, evaluation report.

**How you can test it**
- In `/docs`, ask "What did the new agent-planning benchmark find?" → answer with numbered sources that link to the right articles.
- Ask something NOVA has never covered → it says it couldn't find it instead of inventing an answer.

**Done when**
- [ ] ≥ 85% of evaluation answers cite a correct source
- [ ] 100% of "unanswerable" questions are declined gracefully
- [ ] Quotas and limits enforced

---

## Phase 10 — Daily AI Brief

**Goal:** A daily, bilingual editorial briefing on the site and by email.

**Steps**
- **10.1 Tables** `briefings`, `briefing_items`, `newsletter_subscribers`.
- **10.2 Selection algorithm:** top clusters of the last 24 h (importance × sources × recency), topic diversity, plus 1 paper, 1 tool, 1 closing-soon opportunity.
- **10.3 Generation:** `daily_brief` task (English) + `translate` (Arabic); draft → publish rules (decision D9).
- **10.4 Endpoints:** `/v1/briefings/latest`, `/v1/briefings/{date}`.
- **10.5 Newsletter:** email provider adapter (decision D7), subscribe → double opt-in confirmation → one-click unsubscribe; bilingual email template.
- **10.6 CLI:** `python -m app.cli brief generate --date YYYY-MM-DD` and `brief send --dry-run`.
- **10.7 Tests:** selection edge cases (slow news day), email rendering snapshots, unsubscribe flow.

**Deliverables:** briefing generation, archive endpoints, newsletter.

**How you can test it**
- Run `brief generate` → read today's briefing in `/docs` in both languages.
- Subscribe your own email → confirm → run `brief send` → the briefing arrives; the unsubscribe link works.

**Done when**
- [ ] Briefing generated for 7 consecutive test days with no manual fixes needed
- [ ] Email delivered, confirmed, and unsubscribable

---

## Phase 11 — Automation

**Goal:** Everything from Phases 4–10 runs by itself, reliably, on schedule.

**Steps**
- **11.1 Procrastinate setup:** queue tables (migration), worker process, Docker command.
- **11.2 Convert CLI jobs into tasks** (same functions — no logic duplication).
- **11.3 Schedules** per ARCHITECTURE §15 (fetch, process, arXiv, papers batch, jobs sync, opportunity status, trending, embeddings, related, brief, digests, cleanup, source health).
- **11.4 Reliability:** timeouts, retries with backoff, per-source locks, idempotency tests, `job_runs` records.
- **11.5 Admin endpoints:** job status, run a job now, source health.
- **11.6 Alerting:** Sentry for job failures; daily "system status" summary to admins.

**Deliverables:** worker with schedules, job monitoring.

**How you can test it**
- Leave the worker running for 24 hours on staging → new articles, papers, and a briefing appear without anyone doing anything.
- `GET /v1/admin/jobs` shows last runs, all green (or clear errors).

**Done when**
- [ ] 72 hours of unattended operation on staging without data problems
- [ ] Killing the worker mid-job and restarting causes no duplicates or lost items
- [ ] AI daily budget cap verified to pause work

---

## Phase 12 — Frontend Integration

**Goal:** The existing UI shows real data, unchanged in appearance; new pages fill the gaps.

### 12A — Connect existing pages (can start right after Phase 3)

- **12A.1 API layer:** `src/lib/api/client.ts`, generated types, `adapters.ts` (API → existing `NewsItem`/`Course`/`Opportunity`; dates/numbers formatted with `date-fns` incl. Arabic), TanStack Query hooks.
- **12A.2 Feature flag `VITE_USE_MOCK_DATA`** (default `true` until you approve switching).
- **12A.3 Home page** → `/v1/home` (SSR via route loader). Screenshot comparison.
- **12A.4 Article page** → `/v1/news/{slug}` + related items.
- **12A.5 Courses page** → `/v1/courses`, `/v1/learning-paths`.
- **12A.6 Opportunities page** → `/v1/opportunities` (+ sidebar links apply the right filter).
- **12A.7 Search modal** → `/v1/search` (grouped results, empty state).
- **12A.8 Loading/error states** using existing `SkeletonLoader` / `EmptyState`.
- **12A.9 Behaviour-preserving fixes (need approval):** theme/language cookie to remove the load flash; `AppShell` as a layout route.

### 12B — New pages (after their data exists; each design shown to you first)

- **12B.1** `/research` + `/research/:id` (paper analysis + "Ask about this paper")
- **12B.2** `/jobs` and `/opportunities/:id` ("View Opportunity" becomes real)
- **12B.3** `/tools`
- **12B.4** `/briefing` + `/briefing/:date`; "Get the briefing" → newsletter sign-up
- **12B.5** `/search` (full results page) and `/ask` (Ask NOVA, streaming)
- **12B.6** SEO: `sitemap.xml`, structured data, real Open Graph images
- **12B.7** Minimal `/admin` review queue UI (editors)

**How you can test it**
- Flip `VITE_USE_MOCK_DATA` off on staging → the site shows today's real news; screenshots of existing pages match the baseline layout.
- Switch to Arabic and dark mode → everything still works.

**Done when**
- [ ] All existing pages use the API with no visual regressions (screenshot check)
- [ ] Mock mode still works (Lovable preview safe)
- [ ] New pages approved by you and responsive in EN/AR, light/dark

---

## Phase 13 — Authentication

**Goal:** User accounts, cross-device saved content, and preferences.

**Steps**
- **13.1 Supabase Auth configuration:** email magic link + password, Google sign-in, email templates (EN/AR), redirect URLs.
- **13.2 Backend JWT verification** dependency (signature via Supabase keys, expiry, audience, issuer) + role loading; tests with signed test tokens.
- **13.3 Tables:** `profiles`, `user_interests`, `user_preferences`, `saved_items`, `interactions`, `notifications` (migration); profile auto-created on first sign-in.
- **13.4 Endpoints:** `/v1/me`, `/v1/me/preferences`, `/v1/me/interests`, `/v1/me/saved` (+ `import`), `/v1/events`.
- **13.5 Frontend:** `/login` and `/settings` pages in the existing style; navbar avatar/sign-in button; session handling with the Supabase JS client; API calls send the token.
- **13.6 Saved items migration:** on first sign-in, upload `localStorage` saved IDs and merge; opportunities and courses become saveable too.
- **13.7 Onboarding:** pick interests (the "For You" chips) and level.
- **13.8 Account rights:** export data, delete account.
- **13.9 Roles:** `editor`/`admin` gates on admin endpoints and `/admin` pages; Ask NOVA quotas now per user.

**How you can test it**
- Sign up on your phone, save an article; sign in on your computer → it's in *Saved*.
- Change language in Settings → it's remembered on every device.
- Delete your test account → sign-in no longer works and data is gone.

**Done when**
- [ ] Sign-up/in/out, magic link, Google all work
- [ ] Saved items sync across devices; old browser-saved items migrate
- [ ] A normal user cannot reach admin endpoints (tested)

---

## Phase 14 — Security

**Goal:** Independent-style review and hardening before public launch.

**Steps**
- **14.1 Checklist audit** against ARCHITECTURE §17 and the OWASP Top 10 / API Top 10.
- **14.2 Database access review:** `app` schema not exposed; RLS on every table; app role privileges minimal; test that the public Supabase key cannot read data.
- **14.3 Authorization tests:** every endpoint × every role (anonymous, user, editor, admin); users can't read others' data.
- **14.4 Rate limits and quotas** verified under load; abuse cases (newsletter spam, search flooding, Ask NOVA cost abuse).
- **14.5 Outbound fetch (SSRF) tests** against internal addresses.
- **14.6 Headers:** CSP, HSTS, etc. on frontend and API; CORS allowlist verified.
- **14.7 Automated scans:** dependency audit (`pip-audit`, Bun audit / Dependabot), OWASP ZAP baseline scan on staging.
- **14.8 Secrets rotation** procedure documented and tested; no secrets in git history (scan).
- **14.9 Privacy:** privacy policy & terms pages (text reviewed by you), data retention jobs, cookie notice if analytics added.
- **14.10 Backups:** restore production-like backup into a test project.

**Done when**
- [ ] No high/critical findings open
- [ ] Authorization matrix tests all pass
- [ ] Successful backup restore performed

---

## Phase 15 — Testing

**Goal:** Confidence that changes don't break things, with fast automated feedback.

**Steps**
- **15.1 Backend coverage:** unit tests for pure logic (parsers, dedupe, scoring, status, guards) and integration tests for every endpoint; target ≥ 80% line coverage on `services/`, `search/`, `rag/`, `ingestion/`.
- **15.2 Frontend unit tests** (Vitest) for adapters, formatting (EN/AR), query hooks.
- **15.3 End-to-end tests** (Playwright): browse home → article → save → saved page; search; filter opportunities; sign in; ask NOVA (fake AI in test mode); Arabic/RTL; mobile.
- **15.4 Visual regression** suite from Phase 1.5 extended to new pages.
- **15.5 AI evaluation suites** (Phases 7, 8, 9) runnable on demand with a cost estimate before running.
- **15.6 Load test** (e.g. k6) on home, search, and article endpoints at 5× expected launch traffic.
- **15.7 CI gates:** all of the above (except paid AI evals and load tests) required to pass before merge.

**Done when**
- [ ] CI suite < 10 minutes and required on PRs
- [ ] Load test meets latency targets at 5× traffic
- [ ] E2E suite covers every main user journey

---

## Phase 16 — Deployment

**Goal:** Launch to production safely, with monitoring and a rollback plan.

**Steps**
- **16.1 Production Supabase project `nova-prod`** (paid plan for backups/point-in-time recovery), extensions, roles, auth settings.
- **16.2 Render services:** API (web) + worker from the same image; environment variables; auto-deploy from `main` for `backend/` changes; migrations run before start.
- **16.3 Domains:** `novaai.example` (frontend) and `api.novaai.example` (API) (decision D10); HTTPS; CORS updated; Supabase auth redirect URLs updated.
- **16.4 Frontend production config:** `VITE_API_URL`, Supabase public values, `VITE_USE_MOCK_DATA=false`.
- **16.5 Monitoring:** Sentry projects, uptime checks on `/health`, alert emails; AI budget cap set for production.
- **16.6 Data bootstrap:** run ingestion + processing for a few days on production before announcing, so the site launches full.
- **16.7 Runbook:** how to deploy, roll back, rotate keys, pause AI spending, disable a bad source, restore a backup — in plain English.
- **16.8 Launch checklist** and a soft launch to a small group first.

**How you can test it**
- Visit your domain → real content, fast, in both languages.
- Follow the runbook's rollback steps on staging once, successfully.

**Done when**
- [ ] Production stable for 7 days (no critical errors, jobs green)
- [ ] Rollback and restore rehearsed
- [ ] Monthly cost tracked against the budget

---

## Phase 17 — Advanced Features

**Goal:** The features that make NOVA personal and "smart". Each item is an independent mini-project, prioritised with you.

| # | Feature | Summary | Size |
| --- | --- | --- | --- |
| 17.1 | **Personalized feed** | Scoring formula (ARCHITECTURE §12.1), user vectors job, `/v1/me/feed`, "For You" section real; diversity rules | M |
| 17.2 | **Notifications** | In-app (bell + `/notifications`), deadline reminders for saved opportunities, followed-topic alerts, preferences & quiet hours, email digests | M |
| 17.3 | **Learning recommendations** | Rules + embeddings; learning-path progress; "next step" suggestions; optional AI explanation | M |
| 17.4 | **Deep research paper analysis** | Richer `analyze_paper` (figures/sections via GROBID optional), glossary, "explain like I'm a beginner", compare two papers, related code/datasets | L |
| 17.5 | **Admin dashboard** | Sources, review queue, AI usage/cost charts, job status, user roles | M |
| 17.6 | **Personalized daily brief** | Per-user briefing variant based on interests; per-timezone sending | M |
| 17.7 | **Web push notifications / installable app (PWA)** | Opt-in browser notifications, offline reading of saved items | M |
| 17.8 | **Analytics & tuning** | Privacy-friendly analytics; tune feed/search weights from `interactions` | S |
| 17.9 | **More languages** | The `{en, ar}` design extends to more languages if desired | M |
| 17.10 | **Community features (optional)** | Comments, submissions of opportunities by users with moderation | L |

**Done when (per feature):** evaluation or user-testing criteria agreed before starting that feature.

---

## Risk Register (plan-level)

| Risk | Phase(s) | Mitigation |
| --- | --- | --- |
| Lovable sync conflicts / broken `main` | all | Branch + PR workflow, CI, mock-mode fallback, never rewrite history |
| UI accidentally changed | 12, 13 | Screenshot baseline and comparison on every frontend PR |
| AI cost overrun | 7–10 | Pre-filter, batches, caching, effort tuning, daily cap, cost dashboard |
| AI inaccuracies published | 7, 9, 10 | Guards, labels, citations, review queue, evaluation sets |
| Source terms / copyright | 4–6 | Terms review per source, summaries + links only, retention limits |
| Arabic quality | 7, 10 | Glossary, evaluation ratings, human review for featured items |
| Scope creep | all | Small PRs, phase gates, Phase 17 prioritised with you |
| Beginner operability | 16 | Plain-English runbook, managed services, dashboards |

---

## What Happens Next

1. You review `ARCHITECTURE.md` and this plan.
2. You answer the open decisions (ARCHITECTURE §23 — at minimum D1, D2, D3 to start).
3. On your go-ahead, we begin **Phase 1** only, and stop for your review when it's done.
