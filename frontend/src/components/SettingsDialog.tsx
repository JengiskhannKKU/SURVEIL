"use client";

import { useEffect, useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import TextField from "@mui/material/TextField";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import { api } from "@/lib/api";
import { useToast } from "@/lib/toast";
import type { AppConfig } from "@/lib/types";

export function SettingsDialog({ onClose }: { onClose: () => void }) {
  const toast = useToast();
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [wordlistDir, setWordlistDir] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .getConfig()
      .then((c) => {
        setConfig(c);
        setWordlistDir(c.wordlist_dir ?? "");
      })
      .catch(() => toast.error("Could not reach the backend to load settings."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function save() {
    setSaving(true);
    setError("");
    try {
      const updated = await api.setWordlistDir(wordlistDir.trim() || null);
      setConfig(updated);
      toast.success(
        updated.wordlist_dir
          ? `Wordlist directory set — ${updated.wordlists_found} wordlist(s) found`
          : "Wordlist directory cleared"
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save.");
    } finally {
      setSaving(false);
    }
  }

  async function clear() {
    setWordlistDir("");
    setSaving(true);
    setError("");
    try {
      const updated = await api.setWordlistDir(null);
      setConfig(updated);
      toast.success("Wordlist directory cleared");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to clear.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>Settings</DialogTitle>
      <DialogContent>
        <Stack spacing={2} mt={0.5}>
          <Box>
            <Typography variant="subtitle2" fontWeight={700} mb={0.5}>
              Wordlist directory
            </Typography>
            <Typography variant="body2" color="text.secondary" mb={1.5}>
              Used by <code>ffuf</code>/<code>gobuster</code> as the default
              wordlist, and to populate the wordlist picker in the Run Tool
              dialog. Point it at a directory (searched recursively for{" "}
              <code>*.txt</code>) or a specific wordlist file — a SecLists
              checkout, for example.
            </Typography>
            <TextField
              fullWidth
              size="small"
              placeholder="/path/to/SecLists or /path/to/wordlist.txt"
              value={wordlistDir}
              disabled={saving}
              onChange={(e) => setWordlistDir(e.target.value)}
              slotProps={{ input: { sx: { fontFamily: "var(--font-geist-mono)", fontSize: 13 } } }}
            />
          </Box>

          {error && <Alert severity="error">{error}</Alert>}

          {config && (
            <Alert severity="info" variant="outlined">
              <Typography variant="body2" sx={{ fontFamily: "var(--font-geist-mono)", fontSize: 12.5 }}>
                Effective default: {config.default_wordlist}
              </Typography>
              {config.wordlist_dir_env && !config.wordlist_dir && (
                <Typography variant="caption" color="text.secondary" display="block" mt={0.5}>
                  SURVEIL_WORDLIST_DIR env var is set to {config.wordlist_dir_env} — the
                  setting above, once saved, takes priority over it.
                </Typography>
              )}
              <Typography variant="caption" color="text.secondary" display="block" mt={0.5}>
                {config.wordlists_found} wordlist(s) found from the configured directory (or
                the host&apos;s common install locations if none is set).
              </Typography>
            </Alert>
          )}
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2.5 }}>
        <Button onClick={clear} disabled={saving || !config?.wordlist_dir} color="error">
          Clear
        </Button>
        <Box flex={1} />
        <Button onClick={onClose}>Close</Button>
        <Button onClick={save} variant="contained" disabled={saving}>
          {saving ? "Saving…" : "Save"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
