# NOVA AI

A bilingual (English / العربية) AI information platform: AI news and summaries, scientific research, courses, scholarships, fellowships, internships, jobs, competitions, and AI tools.

**Live app:** https://nova-platformai.lovable.app
**Lovable editor:** https://lovable.dev/projects/5e609998-42ba-4aca-a350-a298a82aaa3c

> **Current status:** frontend prototype. All content comes from built-in sample data in `src/data/`. There is no backend, database, or login yet — see the roadmap documents below.

---

## Documentation

| Document | What it contains |
| --- | --- |
| [`PROJECT_ANALYSIS.md`](PROJECT_ANALYSIS.md) | Analysis of the current codebase |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Target architecture (backend, database, AI, search) |
| [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) | Step-by-step build plan in phases |
| [`docs/ORIGINAL_DESIGN_BRIEF.md`](docs/ORIGINAL_DESIGN_BRIEF.md) | The original Lovable design brief (design-system reference) |
| [`src/routes/README.md`](src/routes/README.md) | How page routing works |

---

## Tech Stack

- **Framework:** React 19 + TanStack Start / TanStack Router (server-side rendering, file-based routes)
- **Language:** TypeScript
- **Styling:** Tailwind CSS v4 + shadcn/ui components
- **Build tool:** Vite (via `@lovable.dev/vite-tanstack-config`)
- **Package manager:** **Bun** (the lockfile is `bun.lock`)

---

## Running the Project Locally

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

A permanent bookmark (git tag) named **`v0-lovable-baseline`** marks the original Lovable version of the app, before any development work began.

| Situation | Safe way to go back |
| --- | --- |
| A merged Pull Request broke something | On GitHub, open the PR and click **Revert** → merge the new "revert" PR. History is kept; nothing is deleted. |
| You want to look at the original version | `git checkout v0-lovable-baseline` (read-only look), then `git checkout main` to return. |
| You want a working copy of the original to start again from | `git checkout -b restore-baseline v0-lovable-baseline`, then open a PR from that branch. |
| In Lovable | Use Lovable's built-in version history to restore an earlier version. |

Avoid `git reset --hard` followed by a force-push on `main` — it rewrites history and breaks the Lovable sync.

---

## Built With Lovable

This project was generated with [Lovable](https://lovable.dev). You can keep making visual changes in the [Lovable editor](https://lovable.dev/projects/5e609998-42ba-4aca-a350-a298a82aaa3c); changes made there are committed to this repository, and changes merged into `main` here sync back into Lovable.
