"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/Badge";
import { FindingsPanel } from "@/components/FindingsPanel";
import { RunToolDialog } from "@/components/RunToolDialog";
import type { ChecklistItem, ToolInfo } from "@/lib/types";

export function ItemDetail({
  engagementId,
  target,
  item,
  onChange,
}: {
  engagementId: string;
  target: string;
  item: ChecklistItem;
  onChange: (item: ChecklistItem) => void;
}) {
  const [tools, setTools] = useState<ToolInfo[]>([]);
  const [showRun, setShowRun] = useState(false);
  const [notes, setNotes] = useState(item.notes);
  const [savingNotes, setSavingNotes] = useState(false);
  const [activeOutput, setActiveOutput] = useState<string | null>(null);

  useEffect(() => {
    api.listTools().then(setTools);
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reset local edit state when the selected item changes
    setNotes(item.notes);
    setActiveOutput(Object.keys(item.tool_outputs)[0] ?? null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [item.id]);

  async function saveNotes() {
    setSavingNotes(true);
    const updated = await api.updateNotes(engagementId, item.id, notes);
    onChange(updated);
    setSavingNotes(false);
  }

  async function act(action: "markDone" | "skip" | "reset") {
    const updated = await api[action](engagementId, item.id);
    onChange(updated);
  }

  const hasRunnableTools = item.tools.length > 0;

  return (
    <div className="flex-1 overflow-y-auto px-6 py-5">
      <div className="mb-1 flex items-center gap-2">
        <h2 className="text-lg font-semibold">
          {item.id} — {item.name}
        </h2>
        <StatusBadge status={item.status} />
      </div>
      <p className="mb-4 text-sm text-neutral-500">{item.category}</p>

      <p className="mb-4 text-sm text-neutral-700 dark:text-neutral-300">
        {item.description}
      </p>

      {item.references.length > 0 && (
        <p className="mb-4 text-xs">
          <a
            href={item.references[0]}
            target="_blank"
            rel="noreferrer"
            className="text-blue-600 hover:underline dark:text-blue-400"
          >
            OWASP WSTG reference ↗
          </a>
        </p>
      )}

      <div className="mb-5 flex flex-wrap gap-2">
        {hasRunnableTools && (
          <button
            onClick={() => setShowRun(true)}
            className="rounded-md bg-foreground px-3 py-1.5 text-sm font-medium text-background hover:opacity-90"
          >
            Run tool
          </button>
        )}
        <button
          onClick={() => act("markDone")}
          className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-900"
        >
          Mark done
        </button>
        <button
          onClick={() => act("skip")}
          className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-900"
        >
          Skip
        </button>
        <button
          onClick={() => act("reset")}
          className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-900"
        >
          Reset
        </button>
      </div>

      {Object.keys(item.tool_outputs).length > 0 && (
        <div className="mb-5">
          <h3 className="mb-2 text-sm font-semibold">Tool output</h3>
          <div className="mb-2 flex gap-2">
            {Object.keys(item.tool_outputs).map((t) => (
              <button
                key={t}
                onClick={() => setActiveOutput(t)}
                className={`rounded px-2 py-1 text-xs ${
                  activeOutput === t
                    ? "bg-neutral-200 dark:bg-neutral-800"
                    : "text-neutral-500 hover:bg-neutral-100 dark:hover:bg-neutral-900"
                }`}
              >
                {t}
              </button>
            ))}
          </div>
          {activeOutput && (
            <pre className="max-h-72 overflow-auto rounded bg-black px-3 py-2 font-mono text-xs text-green-400">
              {item.tool_outputs[activeOutput]}
            </pre>
          )}
        </div>
      )}

      <div className="mb-5">
        <FindingsPanel engagementId={engagementId} item={item} onChange={onChange} />
      </div>

      <div className="mb-5">
        <h3 className="mb-1 text-sm font-semibold">Notes</h3>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          onBlur={saveNotes}
          rows={3}
          placeholder="Tester notes…"
          className="w-full rounded border border-neutral-300 bg-transparent px-2 py-1.5 text-sm dark:border-neutral-700"
        />
        {savingNotes && <p className="text-xs text-neutral-500">Saving…</p>}
      </div>

      {showRun && (
        <RunToolDialog
          engagementId={engagementId}
          target={target}
          item={item}
          allTools={tools}
          onClose={() => setShowRun(false)}
          onDone={(updated) => {
            onChange(updated);
            setActiveOutput(Object.keys(updated.tool_outputs).slice(-1)[0] ?? null);
          }}
        />
      )}
    </div>
  );
}
