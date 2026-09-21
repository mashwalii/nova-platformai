import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";

export function SectionHeader({ title, eyebrow, onViewAll }: { title: string; eyebrow?: string; onViewAll?: () => void }) {
  return <div className="mb-4 grid grid-cols-[minmax(0,1fr)_auto] items-end gap-4"><div className="min-w-0">{eyebrow && <p className="mb-1 text-[10px] font-bold uppercase tracking-widest text-primary">{eyebrow}</p>}<h2 className="truncate text-xl font-bold text-foreground sm:text-2xl">{title}</h2></div>{onViewAll && <Button variant="ghost" size="sm" onClick={onViewAll} className="shrink-0 text-muted-foreground">View all <ArrowRight /></Button>}</div>;
}