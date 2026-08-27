import type { ReactNode } from "react";
import type { PrettyKind } from "@/lib/prettyFormat";

// Group indices: 1 object key · 2 string value · 3 true/false/null ·
// 4 number · 5 punctuation
const JSON_TOKEN_RE =
  /("(?:\\.|[^"\\])*"(?=\s*:))|("(?:\\.|[^"\\])*")|(\btrue\b|\bfalse\b|\bnull\b)|(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)|([{}[\],:])/g;

function renderJsonLine(line: string, lineKey: number): ReactNode {
  const out: ReactNode[] = [];
  let pos = 0;
  let k = 0;
  let m: RegExpExecArray | null;
  JSON_TOKEN_RE.lastIndex = 0;
  while ((m = JSON_TOKEN_RE.exec(line))) {
    if (m.index > pos) out.push(line.slice(pos, m.index));
    const [text, key, str, boolNull, num, punct] = m;
    if (key) {
      out.push(
        <span key={k++} className="text-cyan-300">
          {text}
        </span>
      );
    } else if (str) {
      out.push(
        <span key={k++} className="text-amber-300">
          {text}
        </span>
      );
    } else if (boolNull) {
      out.push(
        <span key={k++} className="text-fuchsia-300">
          {text}
        </span>
      );
    } else if (num) {
      out.push(
        <span key={k++} className="text-sky-300">
          {text}
        </span>
      );
    } else if (punct) {
      out.push(
        <span key={k++} className="text-neutral-500">
          {text}
        </span>
      );
    } else {
      out.push(text);
    }
    pos = m.index + text.length;
  }
  if (pos < line.length) out.push(line.slice(pos));
  return <div key={lineKey}>{out.length ? out : " "}</div>;
}

// Group indices: 1 comment · 2 opening/closing tag name · 3 attribute name ·
// 4 attribute string value · 5 closing bracket(s)
// Tag/attribute name classes include `:` and `.` so this also covers
// namespaced XML tags (`<xhtml:link>`, `xmlns:xhtml=`), reused for both
// "html" and "xml" kinds below rather than duplicating this regex.
const MARKUP_TOKEN_RE =
  /(<!--[\s\S]*?-->)|(<\?[a-zA-Z][\w:.-]*)|(<\/?[a-zA-Z][\w:.-]*)|(\b[a-zA-Z][\w:.-]*(?==))|("(?:\\.|[^"\\])*")|(\?>|\/?>)/g;

function renderMarkupLine(line: string, lineKey: number): ReactNode {
  const out: ReactNode[] = [];
  let pos = 0;
  let k = 0;
  let m: RegExpExecArray | null;
  MARKUP_TOKEN_RE.lastIndex = 0;
  while ((m = MARKUP_TOKEN_RE.exec(line))) {
    if (m.index > pos) out.push(line.slice(pos, m.index));
    const [text, comment, decl, tag, attr, str, close] = m;
    if (comment) {
      out.push(
        <span key={k++} className="text-neutral-500 italic">
          {text}
        </span>
      );
    } else if (decl || tag) {
      out.push(
        <span key={k++} className="text-cyan-300 font-semibold">
          {text}
        </span>
      );
    } else if (attr) {
      out.push(
        <span key={k++} className="text-amber-200">
          {text}
        </span>
      );
    } else if (str) {
      out.push(
        <span key={k++} className="text-green-300">
          {text}
        </span>
      );
    } else if (close) {
      out.push(
        <span key={k++} className="text-cyan-300 font-semibold">
          {text}
        </span>
      );
    } else {
      out.push(text);
    }
    pos = m.index + text.length;
  }
  if (pos < line.length) out.push(line.slice(pos));
  return <div key={lineKey}>{out.length ? out : " "}</div>;
}

const JS_KEYWORDS =
  "function|return|const|let|var|if|else|for|while|do|switch|case|break|continue|" +
  "class|extends|new|this|super|import|export|from|default|async|await|try|catch|" +
  "finally|throw|typeof|instanceof|in|of|null|undefined|true|false|void|yield|delete";

// Group indices: 1 line/block comment · 2 string/template literal ·
// 3 keyword · 4 number · 5 punctuation
const JS_TOKEN_RE = new RegExp(
  "(//.*$|/\\*[\\s\\S]*?\\*/)" +
    '|("(?:\\\\.|[^"\\\\])*"|\'(?:\\\\.|[^\'\\\\])*\'|`(?:\\\\.|[^`\\\\])*`)' +
    "|\\b(" + JS_KEYWORDS + ")\\b" +
    "|(-?\\b\\d+(?:\\.\\d+)?\\b)" +
    "|([{}()[\\];,.:=+\\-*/<>!&|?])",
  "gm"
);

function renderJsLine(line: string, lineKey: number): ReactNode {
  const out: ReactNode[] = [];
  let pos = 0;
  let k = 0;
  let m: RegExpExecArray | null;
  JS_TOKEN_RE.lastIndex = 0;
  while ((m = JS_TOKEN_RE.exec(line))) {
    if (m.index > pos) out.push(line.slice(pos, m.index));
    const [text, comment, str, keyword, num, punct] = m;
    if (comment) {
      out.push(
        <span key={k++} className="text-neutral-500 italic">
          {text}
        </span>
      );
    } else if (str) {
      out.push(
        <span key={k++} className="text-amber-300">
          {text}
        </span>
      );
    } else if (keyword) {
      out.push(
        <span key={k++} className="text-fuchsia-300">
          {text}
        </span>
      );
    } else if (num) {
      out.push(
        <span key={k++} className="text-sky-300">
          {text}
        </span>
      );
    } else if (punct) {
      out.push(
        <span key={k++} className="text-neutral-500">
          {text}
        </span>
      );
    } else {
      out.push(text);
    }
    pos = m.index + text.length;
  }
  if (pos < line.length) out.push(line.slice(pos));
  return <div key={lineKey}>{out.length ? out : " "}</div>;
}

const RENDERERS: Record<PrettyKind, (line: string, key: number) => ReactNode> = {
  json: renderJsonLine,
  html: renderMarkupLine,
  xml: renderMarkupLine,
  javascript: renderJsLine,
};

export function PrettyOutput({ text, kind }: { text: string; kind: PrettyKind }) {
  const lines = text.split("\n");
  const render = RENDERERS[kind];
  return <>{lines.map((l, i) => render(l, i))}</>;
}
