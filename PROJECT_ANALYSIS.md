# NOVA AI — Project Analysis

> **Scope of this document:** a read-only inspection of the repository as of commit `5da6499` ("Add project README").
> Nothing in the application was changed, installed, deleted, or refactored to produce this report.
> Dependencies were **not** installed, so the app was not built or linted; all findings come from reading the source.

---

## Project Overview

**NOVA AI** is a bilingual (English / Arabic) AI news and intelligence platform generated with **Lovable** and synced to this GitHub repository.

What exists today is a **polished, frontend-only prototype**. Every piece of content — news articles, AI summaries, courses, and opportunities — is **hard-coded sample ("mock") data** stored in three TypeScript files. There is no backend, no database, no user accounts, and no connection to any outside data source.

The original Lovable brief (still visible at the top of `README.md`) explicitly said:

> "FRONTEND UI/UX ONLY. No backend, database, authentication, or live APIs. Built strictly with realistic, structured mock data … designed for seamless drop-in API replacement later."

So the current state is intentional, and the codebase was designed with a future backend in mind.

| Item | Value |
| --- | --- |
| Live preview | https://nova-platformai.lovable.app |
| Lovable project | `5e609998-42ba-4aca-a350-a298a82aaa3c` |
| Lovable template | `tanstack_start_ts_current` (revision `ad123148fd3e`) |
| Git history | 15 commits, all by Lovable bots, 18–21 Sep 2026 |
| Custom source code | ~20 hand-written files (the rest is template / UI library) |

---

## Current Architecture

```
┌──────────────────────────────── Browser ────────────────────────────────┐
│                                                                          │
│   Pages (src/routes/*)  ──uses──►  Components (src/components/*)          │
│         │                                   │                            │
│         │ import                            │ useApp()                   │
│         ▼                                   ▼                            │
│   Mock data files                    AppContext (language, theme,        │
│   (src/data/*.ts)                    saved articles)                     │
│                                             │                            │
│                                             ▼                            │
│                                      localStorage (browser only)        │
└──────────────────────────────────────────────────────────────────────────┘
                     ▲
                     │ HTML (server-side rendered)
┌──────────── Server (TanStack Start + Nitro, Cloudflare by default) ──────┐
│  src/server.ts  → only renders pages & an error page. No data, no APIs. │
└──────────────────────────────────────────────────────────────────────────┘
```

- **Rendering:** TanStack Start does *server-side rendering* (SSR): the first HTML is produced on a server, then React takes over in the browser.
- **Server:** exists only as the SSR runtime (`src/server.ts`, `src/start.ts`). It contains error handling and CSRF protection middleware, but **no business logic, no API endpoints, and no server functions**.
- **Data:** imported directly from `src/data/*.ts` into pages. There is no data-access layer in between.
- **Deployment target:** the Lovable Vite config builds with Nitro using **Cloudflare** as the default target (per comment in `vite.config.ts`). Hosting is currently handled by Lovable.

---

## Frontend Stack

### 1. Framework
- **React 19** (`react@^19.2.0`)
- **TanStack Start 1.168** (full-stack React framework with SSR) + **TanStack Router 1.170** (file-based routing)

### 2. Programming languages
- **TypeScript** (all source, `strict` mode with extra-strict options such as `noUncheckedIndexedAccess` and `exactOptionalPropertyTypes`)
- **CSS** via Tailwind (`src/styles.css`)
- No JavaScript source files other than `eslint.config.js`.

### 3. Build system
- **Vite 8.1.5** (bleeding edge) wrapped by `@lovable.dev/vite-tanstack-config`, which silently adds: TanStack Start, React plugin, Tailwind, path aliases, Nitro (build only), `VITE_*` env injection, and Lovable error logging.
- **Nitro 3 beta** (`3.0.260603-beta`) for the server bundle.
- `rolldown` pinned to `1.2.1` via `overrides`.
- Scripts: `dev`, `build`, `build:dev`, `preview`, `lint`, `format`.

