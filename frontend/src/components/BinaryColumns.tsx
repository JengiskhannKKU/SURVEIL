// Fixed (not random-per-render) digit pattern — random content generated at
// render time would mismatch between server and client and trigger a
// hydration error, so this is just a hardcoded "looks random" string table.
const ROWS = [
  "1 0 0 1", "0 1 1 1", "1 1 1 1", "1 1 0 0", "0 0 0 0", "1 0 1 1",
  "0 0 1 1", "0 1 0 1", "0 0 0 1", "0 0 1 1", "1 0 1 1", "1 1 0 1",
  "0 0 0 1", "0 1 1 0", "0 1 1 0", "1 1 1 0", "1 0 0 1", "0 0 0 0",
  "1 1 0 0", "1 0 1 0", "1 1 1 0", "1 1 1 0", "0 1 1 1", "0 0 1 0",
  "1 0 1 0", "1 1 1 1", "1 1 1 1", "1 0 0 0",
];

function Column({ align }: { align: "left" | "right" }) {
  return (
    <div
      aria-hidden
      style={{
        position: "absolute",
        top: 90,
        [align]: 24,
        display: "flex",
        flexDirection: "column",
        gap: 6,
        fontFamily: "var(--font-geist-mono), monospace",
        fontSize: 12,
        color: "rgba(94,234,212,0.28)",
        userSelect: "none",
        textAlign: align,
      }}
    >
      {ROWS.map((row, i) => (
        <span key={i}>{row}</span>
      ))}
    </div>
  );
}

export function BinaryColumns() {
  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        overflow: "hidden",
      }}
      className="binary-columns"
    >
      <Column align="left" />
      <Column align="right" />
    </div>
  );
}
