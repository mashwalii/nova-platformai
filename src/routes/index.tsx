import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { Search, X } from "lucide-react";
import { toast } from "sonner";
import { Navbar } from "@/components/Navbar";
import { Sidebar } from "@/components/Sidebar";
import { PageHeader } from "@/components/PageHeader";
import { FeaturedNewsCard } from "@/components/FeaturedNewsCard";
import { NewsCard } from "@/components/NewsCard";
import { SectionHeader } from "@/components/SectionHeader";
import { EmptyState } from "@/components/EmptyState";
import { Button } from "@/components/ui/button";
import { allNews, briefs, featuredStory, spotlight } from "@/data/mockNews";

export const Route = createFileRoute("/")({
  head: () => ({ meta: [
    { title: "NOVA AI — AI News & Intelligence" },
    { name: "description", content: "Essential reporting and analysis on artificial intelligence, research, models, companies and policy." },
    { property: "og:title", content: "NOVA AI — AI News & Intelligence" },
    { property: "og:description", content: "Signal over noise: essential AI reporting and analysis." },
    { property: "og:type", content: "website" },
    { name: "twitter:card", content: "summary_large_image" },
  ]}),
  component: Index,
});

function Index() {
  const [dark, setDark] = useState(false);
  const [activeCategory, setActiveCategory] = useState("All News");
  const [saved, setSaved] = useState<Set<string>>(new Set(["open-weights"]));
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState("");

  useEffect(() => { document.documentElement.classList.toggle("dark", dark); }, [dark]);
  useEffect(() => {
    const keydown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") { event.preventDefault(); setSearchOpen(true); }
      if (event.key === "Escape") setSearchOpen(false);
    };
    window.addEventListener("keydown", keydown);
    return () => window.removeEventListener("keydown", keydown);
  }, []);

  const toggleSaved = (id: string) => setSaved((current) => { const next = new Set(current); next.has(id) ? next.delete(id) : next.add(id); return next; });
  const filtered = useMemo(() => allNews.filter((item) => `${item.title} ${item.summary} ${item.category}`.toLowerCase().includes(query.toLowerCase())), [query]);
  const categoryItems = activeCategory === "All News" ? null : allNews.filter((item) => item.category === activeCategory);

  return <div className="min-h-screen bg-background text-foreground">
    <Navbar dark={dark} onTheme={() => setDark((value) => !value)} onSearch={() => setSearchOpen(true)} onMenu={() => setMobileOpen(true)} />
    <div className="flex h-[calc(100vh-4rem)]">
      <Sidebar active={activeCategory} onSelect={setActiveCategory} savedCount={saved.size} collapsed={collapsed} onCollapse={() => setCollapsed((value) => !value)} mobileOpen={mobileOpen} onMobileClose={() => setMobileOpen(false)} />
      <main className="min-w-0 flex-1 overflow-y-auto"><div className="mx-auto max-w-[1480px] px-4 py-7 sm:px-6 lg:px-8 lg:py-9">
        <PageHeader category={activeCategory} />
        {categoryItems ? (categoryItems.length ? <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">{categoryItems.map((item) => <NewsCard key={item.id} item={item} saved={saved.has(item.id)} onSave={() => toggleSaved(item.id)} />)}</div> : <EmptyState />) : <>
          <section className="grid gap-5 xl:grid-cols-[minmax(0,1.7fr)_minmax(300px,0.8fr)]">
            <FeaturedNewsCard item={featuredStory} saved={saved.has(featuredStory.id)} onSave={() => toggleSaved(featuredStory.id)} onShare={() => toast.success("Share link copied")} />
            <div className="flex flex-col rounded-lg border border-border bg-card p-5 shadow-card"><SectionHeader title="Intelligence Briefs" eyebrow="Live desk" /><div className="divide-y divide-border">{briefs.map((item, index) => <article key={item.id} className="py-5 first:pt-1"><div className="grid grid-cols-[auto_minmax(0,1fr)] gap-3"><span className="text-xs font-bold text-primary">0{index + 1}</span><div className="min-w-0"><p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">{item.category} · {item.time}</p><h3 className="mt-1.5 text-base font-bold leading-snug text-foreground">{item.title}</h3><p className="mt-2 text-xs leading-5 text-muted-foreground">{item.summary}</p></div></div></article>)}</div><Button variant="outline" className="mt-auto w-full" onClick={() => setActiveCategory("Breaking News")}>Open live briefing</Button></div>
          </section>
          <section className="mt-10"><SectionHeader title="The Spotlight" eyebrow="Deeper intelligence" onViewAll={() => setActiveCategory("AI Research")} /><div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">{spotlight.map((item) => <NewsCard key={item.id} item={item} saved={saved.has(item.id)} onSave={() => toggleSaved(item.id)} />)}</div></section>
        </>}
      </div></main>
    </div>
    {searchOpen && <div className="fixed inset-0 z-[60] bg-overlay/70 px-4 pt-[12vh] backdrop-blur-sm" onMouseDown={() => setSearchOpen(false)}><div className="mx-auto max-w-2xl overflow-hidden rounded-lg border border-border bg-popover shadow-modal" onMouseDown={(event) => event.stopPropagation()}><div className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 border-b border-border px-4"><Search className="h-5 w-5 text-muted-foreground" /><input autoFocus value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search models, companies, research…" className="h-14 min-w-0 bg-transparent text-sm text-foreground outline-none placeholder:text-muted-foreground" /><Button size="icon" variant="ghost" onClick={() => setSearchOpen(false)} aria-label="Close search"><X /></Button></div><div className="max-h-[52vh] overflow-y-auto p-2">{filtered.length ? filtered.map((item) => <button key={item.id} className="block w-full rounded-md px-3 py-3 text-left hover:bg-accent" onClick={() => { setActiveCategory(item.category); setSearchOpen(false); setQuery(""); }}><span className="text-[10px] font-bold uppercase tracking-wider text-primary">{item.category}</span><p className="mt-1 text-sm font-semibold text-foreground">{item.title}</p></button>) : <EmptyState />}</div></div></div>}
  </div>;
}
