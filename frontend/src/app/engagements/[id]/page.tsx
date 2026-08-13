"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Checklist } from "@/components/Checklist";
import { ItemDetail } from "@/components/ItemDetail";
import type { ChecklistItem, Engagement } from "@/lib/types";

export default function EngagementPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [engagement, setEngagement] = useState<Engagement | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .getEngagement(id)
      .then((eng) => {
        setEngagement(eng);
        setSelectedId(eng.checklist_items[0]?.id ?? null);
      })
      .catch(() => setError("Engagement not found."));
  }, [id]);

  function updateItem(updated: ChecklistItem) {
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
  }

  if (error) {
    return (
      <div className="p-8">
        <p className="text-sm text-red-600">{error}</p>
        <Link href="/" className="text-sm text-blue-600 hover:underline">
          ← Back
        </Link>
      </div>
    );
  }

  if (!engagement) {
    return <div className="p-8 text-sm text-neutral-500">Loading…</div>;
  }

  const sev = engagement.checklist_items
    .flatMap((i) => i.findings)
    .reduce<Record<string, number>>((acc, f) => {
      acc[f.severity] = (acc[f.severity] ?? 0) + 1;
      return acc;
    }, {});
  const done = engagement.checklist_items.filter((i) =>
    ["done", "skipped"].includes(i.status)
  ).length;
  const selected = engagement.checklist_items.find((i) => i.id === selectedId) ?? null;

  return (
    <div className="flex flex-1 flex-col">
      <header className="flex items-center justify-between border-b border-neutral-200 px-6 py-3 dark:border-neutral-800">
        <div>
          <Link href="/" className="text-xs text-neutral-500 hover:underline">
            ← All engagements
          </Link>
          <h1 className="text-lg font-semibold">{engagement.name}</h1>
          <p className="text-xs text-neutral-500">
            {engagement.target} · {done}/{engagement.checklist_items.length} items ·{" "}
            {engagement.checklist_items.flatMap((i) => i.findings).length} findings
            {sev.critical ? ` · ${sev.critical} critical` : ""}
            {sev.high ? ` · ${sev.high} high` : ""}
          </p>
        </div>
        <div className="flex gap-2">
          <a
            href={api.reportUrl(engagement.id, "md")}
            className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-900"
          >
            Markdown report
          </a>
          <a
            href={api.reportUrl(engagement.id, "docx")}
            className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-900"
          >
            Word report
          </a>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <aside className="w-72 shrink-0 overflow-y-auto border-r border-neutral-200 px-3 py-4 dark:border-neutral-800">
          <Checklist
            items={engagement.checklist_items}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        </aside>

        {selected ? (
          <ItemDetail
            engagementId={engagement.id}
            target={engagement.target}
            item={selected}
            onChange={updateItem}
          />
        ) : (
          <div className="flex-1 p-6 text-sm text-neutral-500">
            Select a checklist item.
          </div>
        )}
      </div>
    </div>
  );
}
