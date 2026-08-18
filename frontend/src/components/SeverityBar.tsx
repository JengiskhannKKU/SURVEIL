import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { motion } from "framer-motion";
import { SEVERITY_COLOR, SEVERITY_ORDER } from "@/lib/severity";
import type { Severity } from "@/lib/types";

export function SeverityBar({ counts }: { counts: Record<Severity, number> }) {
  const total = SEVERITY_ORDER.reduce((sum, s) => sum + counts[s], 0);

  if (total === 0) {
    return (
      <Box display="flex" alignItems="center" gap={1.5}>
        <Box
          sx={{
            height: 8,
            width: 160,
            borderRadius: 4,
            backgroundColor: "rgba(255,255,255,0.08)",
          }}
        />
        <Typography variant="caption" color="text.secondary">
          No findings yet
        </Typography>
      </Box>
    );
  }

  return (
    <Box display="flex" alignItems="center" gap={1.5} flexWrap="wrap">
      <Box
        sx={{
          display: "flex",
          height: 8,
          width: 160,
          borderRadius: 4,
          overflow: "hidden",
          backgroundColor: "rgba(255,255,255,0.08)",
        }}
      >
        {SEVERITY_ORDER.filter((s) => counts[s] > 0).map((s) => (
          <motion.div
            key={s}
            title={`${s}: ${counts[s]}`}
            initial={{ width: 0 }}
            animate={{ width: `${(counts[s] / total) * 100}%` }}
            transition={{ duration: 0.5, ease: "easeOut" }}
            style={{ backgroundColor: SEVERITY_COLOR[s] }}
          />
        ))}
      </Box>
      <Box display="flex" flexWrap="wrap" gap={1.5}>
        {SEVERITY_ORDER.filter((s) => counts[s] > 0).map((s) => (
          <Box key={s} display="flex" alignItems="center" gap={0.5}>
            <Box
              sx={{
                width: 8,
                height: 8,
                borderRadius: "50%",
                backgroundColor: SEVERITY_COLOR[s],
              }}
            />
            <Typography variant="caption" color="text.secondary">
              {counts[s]} {s}
            </Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
}

export function ProgressBar({ done, total }: { done: number; total: number }) {
  const pct = total === 0 ? 0 : Math.round((done / total) * 100);
  return (
    <Box display="flex" alignItems="center" gap={1.5}>
      <Box
        sx={{
          height: 8,
          width: 160,
          borderRadius: 4,
          overflow: "hidden",
          backgroundColor: "rgba(255,255,255,0.08)",
        }}
      >
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          style={{
            height: "100%",
            borderRadius: 4,
            background: "linear-gradient(90deg, #3b82f6, #22c55e)",
          }}
        />
      </Box>
      <Typography variant="caption" color="text.secondary" whiteSpace="nowrap">
        {done}/{total} ({pct}%)
      </Typography>
    </Box>
  );
}
