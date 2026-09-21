import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";

export function ThemeToggle({ dark, onToggle }: { dark: boolean; onToggle: () => void }) {
  return <Button type="button" variant="ghost" size="icon" onClick={onToggle} aria-label={dark ? "Use light theme" : "Use dark theme"} title={dark ? "Light mode" : "Dark mode"}>{dark ? <Sun /> : <Moon />}</Button>;
}