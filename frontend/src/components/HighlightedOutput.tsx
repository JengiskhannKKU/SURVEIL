// Group indices (no named groups — avoids requiring an ES2018+ compile target):
// 1 url · 2 bracket-status · 3 "Status: NNN" · 4 severity tag · 5 CVE ·
// 6 [+] · 7 [-] · 8 warn glyph · 9 [!] · 10 OSVDB-id · 11 nmap "N/tcp open ..."
// port/state line · 12 risk keyword · 13 bare IPv4
const TOKEN_RE =
  /(https?:\/\/\S+)|\[(\d{3})\]|Status:\s*(\d{3})|\[(critical|high|medium|low|info)\]|(CVE-\d{4}-\d{4,7})|(\[\+\])|(\[-\])|(⚠)|(\[!\])|(OSVDB-\d+)|(\d{1,5}\/(?:tcp|udp)\s+(?:open\|filtered|open|filtered|closed)\S*)|\b(vulnerable|outdated|exposed|misconfigured|risky|sensitive|weak|takeover)\b|\b((?:\d{1,3}\.){3}\d{1,3})\b/gi;

const SEVERITY_COLOR: Record<string, string> = {
  critical: "text-red-400 font-bold",
  high: "text-red-400",
  medium: "text-yellow-300",
  low: "text-cyan-300",
  info: "text-neutral-400",
};

function statusColor(code: string): string {
  const n = parseInt(code, 10);
  if (n >= 200 && n < 300) return "text-green-400";
  if (n >= 300 && n < 400) return "text-yellow-300";
  if (n >= 400 && n < 500) return "text-red-400";
  if (n >= 500) return "text-red-400 font-bold";
  return "";
}

// "80/tcp   open  http" — color the state word by how interesting an open
// port is (definitely open > maybe open > closed/filtered), leave the
// port/protocol and service name in the default terminal color.
function portLineNode(text: string, key: number): React.ReactNode {
  const m = /^(\d{1,5}\/(?:tcp|udp))(\s+)(open\|filtered|open|filtered|closed)(\S*)$/i.exec(text);
  if (!m) return text;
  const [, port, gap, state, rest] = m;
  const lower = state.toLowerCase();
  const stateClass =
    lower === "open"
      ? "text-green-400 font-bold"
      : lower === "open|filtered"
        ? "text-yellow-300"
        : "text-neutral-500";
  return (
    <span key={key}>
      {port}
      {gap}
      <span className={stateClass}>{state}</span>
      {rest}
    </span>
  );
}

function renderSegments(line: string): React.ReactNode[] {
  const out: React.ReactNode[] = [];
  let pos = 0;
  let key = 0;
  TOKEN_RE.lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = TOKEN_RE.exec(line))) {
    if (m.index > pos) out.push(line.slice(pos, m.index));
    const [text, url, bstatus, lstatus, sev, cve, bplus, bminus, warn, bang, osvdb, portLine, risk, ip] = m;
    if (url) {
      out.push(
        <span key={key++} className="text-cyan-300">
          {text}
        </span>
      );
    } else if (bstatus) {
      out.push(
        <span key={key++} className={statusColor(bstatus)}>
          {text}
        </span>
      );
    } else if (lstatus) {
      out.push(
        <span key={key++} className={statusColor(lstatus)}>
          {text}
        </span>
      );
    } else if (sev) {
      out.push(
        <span key={key++} className={SEVERITY_COLOR[sev.toLowerCase()] ?? ""}>
          {text}
        </span>
      );
    } else if (cve) {
      out.push(
        <span key={key++} className="font-bold text-fuchsia-300">
          {text}
        </span>
      );
    } else if (bplus) {
      out.push(
        <span key={key++} className="text-green-400">
          {text}
        </span>
      );
    } else if (bminus) {
      out.push(
        <span key={key++} className="text-red-400">
          {text}
        </span>
      );
    } else if (warn) {
      out.push(
        <span key={key++} className="text-yellow-300">
          {text}
        </span>
      );
    } else if (bang) {
      out.push(
        <span key={key++} className="text-red-400 font-bold">
          {text}
        </span>
      );
    } else if (osvdb) {
      out.push(
        <span key={key++} className="font-bold text-fuchsia-300">
          {text}
        </span>
      );
    } else if (portLine) {
      out.push(portLineNode(text, key++));
    } else if (risk) {
      out.push(
        <span key={key++} className="text-orange-400 font-semibold">
          {text}
        </span>
      );
    } else if (ip) {
      out.push(
        <span key={key++} className="text-cyan-300">
          {text}
        </span>
      );
    } else {
      out.push(text);
    }
    pos = m.index + text.length;
  }
  if (pos < line.length) out.push(line.slice(pos));
  return out;
}

export function HighlightedLine({ line }: { line: string }) {
  const simulated = line.toUpperCase().includes("SIMULATED");
  return (
    <div className={simulated ? "font-bold text-yellow-300" : undefined}>
      {renderSegments(line) || " "}
    </div>
  );
}

export function HighlightedOutput({ text }: { text: string }) {
  const lines = text.split("\n");
  return (
    <>
      {lines.map((l, i) => (
        <HighlightedLine key={i} line={l} />
      ))}
    </>
  );
}
