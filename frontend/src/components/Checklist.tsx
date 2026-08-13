"use client";

import type { ChecklistItem } from "@/lib/types";

export function Checklist({
  items,
  selectedId,
  onSelect,
}: {
  items: ChecklistItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const byCategory = new Map<string, ChecklistItem[]>();
  for (const item of items) {
    const list = byCategory.get(item.category) ?? [];
    list.push(item);
    byCategory.set(item.category, list);
  }

  return (
    <div className="space-y-4">
      {[...byCategory.entries()].map(([category, catItems]) => (
        <div key={category}>
          <h3 className="mb-1 px-1 text-xs font-semibold uppercase tracking-wide text-neutral-500">
            {category}
          </h3>
          <ul className="space-y-0.5">
            {catItems.map((item) => (
              <li key={item.id}>
                <button
                  onClick={() => onSelect(item.id)}
                  className={`flex w-full items-center justify-between gap-2 rounded px-2 py-1.5 text-left text-sm ${
                    selectedId === item.id
                      ? "bg-neutral-200 dark:bg-neutral-800"
                      : "hover:bg-neutral-100 dark:hover:bg-neutral-900"
                  }`}
                >
                  <span className="truncate">
                    <span className="mr-1 text-xs text-neutral-500">{item.id}</span>
                    {item.name}
                  </span>
                  <span className="flex shrink-0 items-center gap-1">
                    {item.findings.length > 0 && (
                      <span className="rounded-full bg-neutral-300 px-1.5 text-[10px] dark:bg-neutral-700">
                        {item.findings.length}
                      </span>
                    )}
                    <StatusIcon status={item.status} />
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

function StatusIcon({ status }: { status: ChecklistItem["status"] }) {
  const colors: Record<string, string> = {
    pending: "text-neutral-400",
    running: "text-amber-500",
    done: "text-emerald-500",
    skipped: "text-neutral-400",
    failed: "text-red-500",
  };
  const icons: Record<string, string> = {
    pending: "○",
    running: "◎",
    done: "✓",
    skipped: "—",
    failed: "✗",
  };
  return <span className={colors[status]}>{icons[status]}</span>;
}
