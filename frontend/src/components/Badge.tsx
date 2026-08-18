import Chip from "@mui/material/Chip";
import type { Severity, Status } from "@/lib/types";
import { SEVERITY_COLOR } from "@/lib/severity";

const STATUS_META: Record<Status, { icon: string; color: string; bg: string }> = {
  pending: { icon: "○", color: "rgba(255,255,255,0.5)", bg: "rgba(255,255,255,0.08)" },
  running: { icon: "◎", color: "#f59e0b", bg: "rgba(245,158,11,0.14)" },
  done: { icon: "✓", color: "#22c55e", bg: "rgba(34,197,94,0.14)" },
  skipped: { icon: "—", color: "rgba(255,255,255,0.5)", bg: "rgba(255,255,255,0.08)" },
  failed: { icon: "✗", color: "#ef4444", bg: "rgba(239,68,68,0.14)" },
};

export function StatusBadge({ status }: { status: Status }) {
  const m = STATUS_META[status];
  return (
    <Chip
      size="small"
      label={`${m.icon} ${status}`}
      sx={{
        color: m.color,
        backgroundColor: m.bg,
        border: `1px solid ${m.color}33`,
        fontWeight: 600,
        textTransform: "capitalize",
      }}
    />
  );
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  const color = SEVERITY_COLOR[severity];
  return (
    <Chip
      size="small"
      label={severity.toUpperCase()}
      sx={{
        color: severity === "medium" ? "#111" : "#fff",
        backgroundColor: color,
        fontWeight: 700,
        letterSpacing: 0.3,
      }}
    />
  );
}
