# Original Lovable Design Brief (historical)

> This is the original prompt/brief that was used to generate the NOVA AI frontend in Lovable.
> It was moved here unchanged from `README.md` so the README can hold real setup instructions.
> It is kept for reference: the design-system and layout notes still describe the current UI.
> The "FRONTEND UI/UX ONLY" constraint below applied to the prototype stage and is superseded by `ARCHITECTURE.md`.

---

# Nova AI Insights

Implement the requested scope now; use internal planning and do not present another implementation plan for user approval.

# Project: NOVA AI — Premium AI News & Intelligence Platform

## Core Constraint
- FRONTEND UI/UX ONLY.
- No backend, database, authentication, or live APIs.
- Built strictly with realistic, structured mock data in a modular centralized file (`src/data/mockNews.ts`) designed for seamless drop-in API replacement later.

## Reference Attachment
- Attached image `uploads/3aae379f-d80b-4bdf-b068-0c5bd0e82376` provides layout inspiration: structured left navigation sidebar, clear top header, editorial card composition with a dominant headline story, secondary side-by-side feeds, metadata chips, and disciplined whitespace. Do not clone it verbatim; interpret it as an ultra-refined, modern AI intelligence platform.

## Design System & Theme
- Visual feel: Editorial tech magazine meets high-end SaaS dashboard (Linear / Monocle / Stripe / NYT tech caliber). Clean, sophisticated, restrained.
- Light Mode:
  - Canvas background: Warm off-white / neutral stone-50 (`#FBFBFB` or `#F7F7F8`)
  - Cards: Crisp pure white (`#FFFFFF`) with ultra-fine borders (`border-stone-200/70` or `border-neutral-200/60`) and soft, subtle ambient elevation
  - Text: Primary deep charcoal (`#121316`), Secondary muted stone/gray (`#64676D`)
  - Accent: Sophisticated electric/deep blue (`#185EE0` / `#2563EB`) used sparingly on active states, key tags, and subtle focus cues
- Dark Mode:
  - Deep rich near-black canvas (`#0A0B0D`)
  - Surface cards (`#121318` or `#16171D`) with subtle borders (`border-neutral-800`)
  - Crisp white primary typography, muted slate/zinc secondary text
  - Deep subtle blue accent glow
- Typography: Inter or Geist, strict scale with bold confident headlines, restrained section titles, and legible metadata.

## Application Shell Architecture
1. **Top Navigation Bar:**
   - Left: Minimalist, sophisticated "NOVA AI" brand mark and wordmark
   - Center Navigation: Home (active), Latest, Research, Models, Companies, Tools
   - Right Side: Search trigger (quick search shortcut `⌘K`), theme toggle (Light / Dark), notification icon with subtle unread badge, and user profile avatar
2. **Left Sidebar:**
   - Section `EXPLORE` with minimal icons:
     - All News (active by default), Breaking News, AI Research, Generative AI, AI Models, AI Agents, Robotics, Computer Vision, Open Source, AI Companies, AI Startups, AI Tools, AI Safety, AI Policy, AI Funding
   - Section `YOUR LIBRARY`:
     - Saved Articles (with interactive saved count badge), My Feed
   - Bottom area:
     - Settings, theme toggle, and collapsible toggle
   - Responsive behavior:
     - Desktop: Full sidebar
     - Tablet: Compact icon-only or collapsible sidebar
     - Mobile: Drawer / slide-out hamburger navigation with simplified top bar
3. **Main Content Area (Home Page):**
   - **Hero / Lead Headline Card:** Full editorial featured story (e.g. multimodal reasoning milestone, foundation model release), category badge, source badge, reading time, interactive Save & Share buttons, and engagement stats.
   - **Top Story Grid / Sidebar Feed:** Secondary intelligence briefs (Funding rounds, breakthrough benchmark papers, safety policy updates) arranged with balanced visual hierarchy.
   - **Spotlight Grid:** AI Research deep-dives, new open-source models, and agentic workflows with clean thumbnail cards and metadata.
   - Interactive features: Search modal / bar filter, active category switching, working bookmark/save state toggle, and share toast notification.

## Reusable Components Directory
Organize clear, reusable components in `src/components/`:
- `Navbar.tsx`
- `Sidebar.tsx`
- `PageHeader.tsx`
- `SectionHeader.tsx`
- `NewsCard.tsx`
- `FeaturedNewsCard.tsx`
- `CategoryBadge.tsx`
- `SourceBadge.tsx`
- `SaveButton.tsx`
- `ShareButton.tsx`
- `EmptyState.tsx`
- `SkeletonLoader.tsx`
- `ThemeToggle.tsx`

Ensure exceptional polish, crisp spacing, and high-density editorial aesthetics across mobile, tablet, and desktop viewports.
