"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/Badge";
import { FindingsPanel } from "@/components/FindingsPanel";
import { RunToolDialog } from "@/components/RunToolDialog";
import { ChecklistItemDialog } from "@/components/ChecklistItemDialog";
import { HighlightedOutput } from "@/components/HighlightedOutput";
import { useToast } from "@/lib/toast";
import type { ChecklistItem, ToolInfo } from "@/lib/types";

export function ItemDetail({
  engagementId,
  target,
  item,
  allTools,
  categories,
  onChange,
  onDelete,
}: {
  engagementId: string;
  target: string;
  item: ChecklistItem;
  allTools: ToolInfo[];
  categories: string[];
  onChange: (item: ChecklistItem) => void;
  onDelete: () => void;
}) {
  const toast = useToast();
  const [showRun, setShowRun] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [notes, setNotes] = useState(item.notes);
  const [savingNotes, setSavingNotes] = useState(false);
  const [activeOutput, setActiveOutput] = useState<string | null>(
    Object.keys(item.tool_outputs)[0] ?? null
  );
  const [busyAction, setBusyAction] = useState<"markDone" | "skip" | "reset" | null>(null);

  async function saveNotes() {
    if (notes === item.notes) return;
    setSavingNotes(true);
    try {
      const updated = await api.updateNotes(engagementId, item.id, notes);
      onChange(updated);
      toast.success("Notes saved");
    } catch {
      toast.error("Failed to save notes");
    } finally {
      setSavingNotes(false);
    }
  }

  async function act(action: "markDone" | "skip" | "reset") {
    setBusyAction(action);
    try {
      const updated = await api[action](engagementId, item.id);
      onChange(updated);
      const labels = { markDone: "Marked done", skip: "Skipped", reset: "Reset to pending" };
      toast.success(labels[action]);
    } catch {
      toast.error("Action failed");
    } finally {
      setBusyAction(null);
    }
  }

  async function handleDelete() {
    if (!confirm(`Delete checklist item "${item.id} — ${item.name}"? Its findings will be lost too.`))
      return;
    try {
      await api.deleteItem(engagementId, item.id);
      onDelete();
    } catch {
      toast.error("Failed to delete checklist item");
    }
  }

  const hasRunnableTools = item.tools.length > 0;

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="flex items-start justify-between gap-3 border-b border-neutral-200 px-6 py-4 dark:border-neutral-800">
        <div>
          <div className="mb-1 flex items-center gap-2">
            <h2 className="text-lg font-semibold">
              {item.id} — {item.name}
            </h2>
            <StatusBadge status={item.status} />
          </div>
          <p className="text-sm text-neutral-500">{item.category}</p>
        </div>
        <div className="flex shrink-0 gap-2">
          <button
            onClick={() => setShowEdit(true)}
            className="rounded-md border border-neutral-300 px-2.5 py-1 text-xs transition hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-900"
          >
            Edit
          </button>
          <button
            onClick={handleDelete}
            className="rounded-md border border-red-300 px-2.5 py-1 text-xs text-red-600 transition hover:bg-red-50 dark:border-red-900 dark:text-red-400 dark:hover:bg-red-900/20"
          >
            Delete
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-5">
        <p className="mb-4 text-sm leading-relaxed text-neutral-700 dark:text-neutral-300">
          {item.description}
        </p>

        {item.references.length > 0 && (
          <p className="mb-5 text-xs">
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
              className="rounded-md bg-foreground px-3 py-1.5 text-sm font-medium text-background transition hover:opacity-90"
            >
              Run tool
            </button>
          )}
          <button
            onClick={() => act("markDone")}
            disabled={busyAction !== null}
            className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm transition hover:bg-neutral-100 disabled:opacity-50 dark:border-neutral-700 dark:hover:bg-neutral-900"
          >
            {busyAction === "markDone" ? "Marking…" : "Mark done"}
          </button>
          <button
            onClick={() => act("skip")}
            disabled={busyAction !== null}
            className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm transition hover:bg-neutral-100 disabled:opacity-50 dark:border-neutral-700 dark:hover:bg-neutral-900"
          >
            {busyAction === "skip" ? "Skipping…" : "Skip"}
          </button>
          <button
            onClick={() => act("reset")}
            disabled={busyAction !== null}
            className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm transition hover:bg-neutral-100 disabled:opacity-50 dark:border-neutral-700 dark:hover:bg-neutral-900"
          >
            {busyAction === "reset" ? "Resetting…" : "Reset"}
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
                  className={`rounded px-2 py-1 text-xs transition-colors ${
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
              <pre className="max-h-72 overflow-auto rounded bg-black px-3 py-2 font-mono text-xs leading-relaxed text-neutral-300">
                <HighlightedOutput text={item.tool_outputs[activeOutput]} />
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
            className="w-full rounded border border-neutral-300 bg-transparent px-2 py-1.5 text-sm outline-none focus:border-neutral-500 dark:border-neutral-700"
          />
          {savingNotes && <p className="text-xs text-neutral-500">Saving…</p>}
        </div>
      </div>

      {showRun && (
        <RunToolDialog
          engagementId={engagementId}
          target={target}
          item={item}
          allTools={allTools}
          onClose={() => setShowRun(false)}
          onDone={(updated) => {
            onChange(updated);
            setActiveOutput(Object.keys(updated.tool_outputs).slice(-1)[0] ?? null);
          }}
        />
      )}

      {showEdit && (
        <ChecklistItemDialog
          mode="edit"
          item={item}
          categories={categories}
          allTools={allTools}
          onClose={() => setShowEdit(false)}
          onSubmit={async (values) => {
            try {
              const updated = await api.updateItem(engagementId, item.id, values);
              onChange(updated);
              toast.success("Checklist item updated");
              setShowEdit(false);
            } catch {
              toast.error("Failed to update checklist item");
            }
          }}
        />
      )}
    </div>
  );
}
