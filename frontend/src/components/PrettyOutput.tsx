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
const HTML_TOKEN_RE =
  /(<!--[\s\S]*?-->)|(<\/?[a-zA-Z][a-zA-Z0-9-]*)|(\b[a-zA-Z-]+(?==))|("(?:\\.|[^"\\])*")|(\/?>)/g;

function renderHtmlLine(line: string, lineKey: number): ReactNode {
  const out: ReactNode[] = [];
  let pos = 0;
  let k = 0;
  let m: RegExpExecArray | null;
  HTML_TOKEN_RE.lastIndex = 0;
  while ((m = HTML_TOKEN_RE.exec(line))) {
    if (m.index > pos) out.push(line.slice(pos, m.index));
    const [text, comment, tag, attr, str, close] = m;
    if (comment) {
      out.push(
        <span key={k++} className="text-neutral-500 italic">
          {text}
        </span>
      );
    } else if (tag) {
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

export function PrettyOutput({ text, kind }: { text: string; kind: PrettyKind }) {
  const lines = text.split("\n");
  const render = kind === "json" ? renderJsonLine : renderHtmlLine;
  return <>{lines.map((l, i) => render(l, i))}</>;
}
