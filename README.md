# NOVA AI

A bilingual (English / العربية) AI information platform: AI news and summaries, scientific research, courses, scholarships, fellowships, internships, jobs, competitions, and AI tools.

**Live app:** https://nova-platformai.lovable.app
**Lovable editor:** https://lovable.dev/projects/5e609998-42ba-4aca-a350-a298a82aaa3c

> **Current status:** the website (frontend) still shows built-in sample data from `src/data/`. The backend foundation (Phase 2) exists in [`backend/`](backend/) but is **not connected to the website yet** — see the roadmap documents below.

---

## Documentation

| Document | What it contains |
| --- | --- |
| [`PROJECT_ANALYSIS.md`](PROJECT_ANALYSIS.md) | Analysis of the current codebase |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Target architecture (backend, database, AI, search) |
| [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) | Step-by-step build plan in phases |
| [`backend/README.md`](backend/README.md) | Backend developer guide (commands, structure, database, Docker) |
| [`docs/ORIGINAL_DESIGN_BRIEF.md`](docs/ORIGINAL_DESIGN_BRIEF.md) | The original Lovable design brief (design-system reference) |
| [`src/routes/README.md`](src/routes/README.md) | How page routing works |

---

## Tech Stack

- **Framework:** React 19 + TanStack Start / TanStack Router (server-side rendering, file-based routes)
- **Language:** TypeScript
- **Styling:** Tailwind CSS v4 + shadcn/ui components
- **Build tool:** Vite (via `@lovable.dev/vite-tanstack-config`)
- **Package manager:** **Bun** (the lockfile is `bun.lock`)
- **Backend:** Python 3.12 + FastAPI, PostgreSQL (SQLAlchemy + Alembic migrations), managed with **uv** — see [`backend/README.md`](backend/README.md)

---

## Running the Website (Frontend) Locally

### 1. Install the tools (one time)

- **Git** — https://git-scm.com/downloads
- **Bun** — https://bun.sh (install instructions on the homepage)
- **Node.js 22 or newer** — https://nodejs.org (some tools rely on it)

Check they are installed:

```sh
git --version
bun --version
node --version
```

### 2. Get the code

```sh
git clone https://github.com/mashwalii/nova-platformai.git
cd nova-platformai
```

### 3. Install dependencies

```sh
bun install
```

> Use **Bun**, not `npm install`. The project's exact dependency versions are locked in `bun.lock`; npm would ignore that file and may install different versions.

### 4. (Optional) Environment variables

The app currently needs **no** environment variables. When it does, copy the template:

```sh
cp .env.example .env
```

Then fill in values in `.env`. Read the warnings inside `.env.example` first — **never** put secret keys in variables that start with `VITE_`.

### 5. Start the development server

```sh
bun run dev
```

