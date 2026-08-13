"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { useToast } from "@/lib/toast";
import { ChecklistItemDialog } from "@/components/ChecklistItemDialog";
import type { ChecklistItem, ToolInfo } from "@/lib/types";

const STATUS_COLOR: Record<string, string> = {
  pending: "text-neutral-400",
  running: "text-amber-500",
  done: "text-emerald-500",
  skipped: "text-neutral-400",
  failed: "text-red-500",
};

const STATUS_ICON: Record<string, string> = {
  pending: "○",
  running: "◎",
  done: "✓",
  skipped: "—",
  failed: "✗",
};

export function Checklist({
  engagementId,
  items,
  selectedId,
  onSelect,
  categories,
  allTools,
  onCreate,
}: {
  engagementId: string;
  items: ChecklistItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  categories: string[];
  allTools: ToolInfo[];
  onCreate: (item: ChecklistItem) => void;
}) {
  const toast = useToast();
  const [query, setQuery] = useState("");
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [showAdd, setShowAdd] = useState(false);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter(
      (i) =>
        i.name.toLowerCase().includes(q) ||
        i.id.toLowerCase().includes(q) ||
        i.category.toLowerCase().includes(q)
    );
  }, [items, query]);

  const byCategory = useMemo(() => {
    const map = new Map<string, ChecklistItem[]>();
    for (const item of filtered) {
      const list = map.get(item.category) ?? [];
      list.push(item);
      map.set(item.category, list);
    }
    return map;
  }, [filtered]);

  // Keyboard nav: up/down moves selection among currently visible items.
  useEffect(() => {
    function handler(e: KeyboardEvent) {
      if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
      const target = e.target as HTMLElement;
      if (["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)) return;
      e.preventDefault();
      const flat = [...byCategory.values()].flat();
      const idx = flat.findIndex((i) => i.id === selectedId);
      const next =
        e.key === "ArrowDown"
          ? flat[Math.min(idx + 1, flat.length - 1)]
          : flat[Math.max(idx - 1, 0)];
      if (next) onSelect(next.id);
    }
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [byCategory, selectedId, onSelect]);

  function toggleCategory(cat: string) {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });
  }

  return (
    <div className="flex h-full flex-col">
      <div className="sticky top-0 z-10 bg-background pb-2">
        <div className="mb-2 flex gap-2">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filter checklist… (↑↓ to navigate)"
            className="w-full rounded border border-neutral-300 bg-transparent px-2 py-1.5 text-sm outline-none focus:border-neutral-500 dark:border-neutral-700"
          />
          <button
            onClick={() => setShowAdd(true)}
            title="Add checklist item"
            className="shrink-0 rounded border border-neutral-300 px-2 py-1.5 text-sm transition hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-900"
          >
            +
          </button>
        </div>
      </div>
      <div className="flex-1 space-y-3 overflow-y-auto">
        {[...byCategory.entries()].map(([category, catItems]) => {
          const isCollapsed = collapsed.has(category);
          const doneCount = catItems.filter((i) => ["done", "skipped"].includes(i.status)).length;
          return (
            <div key={category}>
              <button
                onClick={() => toggleCategory(category)}
                className="mb-1 flex w-full items-center justify-between px-1 text-xs font-semibold uppercase tracking-wide text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300"
              >
                <span className="flex items-center gap-1">
                  <span className={`inline-block transition-transform ${isCollapsed ? "-rotate-90" : ""}`}>
                    ▾
                  </span>
                  {category}
                </span>
                <span className="font-normal normal-case text-neutral-400">
                  {doneCount}/{catItems.length}
                </span>
              </button>
              {!isCollapsed && (
                <ul className="space-y-0.5">
                  {catItems.map((item) => (
                    <li key={item.id}>
                      <button
                        onClick={() => onSelect(item.id)}
                        className={`flex w-full items-center justify-between gap-2 rounded px-2 py-1.5 text-left text-sm transition-colors ${
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
                          <span className={STATUS_COLOR[item.status]}>{STATUS_ICON[item.status]}</span>
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          );
        })}
        {filtered.length === 0 && (
          <p className="px-1 text-sm text-neutral-500">No items match &ldquo;{query}&rdquo;.</p>
        )}
      </div>

      {showAdd && (
        <ChecklistItemDialog
          mode="create"
          categories={categories}
          allTools={allTools}
          onClose={() => setShowAdd(false)}
          onSubmit={async (values) => {
            try {
              const created = await api.createItem(engagementId, values);
              onCreate(created);
              toast.success(`Added ${created.id}`);
              setShowAdd(false);
            } catch {
              toast.error("Failed to add checklist item");
            }
          }}
        />
      )}
    </div>
  );
}
