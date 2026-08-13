"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { EngagementSummary } from "@/lib/types";

export default function Home() {
  const router = useRouter();
  const [engagements, setEngagements] = useState<EngagementSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [target, setTarget] = useState("");
  const [name, setName] = useState("");
  const [notes, setNotes] = useState("");
  const [creating, setCreating] = useState(false);

  async function refresh() {
    setLoading(true);
    try {
      setEngagements(await api.listEngagements());
      setError("");
    } catch {
      setError("Could not reach the backend API. Is it running?");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- initial data fetch on mount
    refresh();
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!target.trim()) return;
    setCreating(true);
    try {
      const eng = await api.createEngagement(target.trim(), name.trim(), notes.trim());
      router.push(`/engagements/${eng.id}`);
    } catch {
      setError("Failed to create engagement.");
      setCreating(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm(`Delete engagement ${id}? This cannot be undone.`)) return;
    await api.deleteEngagement(id);
    refresh();
  }

  return (
    <div className="mx-auto w-full max-w-4xl flex-1 px-6 py-10">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">surveil</h1>
          <p className="text-sm text-neutral-500">
            OWASP WSTG checklist-driven web application penetration testing
          </p>
        </div>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="rounded-md bg-foreground px-4 py-2 text-sm font-medium text-background hover:opacity-90"
        >
          {showForm ? "Cancel" : "New Engagement"}
        </button>
      </div>

      {showForm && (
        <form
          onSubmit={handleCreate}
          className="mb-8 rounded-lg border border-neutral-200 p-5 dark:border-neutral-800"
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="flex flex-col gap-1 text-sm">
              Target *
              <input
                required
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                placeholder="example.com"
                className="rounded border border-neutral-300 bg-transparent px-3 py-2 dark:border-neutral-700"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              Name
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="defaults to target"
                className="rounded border border-neutral-300 bg-transparent px-3 py-2 dark:border-neutral-700"
              />
            </label>
            <label className="col-span-full flex flex-col gap-1 text-sm">
              Scope notes
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={2}
                className="rounded border border-neutral-300 bg-transparent px-3 py-2 dark:border-neutral-700"
              />
            </label>
          </div>
          <button
            type="submit"
            disabled={creating}
            className="mt-4 rounded-md bg-foreground px-4 py-2 text-sm font-medium text-background hover:opacity-90 disabled:opacity-50"
          >
            {creating ? "Creating..." : "Create engagement"}
          </button>
        </form>
      )}

      {error && (
        <p className="mb-4 rounded bg-red-100 px-3 py-2 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
          {error}
        </p>
      )}

      {loading ? (
        <p className="text-sm text-neutral-500">Loading…</p>
      ) : engagements.length === 0 ? (
        <p className="text-sm text-neutral-500">
          No engagements yet. Create one to get started.
        </p>
      ) : (
        <div className="overflow-hidden rounded-lg border border-neutral-200 dark:border-neutral-800">
          <table className="w-full text-sm">
            <thead className="bg-neutral-100 text-left dark:bg-neutral-900">
              <tr>
                <th className="px-4 py-2 font-medium">Name</th>
                <th className="px-4 py-2 font-medium">Target</th>
                <th className="px-4 py-2 font-medium">Progress</th>
                <th className="px-4 py-2 font-medium">Findings</th>
                <th className="px-4 py-2 font-medium">Created</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody>
              {engagements.map((e) => (
                <tr
                  key={e.id}
                  className="border-t border-neutral-200 hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-900"
                >
                  <td className="px-4 py-2">
                    <Link
                      href={`/engagements/${e.id}`}
                      className="font-medium hover:underline"
                    >
                      {e.name}
                    </Link>
                    <div className="text-xs text-neutral-500">{e.id}</div>
                  </td>
                  <td className="px-4 py-2">{e.target}</td>
                  <td className="px-4 py-2">{e.progress}</td>
                  <td className="px-4 py-2">
                    {e.findings}
                    {e.critical > 0 && (
                      <span className="ml-1 text-red-600">
                        ({e.critical} crit)
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-neutral-500">{e.created_at}</td>
                  <td className="px-4 py-2 text-right">
                    <button
                      onClick={() => handleDelete(e.id)}
                      className="text-xs text-red-600 hover:underline"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