### 4. Package manager
- **Bun** — evidenced by `bun.lock` and `bunfig.toml` (which also sets a 24-hour "don't install freshly published packages" supply-chain guard).
- ⚠️ The README tells people to use `npm i`. There is no `package-lock.json`, so npm would resolve versions independently from Bun. This is an inconsistency to fix later.

### 5. Important dependencies

| Purpose | Package(s) | Actually used? |
| --- | --- | --- |
| UI framework | `react`, `react-dom` | ✅ |
| Routing / SSR | `@tanstack/react-router`, `@tanstack/react-start` | ✅ |
| Data fetching / caching | `@tanstack/react-query` | ⚠️ Provider set up, **never used** |
| Styling | `tailwindcss` v4, `tw-animate-css`, `tailwind-merge`, `clsx`, `class-variance-authority` | ✅ |
| UI primitives | ~27 `@radix-ui/*` packages via **shadcn/ui** | ⚠️ Only `Button` and `Toaster` used |
| Icons | `lucide-react` | ✅ |
| Toast notifications | `sonner` | ✅ |
| Forms & validation | `react-hook-form`, `@hookform/resolvers`, `zod` | ❌ Installed, unused |
| Dates | `date-fns`, `react-day-picker` | ❌ Unused |
| Charts | `recharts` | ❌ Unused |
| Misc UI | `cmdk`, `embla-carousel-react`, `vaul`, `input-otp`, `react-resizable-panels` | ❌ Unused |
| Code quality | `eslint` 9, `typescript-eslint`, `prettier` 3 | Configured |

The unused packages come from the Lovable/shadcn template. They are harmless but add weight; several (`zod`, `react-hook-form`, `react-query`, `date-fns`) will be genuinely useful once a backend exists.

### 6. Existing pages (routes)

| URL | File | What it shows |
| --- | --- | --- |
| `/` | `src/routes/index.tsx` | Home "intelligence briefing": headline stats, lead story, Trending, Most Important, For You, Most Discussed, Research & Models, Opportunities preview, Courses preview, newsletter banner |
| `/article/:id` | `src/routes/article.$id.tsx` | Article detail: title, metadata, save/share, AI-summary box (TL;DR, key takeaways, why it matters), "What happened", metrics, quote, timeline, original-source card, related stories. Unknown IDs → 404 |
| `/courses` | `src/routes/courses.tsx` | Featured courses, category filter, course grid, two "learning paths" |
| `/opportunities` | `src/routes/opportunities.tsx` | Category filter + opportunity cards (scholarships, internships, competitions, fellowships, bootcamps, hackathons, research) |
| `/saved` | `src/routes/saved.tsx` | User's saved articles with tabs (All / News / Research / Models), remove & share, empty state |
| (any other) | `src/routes/__root.tsx` | Custom 404 page and error page |

Every page sets its own SEO `<title>` / description / Open Graph tags.

### 7. Existing components (custom, in `src/components/`)

| Component | Role | Used? |
| --- | --- | --- |
| `AppShell` | Page frame: Navbar + Sidebar + main area + **search modal** (⌘K) | ✅ every page |
| `Navbar` | Top bar: logo, Home/Courses/Opportunities links, search, language switch, theme toggle, saved count, bell | ✅ |
| `Sidebar` | Left navigation (collapsible on desktop, drawer on mobile) | ✅ |
| `FeaturedNewsCard` | Large lead-story card | ✅ |
| `NewsCard` | Standard article card | ✅ |
| `SectionHeader` | Section title with eyebrow text | ✅ |
| `CategoryBadge`, `SourceBadge` | Small labels | ✅ |
| `SaveButton`, `ShareButton` | Bookmark and copy-link buttons | ✅ |
| `ThemeToggle`, `LanguageSwitcher` | Light/dark and EN/العربية | ✅ |
| `PageHeader` | Alternative page header | ❌ unused (hard-coded "Monday, Sep 21") |
| `EmptyState` | "No intelligence found" block | ❌ unused |
| `SkeletonLoader` | Loading placeholder | ❌ unused (will be useful with real data) |

