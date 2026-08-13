"use client";

import { use, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Checklist } from "@/components/Checklist";
import { ItemDetail } from "@/components/ItemDetail";
import { ProgressBar, SeverityBar } from "@/components/SeverityBar";
import { useToast } from "@/lib/toast";
import { severityCounts } from "@/lib/severity";
import type { ChecklistItem, Engagement, ToolInfo } from "@/lib/types";

function HeaderSkeleton() {
  return (
    <header className="border-b border-neutral-200 px-6 py-3 dark:border-neutral-800">
      <div className="skeleton mb-2 h-3 w-24 rounded bg-neutral-200 dark:bg-neutral-800" />
      <div className="skeleton mb-2 h-5 w-56 rounded bg-neutral-200 dark:bg-neutral-800" />
      <div className="skeleton h-3 w-72 rounded bg-neutral-200 dark:bg-neutral-800" />
    </header>
  );
}

export default function EngagementPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const toast = useToast();
  const [engagement, setEngagement] = useState<Engagement | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [tools, setTools] = useState<ToolInfo[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .getEngagement(id)
      .then((eng) => {
        setEngagement(eng);
        setSelectedId(eng.checklist_items[0]?.id ?? null);
      })
      .catch(() => setError("Engagement not found."));
    api.listTools().then(setTools);
  }, [id]);

  const updateItem = useCallback((updated: ChecklistItem) => {
    setEngagement((prev) =>
      prev
        ? {
            ...prev,
            checklist_items: prev.checklist_items.map((it) =>
              it.id === updated.id ? updated : it
            ),
          }
        : prev
    );
  }, []);

  const addItem = useCallback((created: ChecklistItem) => {
    setEngagement((prev) =>
      prev ? { ...prev, checklist_items: [...prev.checklist_items, created] } : prev
    );
    setSelectedId(created.id);
  }, []);

  const removeItem = useCallback(
    (itemId: string) => {
      setEngagement((prev) => {
        if (!prev) return prev;
        const remaining = prev.checklist_items.filter((i) => i.id !== itemId);
        setSelectedId((current) =>
          current === itemId ? (remaining[0]?.id ?? null) : current
        );
        return { ...prev, checklist_items: remaining };
      });
    },
    []
  );

  const jumpToNextPending = useCallback(() => {
    setEngagement((prev) => {
      if (!prev) return prev;
      const next = prev.checklist_items.find((i) => i.status === "pending");
      if (next) setSelectedId(next.id);
      return prev;
    });
  }, []);

  useEffect(() => {
    function handler(e: KeyboardEvent) {
      const target = e.target as HTMLElement;
      if (["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)) return;
      if (e.key === "n" || e.key === "N") jumpToNextPending();
    }
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [jumpToNextPending]);

  const sev = useMemo(
    () => severityCounts(engagement?.checklist_items.flatMap((i) => i.findings) ?? []),
    [engagement]
  );
  const done = useMemo(
    () =>
      engagement?.checklist_items.filter((i) => ["done", "skipped"].includes(i.status)).length ?? 0,
    [engagement]
  );
  const categories = useMemo(
    () => [...new Set(engagement?.checklist_items.map((i) => i.category) ?? [])],
    [engagement]
  );
  const selected = engagement?.checklist_items.find((i) => i.id === selectedId) ?? null;

  if (error) {
    return (
      <div className="p-8">
        <p className="mb-2 text-sm text-red-600">{error}</p>
        <Link href="/" className="text-sm text-blue-600 hover:underline dark:text-blue-400">
          ← Back to engagements
        </Link>
      </div>
    );
  }

  if (!engagement) {
    return (
      <div className="flex flex-1 flex-col">
        <HeaderSkeleton />
        <div className="flex flex-1 items-center justify-center text-sm text-neutral-500">
          Loading engagement…
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col">
      <header className="flex flex-wrap items-start justify-between gap-3 border-b border-neutral-200 px-6 py-3 dark:border-neutral-800">
        <div>
          <Link href="/" className="text-xs text-neutral-500 hover:underline">
            ← All engagements
          </Link>
          <h1 className="text-lg font-semibold">{engagement.name}</h1>
          <p className="mb-2 text-xs text-neutral-500">{engagement.target}</p>
          <div className="flex flex-wrap items-center gap-4">
            <ProgressBar done={done} total={engagement.checklist_items.length} />
            <SeverityBar counts={sev} />
          </div>
        </div>
        <div className="flex gap-2">
          <a
            href={api.reportUrl(engagement.id, "md")}
            className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm transition hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-900"
          >
            Markdown report
          </a>
          <a
            href={api.reportUrl(engagement.id, "docx")}
            className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm transition hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-900"
          >
            Word report
          </a>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <aside className="flex w-72 shrink-0 flex-col border-r border-neutral-200 px-3 py-4 dark:border-neutral-800">
          <Checklist
            engagementId={engagement.id}
            items={engagement.checklist_items}
            selectedId={selectedId}
            onSelect={setSelectedId}
            categories={categories}
            allTools={tools}
            onCreate={addItem}
          />
        </aside>

        {selected ? (
          <ItemDetail
            key={selected.id}
            engagementId={engagement.id}
            target={engagement.target}
            item={selected}
            allTools={tools}
            categories={categories}
            onChange={updateItem}
            onDelete={() => {
              removeItem(selected.id);
              toast.success(`Deleted ${selected.id}`);
            }}
          />
        ) : (
          <div className="flex-1 p-6 text-sm text-neutral-500">
            {engagement.checklist_items.length === 0
              ? "No checklist items yet — add one from the sidebar."
              : "Select a checklist item."}
          </div>
        )}
      </div>
    </div>
  );
}
