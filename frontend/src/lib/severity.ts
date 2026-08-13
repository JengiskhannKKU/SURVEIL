import type { Severity, Status } from "./types";

export const SEVERITY_ORDER: Severity[] = ["critical", "high", "medium", "low", "info"];
export const STATUS_ORDER: Status[] = ["running", "failed", "pending", "done", "skipped"];

export const SEVERITY_COLOR: Record<Severity, string> = {
  critical: "#dc2626",
  high: "#f97316",
  medium: "#eab308",
  low: "#0ea5e9",
  info: "#a3a3a3",
};

export const SEVERITY_TEXT_CLASS: Record<Severity, string> = {
  critical: "text-red-600 dark:text-red-400",
  high: "text-orange-500 dark:text-orange-400",
  medium: "text-yellow-600 dark:text-yellow-400",
  low: "text-sky-600 dark:text-sky-400",
  info: "text-neutral-500",
};

export function sortBySeverity<T extends { severity: Severity }>(items: T[]): T[] {
  return [...items].sort(
    (a, b) => SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity)
  );
}

export function severityCounts(items: { severity: Severity }[]): Record<Severity, number> {
  const counts = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
  for (const item of items) counts[item.severity]++;
  return counts;
}