Plus **46 shadcn/ui components** in `src/components/ui/` (template-provided library; only `button` and `sonner` are used).

### 8. Existing layouts
- **Root layout** (`src/routes/__root.tsx`): HTML document shell, fonts (Geist + IBM Plex Sans Arabic from Google Fonts), React Query provider, `AppProvider`, toast container.
- **`AppShell`**: not a router layout — each page wraps itself in `<AppShell>`. Consequence: the shell re-mounts on each navigation, so e.g. the sidebar "collapsed" state resets when you change pages.
- Fully responsive (desktop sidebar, collapsible, mobile drawer) and **RTL-aware** for Arabic (uses logical `ms-`/`me-`/`start`/`end` classes and flips `dir`).

### 9. State management
- One React Context: **`AppContext`** (`src/contexts/AppContext.tsx`) holding:
  - `language` (`"en"` | `"ar"`) → persisted in `localStorage["nova-language"]`
  - `dark` theme flag → `localStorage["nova-theme"]`
  - `saved` article IDs → `localStorage["nova-saved"]`
  - helper actions `toggleSaved`, `isSaved`, `share`, `toggleTheme`
- Local component state (`useState`) for filters, tabs, search query, sidebar/modal visibility.
- Opportunity "Save" uses **separate, non-persisted** local state (lost on page change).
- No Redux/Zustand; React Query is present but unused.

### 10. Existing API calls
**None.** No `fetch`, no `axios`, no server functions (`createServerFn`), no `useQuery`. The only "fetch" in the code is the SSR server's own request handler.

### 11. Existing mock data

