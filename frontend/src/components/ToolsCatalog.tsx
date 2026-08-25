"use client";

import { useEffect, useMemo, useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import Button from "@mui/material/Button";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import InputAdornment from "@mui/material/InputAdornment";
import IconButton from "@mui/material/IconButton";
import CircularProgress from "@mui/material/CircularProgress";
import SearchIcon from "@mui/icons-material/Search";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import CheckIcon from "@mui/icons-material/Check";
import { api } from "@/lib/api";
import { ToolLogo } from "@/components/ToolLogo";
import { InstallHints } from "@/components/InstallHints";
import type { ToolInfo } from "@/lib/types";

function ExampleRow({ example }: { example: string }) {
  const [copied, setCopied] = useState(false);

  function copy() {
    navigator.clipboard?.writeText(example);
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
  }

  return (
    <Stack direction="row" spacing={1} alignItems="center">
      <Box
        component="code"
        sx={{
          flex: 1,
          fontFamily: "var(--font-geist-mono)",
          fontSize: 12,
          bgcolor: "rgba(0,0,0,0.35)",
          border: "1px solid rgba(255,255,255,0.08)",
          borderRadius: 1,
          px: 1,
          py: 0.5,
          overflowX: "auto",
          whiteSpace: "nowrap",
        }}
      >
        {example}
      </Box>
      <IconButton size="small" onClick={copy} title="Copy example command">
        {copied ? <CheckIcon fontSize="small" color="success" /> : <ContentCopyIcon fontSize="small" />}
      </IconButton>
    </Stack>
  );
}

function ToolCard({ tool }: { tool: ToolInfo }) {
  return (
    <Box
      sx={{
        border: "1px solid",
        borderColor: "divider",
        borderRadius: 1.5,
        p: 2,
        display: "flex",
        flexDirection: "column",
        gap: 1,
      }}
    >
      <Stack direction="row" spacing={1.25} alignItems="center">
        <ToolLogo name={tool.name} size={32} dim={!tool.available} />
        <Box minWidth={0} flex={1}>
          <Typography
            variant="subtitle1"
            fontWeight={700}
            sx={{ fontFamily: "var(--font-geist-mono)" }}
          >
            {tool.name}
          </Typography>
        </Box>
        <Chip
          label={tool.available ? "installed" : "not installed"}
          size="small"
          color={tool.available ? "success" : "default"}
          variant={tool.available ? "filled" : "outlined"}
        />
      </Stack>

      <Typography variant="body2" color="text.secondary">
        {tool.description}
      </Typography>

      <Box>
        <Typography variant="caption" color="text.disabled" display="block" mb={0.5}>
          Example
        </Typography>
        <ExampleRow example={tool.example} />
      </Box>

      {tool.uses_wordlist && (
        <Chip label="uses a wordlist" size="small" variant="outlined" sx={{ alignSelf: "flex-start" }} />
      )}
      {tool.domain_only && (
        <Chip
          label="domain targets only"
          size="small"
          variant="outlined"
          color="warning"
          sx={{ alignSelf: "flex-start" }}
        />
      )}
      {Object.keys(tool.modes).length > 0 && (
        <Typography variant="caption" color="text.disabled">
          Scan modes: {Object.values(tool.modes).join(", ")}
        </Typography>
      )}

      {!tool.available && <InstallHints toolName={tool.name} hints={tool.install_hints} />}
    </Box>
  );
}

export function ToolsCatalog({ onClose }: { onClose: () => void }) {
  const [tools, setTools] = useState<ToolInfo[] | null>(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");

  useEffect(() => {
    let cancelled = false;
    api
      .listTools()
      .then((res) => {
        if (!cancelled) setTools(res);
      })
      .catch(() => {
        if (!cancelled) setError("Could not reach the backend to list tools.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(() => {
    if (!tools) return [];
    const q = query.trim().toLowerCase();
    if (!q) return tools;
    return tools.filter(
      (t) => t.name.toLowerCase().includes(q) || t.description.toLowerCase().includes(q)
    );
  }, [tools, query]);

  const installedCount = tools?.filter((t) => t.available).length ?? 0;

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="lg" scroll="paper">
      <DialogTitle>
        Tools
        {tools && (
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.25 }}>
            {installedCount} of {tools.length} installed on this backend host
          </Typography>
        )}
      </DialogTitle>
      <DialogContent dividers sx={{ bgcolor: "background.default" }}>
        <TextField
          fullWidth
          size="small"
          placeholder="Search tools by name or what they do…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          slotProps={{
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              ),
            },
          }}
          sx={{ mb: 2 }}
        />

        {!tools && !error && (
          <Stack alignItems="center" py={6}>
            <CircularProgress size={28} />
          </Stack>
        )}
        {error && (
          <Typography color="error" variant="body2">
            {error}
          </Typography>
        )}
        {tools && filtered.length === 0 && (
          <Typography variant="body2" color="text.secondary">
            No tools match &quot;{query}&quot;.
          </Typography>
        )}

        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))",
            gap: 1.5,
          }}
        >
          {filtered.map((tool) => (
            <ToolCard key={tool.name} tool={tool} />
          ))}
        </Box>
      </DialogContent>
      <DialogActions sx={{ px: 3, py: 1.5 }}>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}
