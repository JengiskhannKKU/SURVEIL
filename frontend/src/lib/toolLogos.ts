// Small colored "logo" badges for each tool wrapper, keyed by tool name
// (see surveil/tools/__init__.py's TOOL_REGISTRY). Deliberately not real
// project logos/wordmarks — pulling in 18 external brand assets (network
// fetches, licensing/trademark questions, inconsistent art styles) isn't
// worth it for a local single-user tool. Instead: a 2-3 letter monogram
// in a fixed, distinct color per tool, styled like the rest of the app's
// terminal/hacker-console theme — gives each tool a consistent, instantly
// recognizable visual identity in the Tool dropdown and the Tools catalog
// without depending on anything outside this repo.
export interface ToolLogoMeta {
  label: string;
  color: string;
}

export const TOOL_LOGOS: Record<string, ToolLogoMeta> = {
  amass:     { label: "AM", color: "#f97316" },
  arjun:     { label: "AJ", color: "#a855f7" },
  dnsx:      { label: "DX", color: "#06b6d4" },
  ffuf:      { label: "FF", color: "#f59e0b" },
  gobuster:  { label: "GB", color: "#eab308" },
  gowitness: { label: "GW", color: "#8b5cf6" },
  httpx:     { label: "HX", color: "#22c55e" },
  hydra:     { label: "HY", color: "#dc2626" },
  katana:    { label: "KT", color: "#ec4899" },
  nikto:     { label: "NK", color: "#14b8a6" },
  nmap:      { label: "NM", color: "#3b82f6" },
  nuclei:    { label: "NU", color: "#ef4444" },
  sqlmap:    { label: "SQ", color: "#f43f5e" },
  subfinder: { label: "SF", color: "#0ea5e9" },
  testssl:   { label: "TS", color: "#10b981" },
  wafw00f:   { label: "WF", color: "#6366f1" },
  whatweb:   { label: "WW", color: "#84cc16" },
  wpscan:    { label: "WP", color: "#2563eb" },
  naabu:     { label: "NB", color: "#0891b2" },
  dalfox:    { label: "DF", color: "#db2777" },
  commix:    { label: "CX", color: "#65a30d" },
};

export function toolLogo(name: string): ToolLogoMeta {
  return TOOL_LOGOS[name] ?? { label: name.slice(0, 2).toUpperCase(), color: "#6b7280" };
}
