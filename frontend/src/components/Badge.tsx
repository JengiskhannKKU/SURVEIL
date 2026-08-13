import type { Severity, Status } from "@/lib/types";

const STATUS_STYLES: Record<Status, string> = {
  pending: "bg-neutral-200 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400",
  running: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300",
  done: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300",
  skipped: "bg-neutral-200 text-neutral-500 dark:bg-neutral-800 dark:text-neutral-500",
  failed: "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300",
};

const STATUS_ICON: Record<Status, string> = {
  pending: "○",
  running: "◎",
  done: "✓",
  skipped: "—",
  failed: "✗",
};

export function StatusBadge({ status }: { status: Status }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[status]}`}
    >
      <span>{STATUS_ICON[status]}</span>
      {status}
    </span>
  );
}

const SEVERITY_STYLES: Record<Severity, string> = {
  critical: "bg-red-600 text-white",
  high: "bg-orange-500 text-white",
  medium: "bg-yellow-400 text-black",
  low: "bg-sky-500 text-white",
  info: "bg-neutral-400 text-black",
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span
      className={`inline-flex items-center rounded px-1.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${SEVERITY_STYLES[severity]}`}
    >
      {severity}
    </span>
  );
}
