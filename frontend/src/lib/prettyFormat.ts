// Detects a structured format embedded in raw tool output and reformats it
// for readability — no external dependency, just enough of a formatter to
// turn a minified/single-line blob into something a human can scan. Common
// shape this has to handle: curl -i / wget -S output is an HTTP header
// block, a blank line, then the actual body — the body is what's worth
// pretty-printing, the headers are left exactly as the tool printed them.
//
// When the output is real curl -i/wget -S output, its own Content-Type
// response header is the most reliable signal for what the body actually
// is (far more reliable than guessing from the bytes alone) — checked
// first, with content-sniffing only as a fallback for output that has no
// header block at all (e.g. `wget -O -` without `-S`).

export type PrettyKind = "json" | "html" | "xml" | "javascript";

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

function contentTypeKind(headers: string): PrettyKind | null {
  const m = /^content-type:\s*([^\r\n;]+)/im.exec(headers);
  if (!m) return null;
  const type = m[1].trim().toLowerCase();
  if (type === "application/json" || type.endsWith("+json")) return "json";
  if (type === "text/html" || type === "application/xhtml+xml") return "html";
  if (type === "application/xml" || type === "text/xml" || type.endsWith("+xml")) return "xml";
  if (
    type === "application/javascript" ||
    type === "text/javascript" ||
    type === "application/x-javascript" ||
    type === "application/ecmascript"
  ) {
    return "javascript";
  }
  return null;
}

// Minimal, dependency-free tag-based indenter — not a real parser (doesn't
// track unclosed/malformed tags perfectly), just reflows a blob of
// HTML/XML onto one tag per line with nesting-based indentation, which is
// what makes a dumped page/document readable at a glance. XML has no void
// tags, so *treatAllAsPaired* skips that lookup for it.
function formatMarkup(markup: string, treatAllAsPaired: boolean): string {
  const withBreaks = markup.replace(/>\s*</g, ">\n<").replace(/\n{2,}/g, "\n");
  const lines = withBreaks.split("\n").map((l) => l.trim()).filter(Boolean);

  let depth = 0;
  const out: string[] = [];
  for (const line of lines) {
    const isComment = /^<!--/.test(line);
    const isDeclaration = /^<[?!]/.test(line);
    const isClosing = !isComment && /^<\//.test(line);
    const tagName = /^<\/?([a-zA-Z0-9_:.-]+)/.exec(line)?.[1]?.toLowerCase();
    const isSelfClosing =
      /\/>\s*$/.test(line) || (!treatAllAsPaired && tagName ? VOID_TAGS.has(tagName) : false);
    const isOpenCloseSameLine = tagName ? new RegExp(`</${tagName}>\\s*$`, "i").test(line) : false;

    if (isClosing) depth = Math.max(0, depth - 1);
    out.push("  ".repeat(depth) + line);
    if (!isClosing && !isSelfClosing && !isComment && !isDeclaration && !isOpenCloseSameLine) {
      depth += 1;
    }
  }
  return out.join("\n");
}

// Minimal, dependency-free JS reflow — not a real parser/AST-based
// formatter (no idea of expression boundaries), just enough brace/semicolon
// tracking to turn a minified or logically-unformatted script into
// something readable. Strings are protected from having their contents
// split on, so a `;` or `{` inside a string literal doesn't break the line.
function formatJavaScript(js: string): string {
  const withBreaks: string[] = [];
  let cur = "";
  let inString: '"' | "'" | "`" | null = null;
  for (let i = 0; i < js.length; i++) {
    const c = js[i];
    const prev = js[i - 1];
    cur += c;
    if (inString) {
      if (c === inString && prev !== "\\") inString = null;
      continue;
    }
    if (c === '"' || c === "'" || c === "`") {
      inString = c;
      continue;
    }
    if (c === "{" || c === ";") {
      withBreaks.push(cur);
      cur = "";
    } else if (c === "}") {
      if (cur.slice(0, -1).trim()) withBreaks.push(cur.slice(0, -1));
      withBreaks.push("}");
      cur = "";
    }
  }
  if (cur.trim()) withBreaks.push(cur);

  let depth = 0;
  const out: string[] = [];
  for (const raw of withBreaks) {
    const line = raw.trim();
    if (!line) continue;
    const closesFirst = line.startsWith("}");
    if (closesFirst) depth = Math.max(0, depth - 1);
    out.push("  ".repeat(depth) + line);
    const opens = (line.match(/{/g) || []).length;
    const closes = (line.match(/}/g) || []).length - (closesFirst ? 1 : 0);
    depth = Math.max(0, depth + opens - closes);
  }
  return out.join("\n");
}

function sniffKind(trimmed: string): PrettyKind | null {
  if (/^[{[]/.test(trimmed)) {
    try {
      JSON.parse(trimmed);
      return "json";
    } catch {
      // Not actually valid JSON as a whole (e.g. NDJSON, or JSON-looking
      // log lines) — fall through to the other checks below.
    }
  }
  if (/^<\?xml\s/.test(trimmed)) return "xml";
  if (/^<!doctype html/i.test(trimmed) || /^<html[\s>]/i.test(trimmed)) return "html";
  if (/<\/[a-zA-Z]+>/.test(trimmed) && /<[a-zA-Z][^>]*>/.test(trimmed)) return "html";
  // JS is the fuzziest of these to sniff blind (no angle brackets/braces to
  // anchor on the way markup has) — require several distinct, fairly
  // JS-specific signals together rather than any single common word, to
  // keep an ordinary log/text file from getting misdetected as code.
  const jsSignals = [
    /\bfunction\s*\w*\s*\(/, /=>\s*{/, /\b(const|let|var)\s+\w+\s*=/,
    /\bexport\s+(default\s+)?(function|class|const)/, /\bimport\s.+\sfrom\s['"]/,
    /\bconsole\.(log|error|warn)\(/, /document\.(getElementById|querySelector)/,
  ];
  const hits = jsSignals.filter((re) => re.test(trimmed)).length;
  if (hits >= 2) return "javascript";
  return null;
}

export function detectAndFormat(raw: string): PrettyResult | null {
  const { headers, body } = splitHeadersAndBody(raw);
  const trimmed = body.trim();
  if (!trimmed) return null;

  const kind = contentTypeKind(headers) ?? sniffKind(trimmed);
  if (!kind) return null;

  let pretty: string;
  try {
    if (kind === "json") pretty = JSON.stringify(JSON.parse(trimmed), null, 2);
    else if (kind === "html") pretty = formatMarkup(trimmed, false);
    else if (kind === "xml") pretty = formatMarkup(trimmed, true);
    else pretty = formatJavaScript(trimmed);
  } catch {
    // Content-Type said json but the body didn't actually parse (a
    // truncated response, an error page served with the wrong header,
    // etc.) — don't offer a "pretty" view of something that isn't
    // actually valid, fall back to no toggle at all.
    return null;
  }

  return { kind, formatted: headers ? `${headers}\n\n${pretty}` : pretty };
}
