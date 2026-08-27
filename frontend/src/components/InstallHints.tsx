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

// Which OS(es) each package-manager key actually targets — the manager
// name alone (e.g. "go") doesn't tell a tester whether it'll work on
// their machine the way "brew"/"apt" obviously do. Covers every key
// currently used across surveil/tools/*.py's install_hints; an unknown
// future key falls back to "Cross-platform" rather than guessing wrong.
const MGR_OS: Record<string, string> = {
  brew: "macOS",
  apt: "Linux (Debian/Ubuntu/Kali)",
  go: "macOS/Linux",
  pip: "macOS/Linux",
  pipx: "macOS/Linux",
  gem: "macOS/Linux",
  git: "macOS/Linux",
};

function CopyRow({ label, command }: { label: string; command: string }) {
  const [copied, setCopied] = useState(false);
  const os = MGR_OS[label] ?? "Cross-platform";

  function copy() {
    navigator.clipboard?.writeText(command);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <Box>
      <Stack direction="row" spacing={0.75} alignItems="center" mb={0.5}>
        <Chip label={label} size="small" sx={{ width: 46, fontFamily: "var(--font-geist-mono)" }} />
        <Chip
          label={os}
          size="small"
          variant="outlined"
          sx={{
            height: 18,
            fontSize: 10,
            color: "text.secondary",
            borderColor: "divider",
          }}
        />
      </Stack>
      <Stack direction="row" spacing={1} alignItems="center">
        <Box
          component="code"
          sx={{
            flex: 1,
            minWidth: 0,
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
    </Box>
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
      <Stack spacing={1.25}>
        {entries.map(([mgr, cmd]) => (
          <CopyRow key={mgr} label={mgr} command={cmd} />
        ))}
      </Stack>
    </Alert>
  );
}