| File | Contents |
| --- | --- |
| `src/data/mockNews.ts` | Types `Language`, `Localized`, `NewsItem`, `TimelineItem`; **7 articles** (all fully bilingual, with TL;DR, takeaways, metrics, quote, timeline); 13 category labels; helpers `text()` and `getArticle()`; unused exports `featuredStory`, `briefs`, `spotlight`, `categories` |
| `src/data/mockLearning.ts` | Type `Course`; 9 course categories; **6 courses** (links to real platforms' home pages); **2 learning paths** |
| `src/data/mockOpportunities.ts` | Type `Opportunity`; 8 categories; **6 fictional opportunities** (no links) |
| `src/assets/*.jpg` | 4 images reused across all articles and courses |

Notable data-shape details that matter for a backend:
- Every human-readable string is a `{ en, ar }` pair ("Localized").
- Dates and relative times are **pre-written text** ("Sep 21, 2026", "Updated 28 min ago"), not real timestamps.
- Views and comments are **text** ("12.8K", "184"), not numbers.
- Several `originalUrl` values are `https://example.com/`.
- The same `sharedTimeline` is reused by most articles.

### 12. Existing backend
**None** beyond the SSR runtime described above.

### 13. Existing database
**None.**

### 14. Existing authentication
**None.** No sign-up, login, profile, or session. The avatar/profile mentioned in the original brief is not present in the current Navbar.

### 15. Existing search
- Search modal in `AppShell`, opened by the Navbar button or **⌘K / Ctrl+K**, closed with Esc.
- Case-insensitive substring match on **article title + summary** in the current language, across the 7 mock articles only.
- Does **not** search courses or opportunities; no "no results" message (the list just goes empty); results list all articles when the box is empty.

### 16. Existing filtering
- **Courses:** category buttons (All, Programming, AI, ML, Data Science, CS, Math, Web Dev, Cybersecurity) — works.
- **Opportunities:** category buttons — works.
- **Saved:** tabs All / News / Research / Models — works, but categorisation is a rough text match on category names.
- **Home "For You" topic chips:** visual only; clicking does nothing.
- No filtering of news by category (sidebar category links all go to `/`).

### 17. Existing forms
**No real forms.** The only input is the search box. The "Get the briefing" newsletter button has no email field and does nothing. `react-hook-form` + `zod` are installed but unused.

### 18. Environment variables
**None defined or read.** No `.env` files, no `import.meta.env` / `process.env` usage. (The Lovable Vite config will automatically expose any variable prefixed `VITE_` to the browser — important to remember for security later.)

### 19. Existing integrations
- **Lovable:** editor sync (commits to `main` sync back to Lovable), error reporting (`src/lib/lovable-error-reporting.ts`, only active inside the Lovable preview), build config.
- **Google Fonts** (Geist, IBM Plex Sans Arabic).
- **Clipboard API** for "Share" (copies `/article/:id` link).
- Outbound links to external sites (course platforms, arXiv, Hugging Face, example.com).
- No analytics, no email, no payments, no AI APIs, no CMS.

---

## Backend Status

| Aspect | Status |
| --- | --- |
| Custom server code | ❌ None (only SSR + error handling) |
| API endpoints | ❌ None |
| Server functions | ❌ None (CSRF middleware is pre-configured for them) |
| Background jobs / scheduled tasks | ❌ None |
| News ingestion (RSS, APIs, scraping) | ❌ None |
| AI summarisation / translation | ❌ None — all "AI-generated summaries" are hand-written mock text |
| Email / newsletter | ❌ None |

The framework (TanStack Start) **is capable** of hosting backend logic via server functions and server routes, so a backend can be added without changing frameworks.

---

## Database Status

**No database.** All content is compiled into the JavaScript bundle. The only persistence is the browser's `localStorage` (language, theme, saved IDs), which is per-device, per-browser, and lost if the user clears their browser data.

---

## API Status

**No API layer exists** — neither consumed nor exposed. Pages import arrays directly (e.g. `import { articles } from "@/data/mockNews"`) and use them synchronously. There are no loading states, error states, or pagination, because data is always instantly available.

The one hopeful sign: `article.$id.tsx` already uses a **route `loader`** (`getArticle(params.id)`), which is exactly the pattern a real data fetch would use.

---

## Authentication Status

**Not implemented.** No login, sign-up, password reset, social login, sessions, protected pages, user profiles, or roles (e.g. admin/editor). "Saved Articles" works only because it's stored in the browser, not tied to a person.

---

## Current Data Flow

```
src/data/mockNews.ts ──import──► routes/index.tsx, article.$id.tsx, saved.tsx, AppShell (search)
src/data/mockLearning.ts ──import──► routes/courses.tsx, routes/index.tsx
src/data/mockOpportunities.ts ──import──► routes/opportunities.tsx, routes/index.tsx

User clicks "Save" ──► AppContext.toggleSaved ──► React state + localStorage["nova-saved"] ──► toast
User switches language ──► AppContext ──► <html lang dir> + localStorage ──► text(value, language)
User toggles theme ──► AppContext ──► <html class="dark"> + localStorage
User clicks "Share" ──► navigator.clipboard ──► toast
```

Because `localStorage` is read *after* the page first renders (in a `useEffect`), a returning user in dark mode or Arabic briefly sees the light/English version first ("flash"), and the saved counter briefly shows 0.

---

## Important Files

| File | Why it matters | Safe to edit? |
| --- | --- | --- |
| `src/routes/*.tsx` | All pages (the UI you value) | Yes, carefully |
| `src/components/*.tsx` | Custom UI building blocks | Yes, carefully |
| `src/contexts/AppContext.tsx` | Global state: language, theme, saved | Will change when auth/backend arrives |
| `src/data/*.ts` | All content + the **data types** the UI expects | Will be replaced by the backend; types are the contract to keep |
| `src/styles.css` | Design system (colours, shadows, dark mode) | Keep unchanged |
| `src/routes/__root.tsx` | HTML shell, fonts, providers, 404, error page | Rarely |
| `src/router.tsx` | Router + React Query client | Rarely |
| `src/server.ts`, `src/start.ts` | SSR entry, error handling, CSRF | Rarely |
| `src/routeTree.gen.ts` | **Auto-generated** route list | Never by hand |
| `src/components/ui/*` | shadcn/ui library | Leave as is |
| `vite.config.ts` | Lovable build config (warns not to add plugins manually) | Only with care |
| `package.json`, `bun.lock`, `bunfig.toml` | Dependencies & package manager | Via Bun only |
| `AGENTS.md` | Lovable rule: **never rewrite pushed git history** | Keep |
| `README.md` | Currently the original Lovable prompt, not real docs | Should be rewritten later |
| `roadmap.md` | Lovable's completed task list | Informational |

---

## Existing Features

**Fully working (with mock data):**
- ✅ Bilingual interface (English/Arabic) with correct right-to-left layout, persisted choice
- ✅ Light/dark theme, persisted choice
- ✅ Responsive layout (desktop, tablet, mobile drawer), collapsible sidebar
- ✅ Home page with multiple editorial sections
- ✅ Article detail page with AI-summary-style sections and related stories
- ✅ 404 for unknown articles; custom error pages
- ✅ Save / unsave articles (browser-only) with live counter in Navbar and Sidebar
- ✅ Saved Articles page with tabs, remove, share, and empty state
- ✅ Share = copy link to clipboard with toast
- ✅ Search modal with ⌘K shortcut (articles only)
- ✅ Course category filter; opportunity category filter
- ✅ External links to course platforms and article sources (open in new tab)
- ✅ Per-page SEO/Open Graph metadata; `robots.txt` allows indexing

**Visual only — look real but do nothing:**
- ❌ Notification bell (Navbar)
- ❌ Settings button (Sidebar)
- ❌ "Get the briefing" newsletter button
- ❌ "For You" topic chips on Home
- ❌ "View Opportunity" button (no link in the data)
- ❌ Opportunity "Save" (not persisted, not shown on Saved page)
- ❌ Sidebar links *Latest*, *Research*, *AI Models* (all go to Home); *Learning Paths* → Courses; *Scholarships / Internships / Competitions / Research* → Opportunities **without** applying the filter
- ❌ Home headline stats (24 / 7 / 3) and the date "Monday, September 21" are hard-coded
- ❌ "Updated 28 min ago", views, comments — static text
- ❌ "AI-generated summary" label — the text is hand-written mock content
- ❌ Comment counts (no comment system exists)

---

## Missing Features

Compared to the platform you described:

| Your intended feature | Current state |
| --- | --- |
| AI news | Mock only (7 articles), no live source |
| AI news summaries | Mock only; no AI pipeline |
| **Scientific research** | ❌ No dedicated page or research-paper data model — only an "AI Research" article category |
| AI courses | Mock only (6), links go to platform home pages |
| Scholarships | Mock only, inside Opportunities |
| Internships | Mock only, inside Opportunities |
| **Jobs** | ❌ **Completely missing** — no page, no category, no data |
| Other opportunities | Mock only (fellowships, hackathons, bootcamps, competitions) |

Missing platform capabilities:
- Backend, database, and content-management/admin panel
- Automatic news collection (RSS/API feeds, arXiv, etc.) and AI summarisation/translation
- User accounts, profiles, cross-device saved items, preferences / personalised feed
- Category/topic pages for news; pagination / "load more"
- Search across all content types; "no results" state
- Newsletter sign-up and email delivery; notifications
- Opportunity detail pages, deadlines as real dates, "closing soon" computed automatically
- Settings page
- Sitemap, structured data (JSON-LD), per-article Open Graph images
- Analytics, error monitoring in production, automated tests

---

## Technical Problems

1. **Code formatting / readability.** Almost all hand-written pages and components are compressed onto one very long line each (e.g. `src/routes/index.tsx` is effectively 4 lines). Prettier is configured but was not applied. This makes future changes and code review harder and riskier.
2. **Data tightly coupled to UI.** Pages import mock arrays directly; there is no data-access layer, no loading/error states, no pagination.
3. **Data shapes not backend-friendly.** Dates, "time ago", read time, views, and comments are pre-formatted strings, and every field is duplicated per language in the same object.
4. **Hydration flash.** Theme, language, and saved items load from `localStorage` after first paint → brief wrong theme/language, and `<html lang="en">` is always sent from the server.
5. **`AppShell` inside every page** instead of a layout route → shell state (sidebar collapse, search) resets on navigation.
6. **Duplicated "save" logic.** Articles use global persisted state; opportunities use separate throwaway local state.
7. **Dead code / unused template weight.** 3 unused custom components, ~44 unused shadcn components, ~15 unused npm packages, unused data exports.
8. **Hard-coded content in components** (dates, stats, topic list, tab definitions, category lists) rather than data.
9. **Fragile category matching** (Saved tabs use `includes("Research")` on English labels; filters compare English label strings instead of IDs).
10. **Hard-coded English strings** in shared components (`EmptyState`, `SaveButton`/`ShareButton` labels and aria-labels, 404/error pages, "FREE" badge) — not translated.
11. **Bleeding-edge toolchain:** Vite 8, Nitro 3 **beta**, rolldown override. Works inside Lovable, but upgrades could break unexpectedly.
12. **Package-manager mismatch:** Bun lockfile vs. README's npm instructions.
13. **No tests** of any kind; no CI workflow in the repository.
14. **README is the original AI prompt**, including instructions that now conflict with your goals ("No backend, database, authentication…").
15. Minor: missing `alt` text on all images (accessibility); reused images; `example.com` placeholder links; notification/setting buttons with no function may confuse users.

---

## Security Concerns

Current risk is **low** because there's no backend, no user data, and no secrets. The concerns below are mainly about what to do correctly *as the backend is added*:

1. **Secrets in the browser.** Any env var prefixed `VITE_` is embedded into public JavaScript. API keys for AI models, news APIs, email, or database admin access must **only** live on the server.
2. **Database access rules.** If using Supabase/Lovable Cloud, every table needs Row-Level Security policies; otherwise anyone can read/modify other users' data.
3. **Authentication done by a trusted provider**, not custom password code.
4. **Admin/editor roles** needed before any content-management features — never trust the browser to decide who is an admin.
5. **Input validation** (e.g. with the already-installed `zod`) on all server functions; keep the existing CSRF middleware.
6. **Rendering external content safely.** Scraped/AI-generated article text must be treated as untrusted; avoid rendering raw HTML (`dangerouslySetInnerHTML`) without sanitisation.
7. **AI prompt-injection & hallucination.** Articles fed to an AI summariser may contain malicious instructions or produce false claims; summaries should be clearly labelled and linked to the source, and ideally reviewed.
8. **Copyright / terms of use** of aggregated news sources — store summaries + links, not full copied articles.
9. **Rate limiting & abuse protection** for newsletter sign-up, search, and any AI-powered endpoints (cost exposure).
10. **Security headers** (Content-Security-Policy, etc.) are not configured.
11. **Privacy:** once accounts/emails exist, you'll need a privacy policy, cookie/consent handling, and data deletion.
12. **Supply chain:** keep Bun's 24-hour release-age guard; avoid adding unvetted packages.

---

## Recommended Architecture

Goal: **keep the existing UI and framework**, and add a backend behind it.

```
                ┌──────────────────────── Frontend (unchanged look) ───────────────────────┐
                │  TanStack Start pages & components                                        │
                │        │ React Query hooks (useArticles, useCourses, …)                   │
                │        ▼                                                                   │
                │  Data layer: src/lib/api/*  (one place that talks to the backend)         │
                └────────┬──────────────────────────────────────────────────────────────────┘
                         │ server functions (TanStack Start) / Supabase client
                         ▼
┌──────────────────────── Backend: Supabase (a.k.a. Lovable Cloud) ────────────────────────┐
│  PostgreSQL database  │  Auth (email, Google)  │  Storage (images)  │  Edge Functions/cron │
│  Row-Level Security   │  Roles: user / editor / admin                                     │
└──────────────┬────────────────────────────────────────────────────────────────────────────┘
               │ scheduled jobs (e.g. every 30–60 min)
               ▼
┌──────────────────────── Content pipeline ────────────────────────────────────────────────┐
│  Fetch: RSS feeds, arXiv API, company blogs, job/opportunity sources                     │
│  → de-duplicate → AI summarise (TL;DR, takeaways, why it matters) → AI translate to AR   │
│  → save as "draft" or "published" → editors can review in an admin area                  │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

**Why Supabase / Lovable Cloud:** it is the backend Lovable integrates with natively, gives a real PostgreSQL database, authentication, file storage, and scheduled functions in one place, and is manageable for a beginner through a web dashboard. TanStack Start server functions can hold any logic that needs secret keys.

**Suggested core tables** (names indicative):

| Table | Purpose |
| --- | --- |
| `sources` | News/research sources (name, URL, feed type, trust level) |
| `categories` | Stable IDs + EN/AR labels (AI Research, Robotics, …) |
| `articles` | News items: slug, category, source, author, `published_at` (real timestamp), image, original URL, status, importance, trending score |
| `article_content` | Per-language text: title, summary, TL;DR, takeaways, why-it-matters, what-happened, quote |
| `article_metrics`, `article_timeline` | Structured "By the numbers" and timeline entries |
| `research_papers` | Papers (arXiv ID, authors, abstract, AI summary) — for the missing Research section |
| `courses`, `learning_paths` | Courses with provider, level, duration, language, real URL |
| `opportunities` | One table with a `type` column: scholarship, internship, **job**, fellowship, competition, hackathon, bootcamp, research — plus `deadline` (real date), location, remote flag, eligibility, apply URL |
| `profiles` | User profile, language, theme, interests |
| `saved_items` | `user_id` + `item_type` + `item_id` (articles, opportunities, courses, papers) |
| `newsletter_subscribers` | Email, language, confirmed flag |

**Frontend principle:** the existing TypeScript types (`NewsItem`, `Course`, `Opportunity`) become the "contract". The backend returns data in (nearly) that shape, so components need little or no change. Pre-formatted strings ("Updated 28 min ago", "12.8K") should be computed in the UI from real values using the already-installed `date-fns`.

---

## Migration Strategy

A step-by-step path where **the site keeps working after every step** (important because commits sync to Lovable).

**Phase 0 — Safety net (no visible change)**
- Agree on a working branch strategy (develop on a branch, merge to `main` only when verified).
- Install dependencies with Bun, confirm `build` and `lint` pass; add a simple CI check.
- Optionally auto-format the compressed files with the existing Prettier config (pure formatting, zero behaviour change) to make later work safer.

**Phase 1 — Data layer (no visible change)**
- Create `src/lib/api/` functions (`getArticles`, `getArticle`, `getCourses`, `getOpportunities`, …) that *still return the mock data*.
- Switch pages to call these via React Query / route loaders. Add loading (`SkeletonLoader`) and empty (`EmptyState`) states.
- Result: identical UI, but a single place to swap in the real backend.

**Phase 2 — Database**
- Set up Supabase (Lovable Cloud), create tables and security policies, and **seed them with the current mock content** so the site looks the same.
- Point the data layer at the database.

**Phase 3 — Accounts**
- Add sign-up/login (email + Google), a profile/settings page, and move "saved" to the database (merge any existing browser-saved items on first login). Unify saving for articles, opportunities, and courses.

**Phase 4 — Missing sections**
- Add **Jobs** (as an opportunity type with its own page/filter) and a **Research** section (papers).
- Make sidebar links go to real filtered views; add opportunity detail pages and real "Apply" links.

**Phase 5 — Content pipeline**
- Scheduled ingestion from selected sources → AI summaries and Arabic translation on the server → admin/editor review screen → publish.

**Phase 6 — Engagement**
- Real search across all content (PostgreSQL full-text search), newsletter sign-up + email sending, notifications, personalised "For You".

**Phase 7 — Production hardening**
- Security headers, rate limiting, error monitoring, analytics, sitemap and structured data, accessibility pass (alt text), performance review, privacy policy.

---

## Risks

| Risk | Why it matters | Mitigation |
| --- | --- | --- |
| **Breaking the Lovable sync** | Force-pushes or history rewrites destroy Lovable project history; broken commits on `main` break the Lovable editor | Never rewrite pushed history; work on branches; merge only working code |
| **Accidental UI changes** | The UI is the most valuable asset | Keep `styles.css` and components untouched; change data sources, not markup; compare screenshots before/after |
| **Lovable and hand-edits conflicting** | Lovable's AI may overwrite hand-written backend code | Decide where future edits happen; keep backend code in clearly separate files |
| **Bleeding-edge dependencies** | Nitro beta / Vite 8 upgrades may break builds | Pin versions; upgrade deliberately |
| **AI summary accuracy** | Wrong facts damage credibility | Label as AI-generated, always link sources, editor review for featured stories |
| **Copyright / source terms** | Republishing full articles can be illegal | Store short summaries + links only; respect robots/terms |
| **Running costs** | AI calls, database, email, hosting scale with traffic | Cache summaries, batch processing, usage limits and budget alerts |
| **Arabic quality** | Machine translation may read poorly | Human review for key content; glossary of AI terms |
| **Security mistakes** | Leaked keys or missing database rules expose data | Server-only secrets, Row-Level Security, security review before launch |
| **Scope creep** | Many features at once for a beginner | Follow phases; ship one working step at a time |

---

## Recommended Next Steps

1. **Review this document** and confirm priorities (e.g. is *Jobs* or *Research* more urgent than accounts?).
2. **Decide the backend provider** — recommendation: **Supabase via Lovable Cloud**.
3. **Confirm the working model with Lovable** — will you keep prompting Lovable, or do changes here and let them sync? (Affects how we avoid conflicts.)
4. **Phase 0:** install dependencies with Bun, verify build/lint, optionally apply formatting-only cleanup.
5. **Phase 1:** introduce the data layer while still using mock data — zero visual change, and the biggest enabler for everything after.
6. Then proceed phase by phase, verifying the live preview after each step.

### Parts that should remain unchanged
- The visual design: `src/styles.css`, colours, typography, spacing, dark mode
- All page layouts and component markup in `src/routes/` and `src/components/`
- Bilingual/RTL behaviour and the `{ en, ar }` text approach
- The shadcn/ui library in `src/components/ui/`
- The framework (TanStack Start/React), error handling (`server.ts`, `start.ts`, `lib/error-*`), and Lovable config
- `routeTree.gen.ts` (auto-generated) and `AGENTS.md`

### Parts that need a real backend
- Articles/news, AI summaries, research, courses, learning paths, opportunities (incl. new Jobs)
- Search, saved items, user preferences, newsletter, notifications, home page stats and "trending"/"most discussed" rankings, views/comments

### Parts that are currently placeholders
- All content in `src/data/*`, the 4 reused images, `example.com` links
- Home stats and date, "Updated X ago", views, comments
- Notifications bell, Settings, newsletter button, For You chips, View Opportunity, sidebar sub-links
- `PageHeader`, `EmptyState`, `SkeletonLoader` (built but unused)
