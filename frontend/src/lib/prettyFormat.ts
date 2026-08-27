// Detects JSON or HTML embedded in raw tool output and reformats it for
// readability — no external dependency, just enough of a formatter to turn
// a minified/single-line blob into something a human can scan. Common
// shape this has to handle: curl -i / wget -S output is an HTTP header
// block, a blank line, then the actual body — the body is what's worth
// pretty-printing, the headers are left exactly as the tool printed them.

export type PrettyKind = "json" | "html";

export interface PrettyResult {
  kind: PrettyKind;
  formatted: string;
}

const VOID_TAGS = new Set([
  "area", "base", "br", "col", "embed", "hr", "img",
  "input", "link", "meta", "param", "source", "track", "wbr",
]);

function splitHeadersAndBody(text: string): { headers: string; body: string } {
  const idx = text.search(/\r?\n\r?\n/);
  if (idx === -1) return { headers: "", body: text };
  const head = text.slice(0, idx);
  const rest = text.slice(idx).replace(/^\r?\n\r?\n/, "");
  const looksLikeHeaders = /^HTTP\/\d/.test(head.trim()) || /^[\w-]+:\s/.test(head.trim());
  if (looksLikeHeaders && rest.trim()) return { headers: head, body: rest };
  return { headers: "", body: text };
}

// Minimal, dependency-free HTML indenter — not a real parser (doesn't track
// unclosed/malformed tags perfectly), just reflows a blob of HTML onto one
// tag per line with nesting-based indentation, which is what makes a dumped
// page readable at a glance.
function formatHtml(html: string): string {
  const withBreaks = html.replace(/>\s*</g, ">\n<").replace(/\n{2,}/g, "\n");
  const lines = withBreaks.split("\n").map((l) => l.trim()).filter(Boolean);

  let depth = 0;
  const out: string[] = [];
  for (const line of lines) {
    const isComment = /^<!--/.test(line);
    const isDoctype = /^<!doctype/i.test(line);
    const isClosing = !isComment && /^<\//.test(line);
    const tagName = /^<\/?([a-zA-Z0-9-]+)/.exec(line)?.[1]?.toLowerCase();
    const isSelfClosing = /\/>\s*$/.test(line) || (tagName ? VOID_TAGS.has(tagName) : false);
    const isOpenCloseSameLine = tagName ? new RegExp(`</${tagName}>\\s*$`, "i").test(line) : false;

    if (isClosing) depth = Math.max(0, depth - 1);
    out.push("  ".repeat(depth) + line);
    if (!isClosing && !isSelfClosing && !isComment && !isDoctype && !isOpenCloseSameLine) {
      depth += 1;
    }
  }
  return out.join("\n");
}

export function detectAndFormat(raw: string): PrettyResult | null {
  const { headers, body } = splitHeadersAndBody(raw);
  const trimmed = body.trim();
  if (!trimmed) return null;

  if (/^[{[]/.test(trimmed)) {
    try {
      const parsed = JSON.parse(trimmed);
      const pretty = JSON.stringify(parsed, null, 2);
      return { kind: "json", formatted: headers ? `${headers}\n\n${pretty}` : pretty };
    } catch {
      // Not actually valid JSON as a whole (e.g. NDJSON, or JSON-looking
      // log lines) — fall through to the HTML check below.
    }
  }

  const looksLikeHtml =
    /^<!doctype html/i.test(trimmed) ||
    /^<html[\s>]/i.test(trimmed) ||
    (/<\/[a-zA-Z]+>/.test(trimmed) && /<[a-zA-Z][^>]*>/.test(trimmed));
  if (looksLikeHtml) {
    const pretty = formatHtml(trimmed);
    return { kind: "html", formatted: headers ? `${headers}\n\n${pretty}` : pretty };
  }

  return null;
}
