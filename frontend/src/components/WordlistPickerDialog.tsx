"use client";

import { useEffect, useMemo, useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import InputAdornment from "@mui/material/InputAdornment";
import Stack from "@mui/material/Stack";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";
import SearchIcon from "@mui/icons-material/Search";
import StarIcon from "@mui/icons-material/Star";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import { api } from "@/lib/api";
import type { GroupedWordlists, WordlistGroup, WordlistInfo } from "@/lib/types";

export function WordlistPickerDialog({
  itemId,
  currentPath,
  onSelect,
  onClose,
}: {
  itemId: string;
  currentPath: string;
  onSelect: (path: string) => void;
  onClose: () => void;
}) {
  const [data, setData] = useState<GroupedWordlists | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");

  useEffect(() => {
    let cancelled = false;
    api
      .listWordlistsGrouped(itemId)
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch(() => {
        if (!cancelled) setError("Could not reach the backend to list wordlists.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [itemId]);

  const filteredGroups = useMemo<WordlistGroup[]>(() => {
    if (!data) return [];
    const q = query.trim().toLowerCase();
    if (!q) return data.groups;
    return data.groups
      .map((g) => ({
        ...g,
        wordlists: g.wordlists.filter(
          (w) => w.label.toLowerCase().includes(q) || g.category.toLowerCase().includes(q)
        ),
      }))
      .filter((g) => g.wordlists.length > 0);
  }, [data, query]);

  const totalCount = useMemo(
    () => (data?.groups ?? []).reduce((sum, g) => sum + g.wordlists.length, 0),
    [data]
  );

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="md">
      <DialogTitle>
        Select wordlist
        {data?.recommended_category_label && (
          <Typography component="div" variant="caption" color="text.secondary" sx={{ mt: 0.25 }}>
            Recommended for this test: <strong>{data.recommended_category_label}</strong>
          </Typography>
        )}
      </DialogTitle>
      <DialogContent>
        <TextField
          fullWidth
          size="small"
          autoFocus
          placeholder="Search wordlists…"
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

        {loading && (
          <Stack alignItems="center" py={4}>
            <CircularProgress size={28} />
          </Stack>
        )}

        {!loading && error && (
          <Typography color="error" variant="body2">
            {error}
          </Typography>
        )}

        {!loading && !error && totalCount === 0 && (
          <Typography variant="body2" color="text.secondary">
            No wordlists found on this host — install SecLists (
            <code>apt install seclists</code> on Kali/Debian, or set a custom directory in
            Settings) or use surveil&apos;s bundled defaults.
          </Typography>
        )}

        {!loading && !error && filteredGroups.length === 0 && totalCount > 0 && (
          <Typography variant="body2" color="text.secondary">
            No wordlists match &quot;{query}&quot;.
          </Typography>
        )}

        {!loading && !error && (
          <Box mb={2.5}>
            <Box
              role="button"
              tabIndex={0}
              onClick={() => onSelect("")}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") onSelect("");
              }}
              sx={{
                cursor: "pointer",
                border: "1px dashed",
                borderColor: currentPath === "" ? "#22c55e" : "divider",
                bgcolor: currentPath === "" ? "rgba(34,197,94,0.08)" : "transparent",
                borderRadius: 1,
                px: 1.25,
                py: 0.75,
                display: "inline-block",
                "&:hover": { borderColor: "#22c55e" },
              }}
            >
              <Typography variant="body2" sx={{ fontFamily: "var(--font-geist-mono)", fontSize: 13 }}>
                Use tool default
              </Typography>
            </Box>
          </Box>
        )}

        <Stack spacing={2.5}>
          {filteredGroups.map((group) => (
            <Box key={group.category}>
              <Stack direction="row" spacing={1} alignItems="center" mb={1}>
                {group.recommended && <StarIcon sx={{ fontSize: 16, color: "#22c55e" }} />}
                <Typography
                  variant="subtitle2"
                  sx={{
                    fontFamily: "var(--font-geist-mono)",
                    color: group.recommended ? "#22c55e" : "text.secondary",
                  }}
                >
                  {group.category}
                </Typography>
                <Chip label={group.wordlists.length} size="small" variant="outlined" />
              </Stack>
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
                  gap: 1,
                }}
              >
                {group.wordlists.map((w: WordlistInfo) => {
                  const selected = w.path === currentPath;
                  return (
                    <Box
                      key={w.path}
                      role="button"
                      tabIndex={0}
                      onClick={() => onSelect(w.path)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") onSelect(w.path);
                      }}
                      sx={{
                        cursor: "pointer",
                        border: "1px solid",
                        borderColor: selected ? "#22c55e" : "divider",
                        bgcolor: selected ? "rgba(34,197,94,0.08)" : "transparent",
                        borderRadius: 1,
                        px: 1.25,
                        py: 1,
                        display: "flex",
                        alignItems: "flex-start",
                        gap: 0.75,
                        transition: "border-color 0.15s, background-color 0.15s",
                        "&:hover": { borderColor: "#22c55e" },
                      }}
                    >
                      <DescriptionOutlinedIcon
                        fontSize="small"
                        sx={{ color: selected ? "#22c55e" : "text.secondary", mt: 0.25 }}
                      />
                      <Box minWidth={0}>
                        <Typography
                          variant="body2"
                          noWrap
                          title={w.label}
                          sx={{ fontFamily: "var(--font-geist-mono)", fontSize: 13 }}
                        >
                          {w.label.split("/").pop()}
                        </Typography>
                        <Typography
                          variant="caption"
                          color="text.disabled"
                          noWrap
                          title={w.path}
                          display="block"
                        >
                          {w.path}
                        </Typography>
                      </Box>
                    </Box>
                  );
                })}
              </Box>
            </Box>
          ))}
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose}>Cancel</Button>
      </DialogActions>
    </Dialog>
  );
}
