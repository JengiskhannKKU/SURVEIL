import { SEVERITY_COLOR, SEVERITY_ORDER } from "@/lib/severity";
import type { Severity } from "@/lib/types";

export function SeverityBar({ counts }: { counts: Record<Severity, number> }) {
  const total = SEVERITY_ORDER.reduce((sum, s) => sum + counts[s], 0);

  if (total === 0) {
    return (
      <div className="flex items-center gap-2 text-xs text-neutral-500">
        <div className="h-2 w-40 rounded-full bg-neutral-200 dark:bg-neutral-800" />
        No findings yet
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3">
      <div className="flex h-2 w-40 overflow-hidden rounded-full bg-neutral-200 dark:bg-neutral-800">
        {SEVERITY_ORDER.filter((s) => counts[s] > 0).map((s) => (
          <div
            key={s}
            style={{ width: `${(counts[s] / total) * 100}%`, backgroundColor: SEVERITY_COLOR[s] }}
            title={`${s}: ${counts[s]}`}
          />
        ))}
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs">
        {SEVERITY_ORDER.filter((s) => counts[s] > 0).map((s) => (
          <span key={s} className="flex items-center gap-1 text-neutral-600 dark:text-neutral-400">
            <span
              className="inline-block h-2 w-2 rounded-full"
              style={{ backgroundColor: SEVERITY_COLOR[s] }}
            />
            {counts[s]} {s}
          </span>
        ))}
      </div>
    </div>
  );
}

export function ProgressBar({ done, total }: { done: number; total: number }) {
  const pct = total === 0 ? 0 : Math.round((done / total) * 100);
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 w-40 overflow-hidden rounded-full bg-neutral-200 dark:bg-neutral-800">
        <div
          className="h-full rounded-full bg-emerald-500 transition-[width] duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-neutral-500">
        {done}/{total} ({pct}%)
      </span>
    </div>
  );
}
