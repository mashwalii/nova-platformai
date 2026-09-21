import { Bookmark } from "lucide-react";
import { Button } from "@/components/ui/button";

export function SaveButton({ saved, onToggle, compact = false }: { saved: boolean; onToggle: () => void; compact?: boolean }) {
  return <Button type="button" variant="outline" size={compact ? "icon" : "sm"} onClick={onToggle} aria-label={saved ? "Remove bookmark" : "Save article"} title={saved ? "Saved" : "Save article"} className={saved ? "border-primary bg-primary-soft text-primary hover:bg-primary-soft" : "bg-card"}><Bookmark className={saved ? "fill-current" : ""} />{!compact && <span>{saved ? "Saved" : "Save"}</span>}</Button>;
}