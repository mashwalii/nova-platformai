export function CategoryBadge({ children }: { children: React.ReactNode }) {
  return <span className="inline-flex items-center rounded-full bg-primary-soft px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-primary">{children}</span>;
}