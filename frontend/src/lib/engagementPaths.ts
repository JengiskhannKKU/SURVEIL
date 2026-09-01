// Aggregates discovered directory/file paths across *every* checklist
// item's tool output for an engagement (ffuf/gobuster/katana, wherever
// parseDiscoveredPaths finds something) into one combined list — backs
// the engagement page's "Paths/Endpoints" summary button, which shows
// what's been found across the whole engagement, not just the one
// checklist item currently open in ItemDetail.
import { parseDiscoveredPaths } from "./pathTree";
import type { ChecklistItem, ManualPathEntry } from "./types";

export interface EngagementPathEntry {
  path: string;
  status: number | null;
  tool: string;
  itemId: string | null; // null for a manually-added entry — not tied to a checklist item's run
  manual: boolean;
  note?: string;
}

function normalizePath(path: string): string {
  path = path.trim();
  return path.startsWith("/") ? path : `/${path}`;
}

// Auto-discovered paths (parsed from every checklist item's tool output)
// merged with hand-added ones (`manual_paths`), minus anything a tester
// has hidden (`removed_paths`) — see backend/routers/paths.py. Manual
// entries always win a collision: a path someone deliberately annotated
// (status/note) shouldn't get silently overwritten by an auto-discovered
// duplicate with no annotation.
export function collectEngagementPaths(
  items: ChecklistItem[],
  manualPaths: ManualPathEntry[] = [],
  removedPaths: string[] = []
): EngagementPathEntry[] {
  const removed = new Set(removedPaths.map(normalizePath));
  const byPath = new Map<string, EngagementPathEntry>();

  for (const item of items) {
    for (const [tool, output] of Object.entries(item.tool_outputs)) {
      for (const { path, status } of parseDiscoveredPaths(output, tool)) {
        if (removed.has(path)) continue;
        const existing = byPath.get(path);
        if (!existing || (status !== null && existing.status === null)) {
          byPath.set(path, { path, status, tool, itemId: item.id, manual: false });
        }
      }
    }
  }

  for (const m of manualPaths) {
    const path = normalizePath(m.path);
    if (removed.has(path)) continue;
    byPath.set(path, {
      path,
      status: m.status,
      tool: "manual",
      itemId: null,
      manual: true,
      note: m.note,
    });
  }

  return Array.from(byPath.values());
}
