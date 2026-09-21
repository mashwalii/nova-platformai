import { Share2 } from "lucide-react";
import { Button } from "@/components/ui/button";

export function ShareButton({ onShare, compact = false }: { onShare: () => void; compact?: boolean }) {
  return <Button type="button" variant="outline" size={compact ? "icon" : "sm"} onClick={onShare} aria-label="Share article" title="Share article" className="bg-card"><Share2 />{!compact && <span>Share</span>}</Button>;
}