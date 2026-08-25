// Parses discovered directory/file paths out of ffuf/gobuster/katana output
// (both the real tools' formats and this project's own mock_output()
// formats — see surveil/tools/ffuf_tool.py, gobuster_tool.py, katana_tool.py)
// and builds them into a tree for the "Tree view" toggle in ItemDetail.

export interface TreeNode {
  name: string;
  path: string; // full path from root, e.g. "/admin/login"
  children: TreeNode[];
  observed: boolean; // this exact path was an actual result, not just an inferred parent segment
}

// ffuf's mock_output() prints "| URL | https://target/admin" per result
// (its own -v-style verbose format), sometimes with " -> https://.../admin/"
// appended for a redirect.
const FFUF_MOCK_URL_RE = /^\|\s*URL\s*\|\s*(\S+)/;
// gobuster: "/admin                (Status: 301) [Size: 178] [--> .../admin/]"
const GOBUSTER_RE = /^(\/\S*)\s+\(Status:/;
// katana / ffuf verbose: a bare absolute URL alone on its own line.
const BARE_URL_RE = /^(https?:\/\/\S+)$/;
// Real ffuf with -s (silent) prints just the matched value, bare, one per
// line ("admin", "api", "login") — no scheme/host/status decoration at all.
const BARE_PATH_RE = /^[\w.\-/]+$/;

const IGNORE_LINE_RE = /^(::|_{3,}|v\d|\[SIMULATED|Duration:|Progress:)/;

function stripUrlToPath(url: string): string {
  try {
    const u = new URL(url);
    return u.pathname || "/";
  } catch {
    return url.startsWith("/") ? url : `/${url}`;
  }
}

export function parseDiscoveredPaths(output: string, toolName: string): string[] {
  const paths = new Set<string>();

  for (const raw of output.split("\n")) {
    const line = raw.trim();
    if (!line || IGNORE_LINE_RE.test(line)) continue;

    let m = line.match(FFUF_MOCK_URL_RE);
    if (m) {
      const url = m[1].split("->")[0].trim();
      paths.add(stripUrlToPath(url));
      continue;
    }

    m = line.match(GOBUSTER_RE);
    if (m) {
      paths.add(m[1]);
      continue;
    }

    m = line.match(BARE_URL_RE);
    if (m) {
      paths.add(stripUrlToPath(m[1]));
      continue;
    }

    // Real ffuf's -s output is deliberately bare (no distinguishing prefix),
    // so this fallback only applies when we already know the active tool is
    // ffuf — otherwise a stray line of plain text from any other tool's
    // output would get misread as a discovered path.
    if (toolName === "ffuf" && BARE_PATH_RE.test(line)) {
      paths.add(line.startsWith("/") ? line : `/${line}`);
    }
  }

  return Array.from(paths).filter((p) => p.length > 1);
}

export function buildPathTree(paths: string[]): TreeNode {
  const root: TreeNode = { name: "/", path: "", children: [], observed: false };
  const index = new Map<string, TreeNode>([["", root]]);

  for (const path of paths) {
    const segments = path.split("/").filter(Boolean);
    let current = root;
    let currentPath = "";
    segments.forEach((seg, i) => {
      currentPath += `/${seg}`;
      let node = index.get(currentPath);
      if (!node) {
        node = { name: seg, path: currentPath, children: [], observed: false };
        index.set(currentPath, node);
        current.children.push(node);
      }
      if (i === segments.length - 1) node.observed = true;
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
