export function SourceBadge({ source }: { source: string }) {
  return <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-foreground"><span className="h-1.5 w-1.5 rounded-full bg-signal" />{source}</span>;
}