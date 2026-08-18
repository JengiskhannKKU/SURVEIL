"use client";

import { useEffect, useMemo, useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import InputAdornment from "@mui/material/InputAdornment";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";
import SearchIcon from "@mui/icons-material/Search";
import StarIcon from "@mui/icons-material/Star";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import { api } from "@/lib/api";
import type { GroupedWordlists, WordlistGroup, WordlistInfo } from "@/lib/types";

const SAMPLE_SIZE = 6;

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
  // queryInput tracks every keystroke (for the field's own value); query is
  // the committed search that actually filters — only updated on Enter (or
  // immediately when the field is cleared), since filtering per-keystroke
  // across a large real SecLists install visibly lagged.
  const [queryInput, setQueryInput] = useState("");
  const [query, setQuery] = useState("");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  function commitSearch() {
    setQuery(queryInput.trim());
  }

  function toggleExpanded(category: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(category)) next.delete(category);
      else next.add(category);
      return next;
    });
  }

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
          placeholder="Search wordlists… (press Enter)"
          value={queryInput}
          onChange={(e) => {
            const val = e.target.value;
            setQueryInput(val);
            // Clearing the box is a "show everything again" action, not a
            // search — that one should be instant, not wait for Enter.
            if (val === "") setQuery("");
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter") commitSearch();
          }}
          slotProps={{
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <IconButton size="small" onClick={commitSearch} edge="start">
                    <SearchIcon fontSize="small" />
                  </IconButton>
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
          {filteredGroups.map((group) => {
            // A search query already narrows a group down to matches — capping
            // those further would hide results the tester just asked to see.
            const isSearching = query.trim().length > 0;
            const isExpanded = isSearching || expanded.has(group.category);
            const overflowing = group.wordlists.length > SAMPLE_SIZE;
            const visible = isExpanded ? group.wordlists : group.wordlists.slice(0, SAMPLE_SIZE);
            return (
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
                {visible.map((w: WordlistInfo) => {
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
              {!isSearching && overflowing && (
                <Button
                  size="small"
                  onClick={() => toggleExpanded(group.category)}
                  startIcon={expanded.has(group.category) ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                  sx={{ mt: 1, textTransform: "none", fontFamily: "var(--font-geist-mono)", fontSize: 12 }}
                >
                  {expanded.has(group.category)
                    ? "Show less"
                    : `Show all ${group.wordlists.length}`}
                </Button>
              )}
            </Box>
            );
          })}
        </Stack>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose}>Cancel</Button>
      </DialogActions>
    </Dialog>
  );
}
