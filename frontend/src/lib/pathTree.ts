// Parses discovered directory/file paths out of ffuf/gobuster/katana output
// (both the real tools' formats and this project's own mock_output()
// formats — see oculus/tools/ffuf_tool.py, gobuster_tool.py, katana_tool.py)
// and builds them into a tree for the "Tree view" toggle in ItemDetail.
import { NOISE_LINE_RE } from "./logFilter";

export interface TreeNode {
  name: string;
  path: string; // full path from root, e.g. "/admin/login"
  children: TreeNode[];
  observed: boolean; // this exact path was an actual result, not just an inferred parent segment
  status: number | null; // HTTP status code for this exact path, if the tool's output carried one
  manual: boolean; // added by hand (see engagementPaths.ts) rather than parsed from a tool's output
}

// ffuf's own "-v" verbose format: a "[Status: 200, Size: ..., ...]" line
// immediately followed by "| URL | https://target/admin" (sometimes with
// " -> https://.../admin/" appended for a redirect). Real ffuf -mc/-v output
// matches this shape (see oculus/tools/ffuf_tool.py) — the status line is
// captured separately and paired with the URL line that follows it.
const FFUF_STATUS_RE = /^\[Status:\s*(\d+)/;
const FFUF_MOCK_URL_RE = /^\|\s*URL\s*\|\s*(\S+)/;
// gobuster: "/admin                (Status: 301) [Size: 178] [--> .../admin/]"
const GOBUSTER_RE = /^(\/\S*)\s+\(Status:\s*(\d+)/;
// nikto: "+ /path/: some finding description." or, when the finding has
// an OSVDB id, "+ OSVDB-3092: /path/: some finding description." — no
// status code in this output format at all, so these entries carry
// status: null. Gated to nikto specifically (like the ffuf bare-path
// fallback below) since "+ <word>:" alone is too generic a shape to
// safely assume means "path" for every tool's output.
const NIKTO_RE = /^\+\s*(?:OSVDB-\d+:\s*)?(\/[^\s:]+):/;
// katana / ffuf verbose: a bare absolute URL alone on its own line.
const BARE_URL_RE = /^(https?:\/\/\S+)$/;
// Real ffuf with -s (silent) prints just the matched value, bare, one per
// line ("admin", "api", "login") — no scheme/host/status decoration at all.
// Only still seen on runs saved before -v replaced -s; carries no status.
const BARE_PATH_RE = /^[\w.\-/]+$/;

const IGNORE_LINE_RE = NOISE_LINE_RE;

function stripUrlToPath(url: string): string {
  try {
    const u = new URL(url);
    return u.pathname || "/";
  } catch {
    return url.startsWith("/") ? url : `/${url}`;
  }
}

export function parseDiscoveredPaths(
  output: string,
  toolName: string
): { path: string; status: number | null }[] {
  const paths = new Map<string, number | null>();
  let pendingStatus: number | null = null;

  for (const raw of output.split("\n")) {
    const line = raw.trim();
    if (!line || IGNORE_LINE_RE.test(line)) continue;

    let m = line.match(FFUF_STATUS_RE);
    if (m) {
      pendingStatus = Number(m[1]);
      continue;
    }

    m = line.match(FFUF_MOCK_URL_RE);
    if (m) {
      const url = m[1].split("->")[0].trim();
      paths.set(stripUrlToPath(url), pendingStatus);
      pendingStatus = null;
      continue;
    }

    m = line.match(GOBUSTER_RE);
    if (m) {
      paths.set(m[1], Number(m[2]));
      continue;
    }

    if (toolName === "nikto") {
      m = line.match(NIKTO_RE);
      if (m) {
        paths.set(m[1], null);
        continue;
      }
    }

    m = line.match(BARE_URL_RE);
    if (m) {
      paths.set(stripUrlToPath(m[1]), null);
      continue;
    }

    // Real ffuf's -s output is deliberately bare (no distinguishing prefix,
    // no status — only still seen on runs saved before -v replaced -s), so
    // this fallback only applies when we already know the active tool is
    // ffuf — otherwise a stray line of plain text from any other tool's
    // output would get misread as a discovered path.
    if (toolName === "ffuf" && BARE_PATH_RE.test(line)) {
      paths.set(line.startsWith("/") ? line : `/${line}`, null);
    }
  }

  return Array.from(paths.entries())
    .filter(([p]) => p.length > 1)
    .map(([path, status]) => ({ path, status }));
}

export function buildPathTree(
  entries: { path: string; status: number | null; manual?: boolean }[]
): TreeNode {
  const root: TreeNode = {
    name: "/",
    path: "",
    children: [],
    observed: false,
    status: null,
    manual: false,
  };
  const index = new Map<string, TreeNode>([["", root]]);

  for (const { path, status, manual } of entries) {
    const segments = path.split("/").filter(Boolean);
    let current = root;
    let currentPath = "";
    segments.forEach((seg, i) => {
      currentPath += `/${seg}`;
      let node = index.get(currentPath);
      if (!node) {
        node = {
          name: seg,
          path: currentPath,
          children: [],
          observed: false,
          status: null,
          manual: false,
        };
        index.set(currentPath, node);
        current.children.push(node);
      }
      if (i === segments.length - 1) {
        node.observed = true;
        node.status = status;
        node.manual = manual ?? false;
      }
      current = node;
    });
  }

  function sortTree(node: TreeNode) {
    node.children.sort((a, b) => a.name.localeCompare(b.name));
    node.children.forEach(sortTree);
  }
  sortTree(root);

  return root;
}

// Distinct HTTP status codes actually present in a parsed result set, sorted
// ascending — drives which status filter chips ItemDetail shows (e.g. only
// "200 / 301 / 403" if that's genuinely what this run found, not every code
// ffuf could theoretically return).
export function collectStatuses(entries: { status: number | null }[]): number[] {
  const set = new Set<number>();
  for (const { status } of entries) {
    if (status !== null) set.add(status);
  }
  return Array.from(set).sort((a, b) => a - b);
}

// Filters ffuf's "-v" verbose raw output (a "[Status: N, ...]" line paired
// with the "| URL | ..." line right after it) or gobuster's inline
// "path (Status: N)" lines down to just the ones matching `status`, keeping
// any other line (banners/progress) verbatim so the surrounding context of
// a real run isn't stripped away. No-op passthrough for tool output shaped
// like anything else (nmap, nuclei, ...) — those never carry a status code
// in the first place.
export function filterRawByStatus(output: string, status: number): string {
  const lines = output.split("\n");
  const result: string[] = [];
  let pendingStatusLine: string | null = null;
  let pendingStatus: number | null = null;

  for (const raw of lines) {
    const trimmed = raw.trim();

    const statusMatch = trimmed.match(FFUF_STATUS_RE);
    if (statusMatch) {
      pendingStatusLine = raw;
      pendingStatus = Number(statusMatch[1]);
      continue;
    }

    if (pendingStatus !== null && FFUF_MOCK_URL_RE.test(trimmed)) {
      if (pendingStatus === status) result.push(pendingStatusLine as string, raw);
      pendingStatusLine = null;
      pendingStatus = null;
      continue;
    }

    const gobusterMatch = trimmed.match(GOBUSTER_RE);
    if (gobusterMatch) {
      if (Number(gobusterMatch[2]) === status) result.push(raw);
      continue;
    }

    result.push(raw);
  }

  return result.join("\n");
}
