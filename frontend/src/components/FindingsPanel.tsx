"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { SeverityBadge } from "@/components/Badge";
import type { ChecklistItem, Finding, Severity } from "@/lib/types";

const SEVERITIES: Severity[] = ["critical", "high", "medium", "low", "info"];

export function FindingsPanel({
  engagementId,
  item,
  onChange,
}: {
  engagementId: string;
  item: ChecklistItem;
  onChange: (item: ChecklistItem) => void;
}) {
  const [showForm, setShowForm] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [severity, setSeverity] = useState<Severity>("medium");
  const [description, setDescription] = useState("");
  const [remediation, setRemediation] = useState("");
  const [cvssVector, setCvssVector] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setSaving(true);
    const finding = await api.addFinding(engagementId, item.id, {
      title: title.trim(),
      severity,
      description: description.trim(),
      remediation: remediation.trim(),
      cvss_vector: cvssVector.trim(),
    });
    onChange({ ...item, findings: [...item.findings, finding] });
    setTitle("");
    setDescription("");
    setRemediation("");
    setCvssVector("");
    setSeverity("medium");
    setShowForm(false);
    setSaving(false);
  }

  async function toggleVerified(f: Finding) {
    const updated = await api.updateFinding(engagementId, item.id, f.id, {
      verified: !f.verified,
    });
    onChange({
      ...item,
      findings: item.findings.map((x) => (x.id === f.id ? updated : x)),
    });
  }

  async function handleDelete(f: Finding) {
    if (!confirm(`Delete finding "${f.title}"?`)) return;
    await api.deleteFinding(engagementId, item.id, f.id);
    onChange({ ...item, findings: item.findings.filter((x) => x.id !== f.id) });
  }

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-semibold">Findings ({item.findings.length})</h3>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="text-xs text-blue-600 hover:underline dark:text-blue-400"
        >
          {showForm ? "Cancel" : "+ Add finding"}
        </button>
      </div>

      {showForm && (
        <form
          onSubmit={handleAdd}
          className="mb-3 rounded border border-neutral-200 p-3 dark:border-neutral-800"
        >
          <div className="mb-2 grid gap-2 sm:grid-cols-2">
            <input
              required
              placeholder="Title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="rounded border border-neutral-300 bg-transparent px-2 py-1 text-sm dark:border-neutral-700"
            />
            <select
              value={severity}
              onChange={(e) => setSeverity(e.target.value as Severity)}
              className="rounded border border-neutral-300 bg-transparent px-2 py-1 text-sm dark:border-neutral-700"
            >
              {SEVERITIES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <textarea
            placeholder="Description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            className="mb-2 w-full rounded border border-neutral-300 bg-transparent px-2 py-1 text-sm dark:border-neutral-700"
          />
          <div className="mb-2 grid gap-2 sm:grid-cols-2">
            <input
              placeholder="CVSS vector (optional)"
              value={cvssVector}
              onChange={(e) => setCvssVector(e.target.value)}
              className="rounded border border-neutral-300 bg-transparent px-2 py-1 text-sm font-mono dark:border-neutral-700"
            />
            <input
              placeholder="Remediation"
              value={remediation}
              onChange={(e) => setRemediation(e.target.value)}
              className="rounded border border-neutral-300 bg-transparent px-2 py-1 text-sm dark:border-neutral-700"
            />
          </div>
          <button
            type="submit"
            disabled={saving}
            className="rounded-md bg-foreground px-3 py-1 text-xs font-medium text-background hover:opacity-90 disabled:opacity-50"
          >
            Save finding
          </button>
        </form>
      )}

      {item.findings.length === 0 ? (
        <p className="text-xs text-neutral-500">No findings on this item yet.</p>
      ) : (
        <ul className="space-y-2">
          {item.findings.map((f) => (
            <li
              key={f.id}
              className="rounded border border-neutral-200 p-2 text-sm dark:border-neutral-800"
            >
              <div
                className="flex cursor-pointer items-center justify-between gap-2"
                onClick={() => setExpanded(expanded === f.id ? null : f.id)}
              >
                <div className="flex items-center gap-2">
                  <SeverityBadge severity={f.severity} />
                  <span className="font-medium">{f.title}</span>
                  {f.verified && (
                    <span className="text-xs text-emerald-600 dark:text-emerald-400">
                      verified
                    </span>
                  )}
                  <span className="text-xs text-neutral-500">({f.tool})</span>
                </div>
              </div>
              {expanded === f.id && (
                <div className="mt-2 space-y-2 text-xs text-neutral-600 dark:text-neutral-400">
                  {f.description && <p>{f.description}</p>}
                  {f.evidence && (
                    <pre className="overflow-x-auto rounded bg-neutral-100 p-2 dark:bg-neutral-900">
                      {f.evidence}
                    </pre>
                  )}
                  {f.remediation && (
                    <p>
                      <span className="font-medium">Remediation: </span>
                      {f.remediation}
                    </p>
                  )}
                  {f.cvss_vector && (
                    <p className="font-mono">
                      {f.cvss_vector} ({f.cvss_score})
                    </p>
                  )}
                  <div className="flex gap-3">
                    <button
                      onClick={() => toggleVerified(f)}
                      className="text-blue-600 hover:underline dark:text-blue-400"
                    >
                      {f.verified ? "Unverify" : "Verify"}
                    </button>
                    <button
                      onClick={() => handleDelete(f)}
                      className="text-red-600 hover:underline dark:text-red-400"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
