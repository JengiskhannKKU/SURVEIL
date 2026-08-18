"use client";

import { useState } from "react";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import Alert from "@mui/material/Alert";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import CheckIcon from "@mui/icons-material/Check";

function CopyRow({ label, command }: { label: string; command: string }) {
  const [copied, setCopied] = useState(false);

  function copy() {
    navigator.clipboard?.writeText(command);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <Stack direction="row" spacing={1} alignItems="center">
      <Chip label={label} size="small" sx={{ width: 46, fontFamily: "var(--font-geist-mono)" }} />
      <Box
        component="code"
        sx={{
          flex: 1,
          fontFamily: "var(--font-geist-mono)",
          fontSize: 12.5,
          bgcolor: "rgba(0,0,0,0.35)",
          border: "1px solid rgba(255,255,255,0.08)",
          borderRadius: 1,
          px: 1,
          py: 0.5,
          overflowX: "auto",
          whiteSpace: "nowrap",
        }}
      >
        {command}
      </Box>
      <IconButton size="small" onClick={copy} title="Copy">
        {copied ? <CheckIcon fontSize="small" color="success" /> : <ContentCopyIcon fontSize="small" />}
      </IconButton>
    </Stack>
  );
}

export function InstallHints({
  toolName,
  hints,
}: {
  toolName: string;
  hints: Record<string, string>;
}) {
  const entries = Object.entries(hints);
  if (entries.length === 0) {
    return (
      <Alert severity="warning" variant="outlined">
        <Typography variant="body2">
          <strong>{toolName}</strong> isn&apos;t installed on the backend host — runs will use
          simulated demo output instead. No install command is on file for this tool.
        </Typography>
      </Alert>
    );
  }

  return (
    <Alert severity="warning" variant="outlined">
      <Typography variant="body2" mb={1}>
        <strong>{toolName}</strong> isn&apos;t installed on the backend host — runs will use
        simulated demo output until it is. Install it there with:
      </Typography>
      <Stack spacing={0.75}>
        {entries.map(([mgr, cmd]) => (
          <CopyRow key={mgr} label={mgr} command={cmd} />
        ))}
      </Stack>
    </Alert>
  );
}
