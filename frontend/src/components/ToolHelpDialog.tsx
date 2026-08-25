"use client";

import { useEffect, useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import Button from "@mui/material/Button";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";
import { api } from "@/lib/api";
import { ToolLogo } from "@/components/ToolLogo";
import { InstallHints } from "@/components/InstallHints";
import type { ToolInfo } from "@/lib/types";

// Shows a tool's real --help output (the actual binary's usage text, e.g.
// what `nmap -h` prints) rather than a hand-maintained summary that drifts
// from the installed version. Falls back to the description/example
// already shown in the Run Tool dialog when the binary isn't installed —
// there's nothing to shell out to.
export function ToolHelpDialog({ tool, onClose }: { tool: ToolInfo; onClose: () => void }) {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    api
      .getToolHelp(tool.name)
      .then((res) => {
        if (cancelled) return;
        setText(res.text);
      })
      .catch(() => {
        if (!cancelled) setError("Could not reach the backend to load help output.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [tool.name]);

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="md">
      <DialogTitle sx={{ display: "flex", alignItems: "center", gap: 1.25 }}>
        <ToolLogo name={tool.name} size={26} dim={!tool.available} />
        <Box>
          <Typography variant="subtitle1" fontWeight={700} sx={{ fontFamily: "var(--font-geist-mono)" }}>
            {tool.name} {tool.available ? tool.help_flag : ""}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {tool.description}
          </Typography>
        </Box>
      </DialogTitle>
      <DialogContent>
        {!tool.available && (
          <Stack spacing={1.5} mb={2}>
            <Typography variant="body2" color="text.secondary">
              {tool.name} isn&apos;t installed on this host, so its real --help output can&apos;t
              be shown. Here&apos;s what an example invocation looks like:
            </Typography>
            <Box
              component="pre"
              sx={{
                m: 0,
                borderRadius: 1,
                bgcolor: "#000",
                border: "1px solid rgba(255,255,255,0.08)",
                px: 1.5,
                py: 1,
                fontFamily: "var(--font-geist-mono), monospace",
                fontSize: 12.5,
                color: "rgba(255,255,255,0.8)",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}
            >
              {tool.example}
            </Box>
            <InstallHints toolName={tool.name} hints={tool.install_hints} />
          </Stack>
        )}

        {tool.available && loading && (
          <Stack direction="row" spacing={1.5} alignItems="center" py={3} justifyContent="center">
            <CircularProgress size={18} />
            <Typography variant="body2" color="text.secondary">
              Running {tool.name} {tool.help_flag}…
            </Typography>
          </Stack>
        )}

        {tool.available && !loading && error && (
          <Typography variant="body2" color="error">
            {error}
          </Typography>
        )}

        {tool.available && !loading && !error && (
          <Box
            component="pre"
            sx={{
              m: 0,
              maxHeight: 480,
              overflow: "auto",
              borderRadius: 1,
              bgcolor: "#000",
              border: "1px solid rgba(255,255,255,0.08)",
              px: 1.5,
              py: 1,
              fontFamily: "var(--font-geist-mono), monospace",
              fontSize: 12.5,
              lineHeight: 1.6,
              color: "rgba(255,255,255,0.8)",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}
          >
            {text || "(no help output)"}
          </Box>
        )}
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2.5 }}>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}