Open the address printed in the terminal (usually http://localhost:8080 or http://localhost:5173).

### Available commands

| Command | What it does |
| --- | --- |
| `bun run dev` | Start the local development server with live reload |
| `bun run build` | Create a production build |
| `bun run build:dev` | Create a development-mode build |
| `bun run preview` | Preview the production build locally |
| `bun run lint` | Check code style and common mistakes |
| `bun run format` | Auto-format code with Prettier |

---

## Running the Backend Locally

The backend is a separate program in the `backend/` folder. It runs on its own and does not change the website yet.

### 1. Install uv (one time)

uv installs Python and the backend's libraries for you. Follow the official instructions: https://docs.astral.sh/uv/getting-started/installation/

- **macOS / Linux:** `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Windows (PowerShell):** `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`

Close and reopen your terminal, then check: `uv --version`

### 2. Install the backend's dependencies

```sh
cd backend
uv sync
```

### 3. Start the backend

```sh
uv run python -m app
```

Leave this terminal window open — the backend runs as long as it stays open. Stop it with **Ctrl + C**.

### 4. Check that it works

Open these addresses in your web browser:

- http://127.0.0.1:8000/health → should show `{"status":"ok","service":"NOVA AI API","version":"0.1.0"}`
- http://127.0.0.1:8000/docs → interactive page listing every API endpoint
- http://127.0.0.1:8000/ready → shows `"not_configured"` until a database is connected (this is expected)

### 5. Run the tests

In a second terminal window:

```sh
cd backend
uv run pytest
```

The last line should say **passed** (for example `62 passed, 13 skipped`) and must not mention **failed**. Skipped tests need a separate test database — see [`backend/README.md`](backend/README.md#running-the-database-tests).

### Optional: settings and database

- Settings: copy `backend/.env.example` to `backend/.env` and edit your copy. **Never commit `.env`.**
- Database: put your PostgreSQL/Supabase connection string in `backend/.env` as `DATABASE_URL=...`, then run `uv run alembic upgrade head`. Full steps: [`backend/README.md`](backend/README.md#connecting-a-database).

---

## Project Structure

```
src/
├── routes/        # Pages (file-based routing): home, article, courses, opportunities, saved
├── components/    # NOVA UI components (Navbar, Sidebar, NewsCard, …)
│   └── ui/        # shadcn/ui building blocks
├── contexts/      # Global state: language, theme, saved articles
├── data/          # Sample (mock) content — replaced by the API in later phases
├── assets/        # Images
├── lib/           # Utilities and error handling
└── styles.css     # Design system (colors, dark mode, shadows)
public/            # Static files (favicon, robots.txt)
docs/              # Project documents
backend/           # Python/FastAPI backend (see backend/README.md)
.github/workflows/ # Automatic checks that run on GitHub
```

`src/routeTree.gen.ts` is generated automatically — do not edit it by hand.

---

## Safe Development Workflow

This repository is connected to **Lovable**: commits on `main` sync into the Lovable editor, and edits made in Lovable are committed to `main`.

1. **Never work directly on `main`.** Create a branch for each change:
   ```sh
   git checkout main
   git pull origin main
   git checkout -b my-change-name
   ```
2. Commit your work on the branch and push it:
   ```sh
   git push -u origin my-change-name
   ```
3. Open a **Pull Request** on GitHub, review it, and merge only when it works.
4. **Never rewrite published history** — no `git push --force`, and no rebasing, amending, or squashing of commits that are already pushed. It breaks Lovable's project history (see `AGENTS.md`).
5. **Never commit secrets.** `.env` files, keys, and credential files are blocked by `.gitignore`. If a secret is ever committed by accident, treat it as leaked: revoke/rotate the key immediately — deleting the file afterwards is not enough, because it stays in git history.

---

## Restoring a Previous Version

The original Lovable version of the app, before any development work began, is commit **`5da6499`** ("Add project README"). Every commit ID is permanent, so this version can always be recovered.

*Recommended:* give it an easy-to-remember name by creating a tag called **`v0-lovable-baseline`** — on GitHub: **Releases → Draft a new release → Choose a tag → type `v0-lovable-baseline` → Target: pick commit `5da6499` via "Recent commits"** → Publish (or from a terminal: `git tag v0-lovable-baseline 5da6499 && git push origin v0-lovable-baseline`). Once it exists, you can use `v0-lovable-baseline` anywhere `5da6499` appears below.

| Situation | Safe way to go back |
| --- | --- |
| A merged Pull Request broke something | On GitHub, open the PR and click **Revert** → merge the new "revert" PR. History is kept; nothing is deleted. |
| You want to look at the original version | `git checkout 5da6499` (read-only look), then `git checkout main` to return. |
| You want a working copy of the original to start again from | `git checkout -b restore-baseline 5da6499`, then open a PR from that branch. |
| In Lovable | Use Lovable's built-in version history to restore an earlier version. |

Avoid `git reset --hard` followed by a force-push on `main` — it rewrites history and breaks the Lovable sync.

---

## Built With Lovable

This project was generated with [Lovable](https://lovable.dev). You can keep making visual changes in the [Lovable editor](https://lovable.dev/projects/5e609998-42ba-4aca-a350-a298a82aaa3c); changes made there are committed to this repository, and changes merged into `main` here sync back into Lovable.
