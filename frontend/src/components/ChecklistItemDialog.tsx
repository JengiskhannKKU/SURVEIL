"use client";

import { useState } from "react";
import type { ChecklistItem, ToolInfo } from "@/lib/types";

export interface ChecklistItemFormValues {
  name: string;
  description: string;
  category: string;
  category_code: string;
  tools: string[];
  references: string[];
}

function toFormValues(item?: ChecklistItem): ChecklistItemFormValues {
  return {
    name: item?.name ?? "",
    description: item?.description ?? "",
    category: item?.category ?? "",
    category_code: item?.category_code ?? "",
    tools: item?.tools ?? [],
    references: item?.references ?? [],
  };
}

export function ChecklistItemDialog({
  mode,
  item,
  categories,
  allTools,
  onClose,
  onSubmit,
}: {
  mode: "create" | "edit";
  item?: ChecklistItem;
  categories: string[];
  allTools: ToolInfo[];
  onClose: () => void;
  onSubmit: (values: ChecklistItemFormValues) => Promise<void>;
}) {
  const [values, setValues] = useState<ChecklistItemFormValues>(toFormValues(item));
  const [referencesText, setReferencesText] = useState((item?.references ?? []).join("\n"));
  const [saving, setSaving] = useState(false);

  function toggleTool(name: string) {
    setValues((prev) => ({
      ...prev,
      tools: prev.tools.includes(name)
        ? prev.tools.filter((t) => t !== name)
        : [...prev.tools, name],
    }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!values.name.trim() || !values.category.trim()) return;
    setSaving(true);
    try {
      await onSubmit({
        ...values,
        name: values.name.trim(),
        category: values.category.trim(),
        references: referencesText
          .split("\n")
          .map((r) => r.trim())
          .filter(Boolean),
      });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <form
        onSubmit={handleSubmit}
        className="flex max-h-[90vh] w-full max-w-lg flex-col overflow-hidden rounded-lg border border-neutral-200 bg-background shadow-xl dark:border-neutral-800"
      >
        <div className="flex items-center justify-between border-b border-neutral-200 px-5 py-3 dark:border-neutral-800">
          <h2 className="font-semibold">
            {mode === "create" ? "Add checklist item" : `Edit ${item?.id}`}
          </h2>
          <button type="button" onClick={onClose} className="text-neutral-500 hover:text-foreground">
            ✕
          </button>
        </div>

        <div className="flex-1 space-y-3 overflow-y-auto px-5 py-4">
          <label className="flex flex-col gap-1 text-sm">
            Name *
            <input
              required
              autoFocus
              value={values.name}
              onChange={(e) => setValues((v) => ({ ...v, name: e.target.value }))}
              className="rounded border border-neutral-300 bg-transparent px-2 py-1.5 outline-none focus:border-neutral-500 dark:border-neutral-700"
            />
          </label>

          <label className="flex flex-col gap-1 text-sm">
            Description
            <textarea
              value={values.description}
              onChange={(e) => setValues((v) => ({ ...v, description: e.target.value }))}
              rows={3}
              className="rounded border border-neutral-300 bg-transparent px-2 py-1.5 outline-none focus:border-neutral-500 dark:border-neutral-700"
            />
          </label>

          <div className="grid gap-3 sm:grid-cols-2">
            <label className="flex flex-col gap-1 text-sm">
              Category *
              <input
                required
                list="checklist-categories"
                value={values.category}
                onChange={(e) => setValues((v) => ({ ...v, category: e.target.value }))}
                className="rounded border border-neutral-300 bg-transparent px-2 py-1.5 outline-none focus:border-neutral-500 dark:border-neutral-700"
              />
              <datalist id="checklist-categories">
                {categories.map((c) => (
                  <option key={c} value={c} />
                ))}
              </datalist>
            </label>

            <label className="flex flex-col gap-1 text-sm">
              Category code
              <input
                value={values.category_code}
                placeholder="auto"
                onChange={(e) => setValues((v) => ({ ...v, category_code: e.target.value }))}
                className="rounded border border-neutral-300 bg-transparent px-2 py-1.5 outline-none focus:border-neutral-500 dark:border-neutral-700"
              />
            </label>
          </div>

          <div className="text-sm">
            <span className="mb-1 block">Tools</span>
            <div className="flex flex-wrap gap-2">
              {allTools.map((t) => (
                <label
                  key={t.name}
                  className={`cursor-pointer rounded-full border px-2.5 py-1 text-xs transition-colors ${
                    values.tools.includes(t.name)
                      ? "border-neutral-800 bg-neutral-800 text-white dark:border-neutral-200 dark:bg-neutral-200 dark:text-neutral-900"
                      : "border-neutral-300 hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-900"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={values.tools.includes(t.name)}
                    onChange={() => toggleTool(t.name)}
                    className="hidden"
                  />
                  {t.name}
                </label>
              ))}
            </div>
          </div>

          <label className="flex flex-col gap-1 text-sm">
            References (one URL per line)
            <textarea
              value={referencesText}
              onChange={(e) => setReferencesText(e.target.value)}
              rows={2}
              className="rounded border border-neutral-300 bg-transparent px-2 py-1.5 font-mono text-xs outline-none focus:border-neutral-500 dark:border-neutral-700"
            />
          </label>
        </div>

        <div className="flex justify-end gap-2 border-t border-neutral-200 px-5 py-3 dark:border-neutral-800">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-neutral-300 px-4 py-1.5 text-sm transition hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-900"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={saving}
            className="rounded-md bg-foreground px-4 py-1.5 text-sm font-medium text-background transition hover:opacity-90 disabled:opacity-50"
          >
            {saving ? "Saving…" : mode === "create" ? "Add item" : "Save changes"}
          </button>
        </div>
      </form>
    </div>
  );
}
