# NOVA AI — Database Guide

This document explains how NOVA stores its information, in plain language. You don't need to know SQL to follow it.

> **Status:** Phase 3. The database structure exists and is filled with sample data for development. The website does **not** read from it yet (that's Phase 12).

---

## 1. The big picture

A **database** is an organised collection of **tables**. A table is like a spreadsheet:

* each **row** is one thing (one article, one user, one saved item);
* each **column** is one piece of information about it (title, date, status).

NOVA uses **PostgreSQL**, a free, very reliable database used by large companies. In production it will be hosted by **Supabase**, which runs PostgreSQL for us, handles backups, and also provides user login (authentication).

All of NOVA's tables live in a separate section of the database called the **`app` schema**. Think of a schema as a folder: keeping NOVA's tables in their own folder means Supabase's built-in public data access can't see them, and they never mix with Supabase's own tables.

There are **27 tables**, in six groups:

| Group | Tables | What it holds |
| --- | --- | --- |
| **Reference data** | `sources`, `authors`, `categories`, `tags` | Where content comes from and how it's organised |
| **Content** | `content_items` + `articles`, `papers`, `courses`, `opportunities`, `ai_tools`, `learning_paths`, `learning_path_steps`, `content_authors`, `content_tags` | Everything shown on the site |
| **AI outputs** | `ai_summaries`, `ai_classifications`, `embeddings` | What the AI wrote or decided about each item |
| **Users** | `users`, `user_preferences`, `user_interests`, `saved_items`, `notifications` | People and their personal data |
| **Daily briefs** | `daily_briefs`, `daily_brief_items` | The daily AI briefing |
| **Operations** | `collection_jobs`, `processing_logs`, `error_logs` | Records of background work and problems |

---

## 2. Key ideas (read this first)

### Primary keys: every row has a unique ID
Every row has an **ID** that never changes. Most tables use a **UUID**, a long random identifier like `2f1c9a5e-…`, which is safe to show in web addresses and can be created anywhere without clashing. The three fast-growing log tables (`processing_logs`, `error_logs`, `embeddings`) use simple counting numbers (1, 2, 3 …) because they're smaller and faster.

### Foreign keys: links between tables
A **foreign key** is a column that points to a row in another table — for example, `saved_items.user_id` points to a user. The database **refuses** links to things that don't exist, so data can't become inconsistent.

Each link also says **what happens when the linked row is deleted**:

| Rule | Meaning | Example |
| --- | --- | --- |
| **CASCADE** | Delete the dependent rows too | Delete a user → their saved items, preferences and notifications are deleted |
| **SET NULL** | Keep the row, just remove the link | Delete a category → its articles stay, with no category |

### One shared content table + a details table per type
Every article, paper, course, opportunity and AI tool has **one row in `content_items`** (title, summary, status, dates …). The details that only make sense for one type live in a separate **details table** that shares the same ID:

```
content_items (id = 7f3…, type = "course", title = "Python for AI Builders", …)
      └── courses (content_id = 7f3…, provider = "DeepLearning.AI", level = "beginner", …)
```

**Why?** Saving, search, AI summaries, embeddings, notifications and briefings then work the same way for **every** kind of content, with one piece of code.

### Two languages side by side
Text that users read exists in English and Arabic as **pairs of columns**: `title_en` / `title_ar`, `summary_en` / `summary_ar`, and so on. The API will return them as `{ "en": "…", "ar": "…" }`, which is exactly the format the website already uses.

### Allowed values
Columns like `status` or `opportunity_type` only accept a fixed list of values (for example `draft`, `published`, `archived`). The database rejects anything else. The lists are in `backend/app/models/enums.py` and in section 4 below.

### Timestamps
Every table records **when a row was created** (`created_at`, or `occurred_at` for errors). Tables whose rows get edited also have **`updated_at`**, which the database updates **automatically** on every change, even when someone edits a row directly in the Supabase dashboard. All times are stored in **UTC** and converted to the reader's time zone on the website.

### Indexes: the database's "table of contents"
An **index** lets the database find rows quickly without reading the whole table, like the index at the back of a book. NOVA has indexes for every common lookup: newest published articles, a user's saved items, unread notifications, opportunities by deadline, every link between tables, fuzzy title search, and similarity search on embeddings.

### Unique constraints: no duplicates
Some values must be unique: a source's `slug`, a user's e-mail (ignoring upper/lower case), the same article saved twice by one user, the same link collected twice (`url_hash`), and so on.

---

## 3. How the tables connect

```mermaid
erDiagram
  sources ||--o{ content_items : "provides"
  categories ||--o{ content_items : "classifies"
  categories ||--o{ categories : "parent of"
  content_items ||--o| articles : "details"
  content_items ||--o| papers : "details"
  content_items ||--o| courses : "details"
  content_items ||--o| opportunities : "details"
  content_items ||--o| ai_tools : "details"
  content_items ||--o{ content_authors : ""
  authors ||--o{ content_authors : "wrote"
  content_items ||--o{ content_tags : ""
  tags ||--o{ content_tags : "labels"
  learning_paths ||--o{ learning_path_steps : "has"
  content_items ||--o{ learning_path_steps : "course for step"
  content_items ||--o{ ai_summaries : "summarised by"
  content_items ||--o{ ai_classifications : "classified by"
  content_items ||--o{ embeddings : "represented by"
  users ||--o| user_preferences : "has"
  users ||--o{ user_interests : "follows"
  categories ||--o{ user_interests : ""
  users ||--o{ saved_items : "saves"
  content_items ||--o{ saved_items : ""
  users ||--o{ notifications : "receives"
  daily_briefs ||--o{ daily_brief_items : "contains"
  content_items ||--o{ daily_brief_items : ""
  sources ||--o{ collection_jobs : "collected by"
  collection_jobs ||--o{ processing_logs : ""
  content_items ||--o{ processing_logs : ""
  collection_jobs ||--o{ error_logs : ""
```

(GitHub shows this as a diagram. `||--o{` means "one … to many", `||--o|` means "one … to at most one".)

---

## 4. Every table explained

### 4.1 Reference data

**`sources`**: places content comes from (an RSS feed, arXiv, a job board, or manual entry by editors).
Key columns: `slug` (unique short name), `name`, `kind` (`rss`, `arxiv`, `api`, `job_board`, `website`, `manual`), `feed_url`, `trust_level` (1–5), `is_active`, `fetch_interval_minutes`, `config` (non-secret settings, e.g. which arXiv categories), plus health fields updated by collectors (`last_fetched_at`, `last_success_at`, `consecutive_failures`, `etag`, `last_modified`).
⚠️ **No API keys here**; they live in environment variables.

**`authors`**: people who wrote articles or papers. `name`, `name_ar`, `affiliation`, `orcid` (a researcher ID, unique), `homepage_url`.

**`categories`**: the curated topic list ("AI Research", "Robotics", course categories …). Bilingual names, optional `parent_id` for sub-categories, optional `content_type` to limit a category to one kind of content (e.g. course categories), `sort_order`, `is_active`.

**`tags`**: free-form keywords ("multimodal", "open-weights"). Many per item.

### 4.2 Content

**`content_items`**: one row for **every** piece of content.

| Column | Meaning |
| --- | --- |
| `content_type` | `article`, `paper`, `course`, `opportunity`, `tool` |
| `slug` | web-address name, unique **within** its type (`/article/benchmark`) |
| `status` | `draft` → `ingested` → `processing` → `needs_review` → `published` (or `rejected` / `archived`) |
| `title_en/ar`, `summary_en/ar` | text shown to readers (at least one title is required) |
| `source_id`, `category_id` | links to `sources` and `categories` |
| `original_language` | `en` or `ar` |
| `canonical_url`, `url_hash` | original link; the hash stops the same link being stored twice |
| `image_url` | preview image |
| `published_at`, `source_updated_at` | when it was published / last updated by the source |
| `importance` (1–5), `is_featured`, `is_trending`, `trending_score`, `view_count` | ranking signals |
| `ai_generated` | true if the text was written by AI |
| `extra` | flexible extra data (e.g. which built-in image to show) |

**`articles`**: news details: `reading_minutes`, `word_count`, `body_text` (the extracted article text, used **internally only** for AI processing and never shown in full), `body_retained_until` (when that text will be deleted).

**`papers`**: research papers: `arxiv_id` and `doi` (both unique), `abstract`, `subject_areas` (e.g. `cs.CL`), `pdf_url`, `code_url`, `venue`, `citation_count`, `full_text` (internal), `license`.

**`courses`**: `provider`, `level` (`beginner`, `intermediate`, `advanced`, `all_levels`), `duration_hours` and bilingual `duration_label`, `instruction_language_en/ar`, `is_free`, `has_certificate`, `enrollment_url`.

**`opportunities`**: **scholarships, fellowships, internships, jobs, competitions, hackathons, bootcamps and research programmes** in one table.
`opportunity_type` says which. Shared fields: `organization`, bilingual `location` and `eligibility`, `country_code`, `is_remote`, `deadline_at`, `starts_at`, `ends_at`, `apply_url`, bilingual `funding`. Job-only fields (empty for other types): `employment_type` (`full_time`, `part_time`, `contract`, `temporary`, `internship`), `seniority`, `salary_text`.
*Why one table?* Most fields are shared, and one table makes "all opportunities closing this week" a single fast query. "Open / closing soon / closed" is **calculated** from `deadline_at`, not stored, so it's never out of date.

**`ai_tools`**: tools directory: `website_url`, `pricing` (`free`, `freemium`, `paid`, `open_source`, `enterprise`), `vendor`, `platforms`, `has_api`, `repository_url`.

**`learning_paths`** and **`learning_path_steps`**: ordered study paths (e.g. *AI Engineer: Python → Data Science → Machine Learning → AI Systems*). Each step has a `position` (unique within its path) and can link to a course.

**`content_authors`**: who wrote what, in order (`position`).
**`content_tags`**: tags on each item, with `origin` (`editor`, `ai`, `source`) and, for AI-suggested tags, a `confidence` between 0 and 1.

### 4.3 AI outputs

Every AI result records the `model` and `prompt_version` that produced it and links to the `processing_logs` row of that run, so any result can be traced and compared. Old versions are kept with `is_current = false`.

**`ai_summaries`**: an AI-written summary of one item **in one language**.
`kind` (`article_brief`, `paper_analysis`, `short`), `language`, `tldr`, `key_points` (list), `why_it_matters`, and `sections` holding the structured parts of the Article page (what happened, "by the numbers" metrics, quote, timeline) or a paper analysis. `reviewed_by` / `reviewed_at` record human review.
Rule: only **one current** summary per item, kind and language.

**`ai_classifications`**: what the AI decided: `is_relevant`, `suggested_category_id`, `importance` (1–5), `confidence` (0–1), and detailed `labels`. Only one current classification per item.

**`embeddings`**: lists of 1,024 numbers that represent the *meaning* of a text, used for meaning-based search, "related content" and question answering (Phases 8–9). `kind` is `document` (one per item) or `chunk` (one per passage). They're stored with the **pgvector** extension, with a special index for fast "most similar" searches.
Rule: all embedding models must produce **1,024** numbers; changing models means re-creating embeddings (the `model` column says which model made each one).

### 4.4 Users

**`users`**: one row per person. The `id` is **the same ID Supabase Auth gives them**. **Passwords are never stored here**; Supabase Auth handles login. Columns: `email` (unique, ignoring case), `display_name`, `role` (`user`, `editor`, `admin`), `status` (`active`, `suspended`, `deleted`), `onboarding_completed_at`, `last_seen_at`.
There is deliberately no hard database link to Supabase's internal `auth` tables, so the same structure also works on a plain PostgreSQL for development and tests. The backend keeps the two in sync (Phase 13).

**`user_preferences`**: exactly one row per user: `language`, `theme` (`light`, `dark`, `system`), `timezone`, `email_digest` (`off`, `daily`, `weekly`), `notify_deadlines`, `notify_topic_updates`, quiet hours.

**`user_interests`**: categories a user follows, each with a `weight` (0–1) for personalisation.

**`saved_items`**: bookmarks. Works for **any** content type. A user can save an item only once.

**`notifications`**: in-app notifications (the bell icon): `kind` (`deadline_reminder`, `topic_update`, `daily_brief`, `system`), bilingual title/body, optional linked content, `read_at` (empty = unread), `emailed_at`.

### 4.5 Daily briefs

**`daily_briefs`**: one per day (`brief_date` is unique): `status` (`draft`, `published`, `archived`), bilingual `headline`, `intro` and "one essential `signal`", `published_at`, and which AI `model` wrote it.

**`daily_brief_items`**: the stories in a brief, in order (`position`), with a short bilingual `blurb`. The same item can't appear twice in one brief.

### 4.6 Operations

**`collection_jobs`**: one row per run of a background task (e.g. "fetch source X"): `job_type`, `source_id`, `status` (`queued`, `running`, `succeeded`, `failed`, `cancelled`), `trigger` (`schedule`, `manual`, `retry`), start/finish times, counts of items found/created/updated/failed, `error_message`.

**`processing_logs`**: one row per pipeline step for one item (`fetch`, `extract`, `deduplicate`, `classify`, `summarize`, `translate`, `embed`, `publish`) with its `status` (`started`, `succeeded`, `failed`, `skipped`). AI steps also record `provider`, `model`, `prompt_version`, `input_tokens`, `output_tokens`, `cost_usd` and `duration_ms`. This powers the AI cost dashboard and the daily budget cap.

**`error_logs`**: problems worth keeping: `severity` (`warning`, `error`, `critical`), `component` (api, worker, collector, ai …), `error_type`, `message`, `stack_trace`, `context`, `request_id`, and `resolved_at`.
Always write errors with `ErrorLogRepository.record(...)`, which **automatically removes passwords, tokens and keys** before saving.

---

## 5. Security and privacy

| Protection | How |
| --- | --- |
| No secrets in the database | No password/API-key columns (a test fails if one is added). Keys live in environment variables. |
| No secrets in source code | Connection strings come from `backend/.env` (never committed) or the hosting provider's settings. |
| Hidden from the public API | Tables are in the `app` schema, which Supabase's public data API doesn't expose; access for the public roles is revoked. |
| Row-Level Security | Switched on for every table (a test checks this). The backend connects as the table owner and is unaffected; anyone else is blocked by default. |
| Personal data removal | Deleting a user automatically deletes their preferences, interests, saved items and notifications. |
| Copyright | Full article/paper text (`body_text`, `full_text`) is for internal processing only and has a retention date. |
| Error logs | Credentials are scrubbed before storage. |

---

## 6. Development seed data

A small set of **sample data** lets you develop and test without collecting real content. It lives in `backend/app/seed/data/dev_seed.json`:

| What | How many | Where it comes from |
| --- | --- | --- |
| Articles (with English + Arabic AI-style summaries) | 7 | The website's current sample articles (`src/data/mockNews.ts`) |
| Courses and learning paths | 6 + 2 | The website's sample courses (`src/data/mockLearning.ts`) |
| Opportunities (all 8 types, incl. a job) | 8 | The website's 6 samples + 2 new sample listings |
| Research papers | 2 | Real, famous papers (links and authors), summaries written by NOVA |
| AI tools | 4 | Real open-source tools, descriptions written by NOVA |
| Sources, categories, tags, authors | 10 / 21 / 14 / 13 | Matching the above |
| Users | 2 | **Fake** people (`admin@example.com`, `reader@example.com`) with preferences, interests, saved items and notifications |
| Daily brief, collection jobs, processing logs, error log | a few | Examples |

It contains **no embeddings**, since those are produced by an AI embedding model in Phase 8.

**Load it** (development or test databases only; the command refuses to run in staging/production):

```sh
cd backend
uv run python -m app.cli seed
```

It's safe to run repeatedly: every sample row has a fixed ID, so running it again **updates** rows instead of creating duplicates.

---

## 7. Setting up a database

### Option A: Supabase (recommended)
1. Create a free project at https://supabase.com (e.g. `nova-dev`). Save the database password in a password manager.
2. In the project, open **Connect** (or *Project Settings → Database*) and copy the **URI** connection string. Use the *direct* or *session pooler* connection for migrations.
3. Put it in `backend/.env` (never committed):
   ```
   DATABASE_URL=postgresql://postgres:YOUR-PASSWORD@db.YOUR-PROJECT.supabase.co:5432/postgres?sslmode=require
   ```
4. Create the tables and load sample data:
   ```sh
   cd backend
   uv run alembic upgrade head
   uv run python -m app.cli seed
   uv run python -m app.cli check-db
   ```
5. In Supabase's **Table Editor**, switch the schema dropdown from `public` to `app` to browse the tables.

The migration turns on the `vector` and `pg_trgm` extensions itself (in Supabase's `extensions` schema). If your project restricts that, enable both in **Database → Extensions** first.

### Option B: PostgreSQL on your own computer
Install PostgreSQL 16+ **with the pgvector extension** (e.g. the Docker image `pgvector/pgvector:pg16`), create a database, set `DATABASE_URL=postgresql://USER:PASSWORD@localhost:5432/nova`, then run the same commands as step 4.

---

## 8. Migrations: changing the structure safely

A **migration** is a small, numbered script that changes the database structure (adds a table, a column, an index …). Migrations run **in order**, and every one can also be **undone**. The database remembers which ones it already has, so running them again does nothing.

| Migration | What it does |
| --- | --- |
| `0001_baseline` | Creates the `app` schema's security settings and the automatic `updated_at` helper |
| `0002_core_schema` | Creates the 27 tables, their links, rules and indexes; enables `vector` and `pg_trgm`; turns on Row-Level Security; adds `updated_at` triggers |

Useful commands (run in `backend/`):

| Command | What it does |
| --- | --- |
| `uv run alembic upgrade head` | Apply all migrations not yet applied |
| `uv run alembic current` | Show which migration the database is on |
| `uv run alembic downgrade -1` | Undo the most recent migration (**deletes data** in affected tables) |
| `uv run alembic check` | Confirm the models and migrations match |

**Adding or changing a table** (developer workflow):
1. Edit or add a model in `backend/app/models/`.
2. `uv run alembic revision --autogenerate -m "describe the change"`.
3. **Read the generated file** in `alembic/versions/`, and add the `updated_at` trigger and Row-Level Security for new tables (tests will remind you).
4. `uv run alembic upgrade head`, then `uv run pytest` with `TEST_DATABASE_URL` set.
5. Commit the model, the migration and tests together.

Never edit a migration that has already been applied to a shared database (staging/production). Add a new one instead.

---

## 9. What's intentionally not here yet

| Planned | Phase |
| --- | --- |
| Full-text search columns (keyword search in English and Arabic) | 8 — Search |
| Text chunks for question answering | 9 — RAG (the `embeddings` table already supports chunks) |
| Story clusters (grouping articles about the same event) | 7 — AI processing |
| Newsletter subscribers without an account | 10 — Daily brief |
| Reading history / interaction events for personalisation | 17 — Advanced features |
| Automatic sync with Supabase Auth users | 13 — Authentication |

Adding these later is a normal migration and won't require changing existing tables.
