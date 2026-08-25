"use client";

import Box from "@mui/material/Box";
import Tooltip from "@mui/material/Tooltip";
import { toolLogo } from "@/lib/toolLogos";

export function ToolLogo({
  name,
  size = 24,
  dim = false,
}: {
  name: string;
  size?: number;
  dim?: boolean;
}) {
  const { label, color } = toolLogo(name);
  return (
    <Tooltip title={name} disableInteractive>
      <Box
        aria-hidden
        sx={{
          width: size,
          height: size,
          flexShrink: 0,
          borderRadius: "6px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          bgcolor: dim ? "rgba(255,255,255,0.06)" : `${color}26`,
          border: "1px solid",
          borderColor: dim ? "rgba(255,255,255,0.1)" : `${color}66`,
          color: dim ? "text.disabled" : color,
          fontFamily: "var(--font-geist-mono)",
          fontWeight: 700,
          fontSize: size * 0.36,
          letterSpacing: "-0.02em",
        }}
      >
        {label}
      </Box>
    </Tooltip>
  );
}
