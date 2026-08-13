"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { useToast } from "@/lib/toast";
import { ProgressBar } from "@/components/SeverityBar";
import type { EngagementSummary } from "@/lib/types";

function SkeletonRow() {
  return (
    <tr className="border-t border-neutral-200 dark:border-neutral-800">
      <td className="px-4 py-3">
        <div className="skeleton h-4 w-32 rounded bg-neutral-200 dark:bg-neutral-800" />
      </td>
      <td className="px-4 py-3">
        <div className="skeleton h-4 w-24 rounded bg-neutral-200 dark:bg-neutral-800" />
      </td>
      <td className="px-4 py-3">
        <div className="skeleton h-4 w-28 rounded bg-neutral-200 dark:bg-neutral-800" />
      </td>
      <td className="px-4 py-3">
        <div className="skeleton h-4 w-12 rounded bg-neutral-200 dark:bg-neutral-800" />
      </td>
      <td className="px-4 py-3">
        <div className="skeleton h-4 w-20 rounded bg-neutral-200 dark:bg-neutral-800" />
      </td>
      <td />
    </tr>
  );
}

function StatCard({ label, value, accent }: { label: string; value: string | number; accent?: string }) {
  return (
    <div className="rounded-lg border border-neutral-200 px-4 py-3 dark:border-neutral-800">
      <div className={`text-2xl font-semibold ${accent ?? ""}`}>{value}</div>
      <div className="text-xs text-neutral-500">{label}</div>
    </div>
  );
}

export default function Home() {
  const router = useRouter();
  const toast = useToast();
  const [engagements, setEngagements] = useState<EngagementSummary[] | null>(null);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [query, setQuery] = useState("");
  const [target, setTarget] = useState("");
  const [name, setName] = useState("");
  const [notes, setNotes] = useState("");
  const [creating, setCreating] = useState(false);

  async function refresh() {
    try {
      setEngagements(await api.listEngagements());
      setError("");
    } catch {
      setError("Could not reach the backend API. Is it running?");
      setEngagements([]);
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
      toast.success(`Engagement "${eng.name}" created`);
      router.push(`/engagements/${eng.id}`);
    } catch {
      toast.error("Failed to create engagement.");
      setCreating(false);
    }
  }

  async function handleDelete(id: string, name: string) {
    if (!confirm(`Delete engagement "${name}"? This cannot be undone.`)) return;
    try {
      await api.deleteEngagement(id);
      toast.success(`Deleted "${name}"`);
      refresh();
    } catch {
      toast.error("Failed to delete engagement.");
    }
  }

  const filtered = useMemo(() => {
    if (!engagements) return [];
    const q = query.trim().toLowerCase();
    if (!q) return engagements;
    return engagements.filter(
      (e) => e.name.toLowerCase().includes(q) || e.target.toLowerCase().includes(q)
    );
  }, [engagements, query]);

  const totals = useMemo(() => {
    if (!engagements) return { count: 0, findings: 0, critical: 0, high: 0 };
    return engagements.reduce(
      (acc, e) => ({
        count: acc.count + 1,
        findings: acc.findings + e.findings,
        critical: acc.critical + e.critical,
        high: acc.high + e.high,
      }),
      { count: 0, findings: 0, critical: 0, high: 0 }
    );
  }, [engagements]);

  const loading = engagements === null;

  return (
    <div className="mx-auto w-full max-w-4xl flex-1 px-6 py-10">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">surveil</h1>
          <p className="text-sm text-neutral-500">
            OWASP WSTG checklist-driven web application penetration testing
          </p>
        </div>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="rounded-md bg-foreground px-4 py-2 text-sm font-medium text-background transition hover:opacity-90"
        >
          {showForm ? "Cancel" : "+ New Engagement"}
        </button>
      </div>

      {!loading && engagements.length > 0 && (
        <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatCard label="Engagements" value={totals.count} />
          <StatCard label="Total findings" value={totals.findings} />
          <StatCard label="Critical" value={totals.critical} accent={totals.critical > 0 ? "text-red-600" : ""} />
          <StatCard label="High" value={totals.high} accent={totals.high > 0 ? "text-orange-500" : ""} />
        </div>
      )}

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
                autoFocus
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                placeholder="example.com"
                className="rounded border border-neutral-300 bg-transparent px-3 py-2 outline-none focus:border-neutral-500 dark:border-neutral-700"
              />
            </label>
            <label className="flex flex-col gap-1 text-sm">
              Name
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="defaults to target"
                className="rounded border border-neutral-300 bg-transparent px-3 py-2 outline-none focus:border-neutral-500 dark:border-neutral-700"
              />
            </label>
            <label className="col-span-full flex flex-col gap-1 text-sm">
              Scope notes
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={2}
                className="rounded border border-neutral-300 bg-transparent px-3 py-2 outline-none focus:border-neutral-500 dark:border-neutral-700"
              />
            </label>
          </div>
          <button
            type="submit"
            disabled={creating}
            className="mt-4 rounded-md bg-foreground px-4 py-2 text-sm font-medium text-background transition hover:opacity-90 disabled:opacity-50"
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

      {!loading && engagements.length > 0 && (
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by name or target…"
          className="mb-3 w-full max-w-xs rounded border border-neutral-300 bg-transparent px-3 py-1.5 text-sm outline-none focus:border-neutral-500 dark:border-neutral-700"
        />
      )}

      {!loading && engagements.length === 0 ? (
        <div className="rounded-lg border border-dashed border-neutral-300 px-6 py-12 text-center dark:border-neutral-700">
          <p className="mb-1 text-sm font-medium">No engagements yet</p>
          <p className="text-sm text-neutral-500">
            Create one to start working through the OWASP WSTG checklist.
          </p>
        </div>
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
              {loading ? (
                <>
                  <SkeletonRow />
                  <SkeletonRow />
                  <SkeletonRow />
                </>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-6 text-center text-sm text-neutral-500">
                    No engagements match &ldquo;{query}&rdquo;.
                  </td>
                </tr>
              ) : (
                filtered.map((e) => {
                  const [done, total] = e.progress.split("/").map(Number);
                  return (
                    <tr
                      key={e.id}
                      className="group border-t border-neutral-200 transition hover:bg-neutral-50 dark:border-neutral-800 dark:hover:bg-neutral-900"
                    >
                      <td className="px-4 py-2.5">
                        <Link
                          href={`/engagements/${e.id}`}
                          className="font-medium hover:underline"
                        >
                          {e.name}
                        </Link>
                        <div className="text-xs text-neutral-500">{e.id}</div>
                      </td>
                      <td className="px-4 py-2.5 text-neutral-600 dark:text-neutral-400">
                        {e.target}
                      </td>
                      <td className="px-4 py-2.5">
                        <ProgressBar done={done || 0} total={total || 0} />
                      </td>
                      <td className="px-4 py-2.5">
                        {e.findings}
                        {e.critical > 0 && (
                          <span className="ml-1.5 rounded bg-red-600 px-1.5 py-0.5 text-[10px] font-semibold text-white">
                            {e.critical} crit
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-2.5 text-neutral-500">{e.created_at}</td>
                      <td className="px-4 py-2.5 text-right opacity-0 transition-opacity group-hover:opacity-100">
                        <button
                          onClick={() => handleDelete(e.id, e.name)}
                          className="text-xs text-red-600 hover:underline"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
