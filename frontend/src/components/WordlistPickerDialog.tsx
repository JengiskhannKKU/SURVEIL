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
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";
import SearchIcon from "@mui/icons-material/Search";
import StarIcon from "@mui/icons-material/Star";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import CloudDownloadOutlinedIcon from "@mui/icons-material/CloudDownloadOutlined";
import CloudDoneOutlinedIcon from "@mui/icons-material/CloudDoneOutlined";
import { api } from "@/lib/api";
import type {
  GroupedWordlists,
  RemoteGroupedWordlists,
  RemoteWordlistGroup,
  WordlistGroup,
} from "@/lib/types";

const SAMPLE_SIZE = 6;

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  return `${(bytes / 1024).toFixed(1)} KB`;
}

// Shared search box: filters live as you type nowhere — filtering (and its
// re-render across every category's cards) only runs on Enter/icon-click,
// since filtering per keystroke visibly lagged against a large wordlist set.
function SearchBox({
  queryInput,
  onInputChange,
  onCommit,
}: {
  queryInput: string;
  onInputChange: (v: string) => void;
  onCommit: () => void;
}) {
  return (
    <TextField
      fullWidth
      size="small"
      autoFocus
      placeholder="Search wordlists… (press Enter)"
      value={queryInput}
      onChange={(e) => onInputChange(e.target.value)}
      onKeyDown={(e) => {
        if (e.key === "Enter") onCommit();
      }}
      slotProps={{
        input: {
          startAdornment: (
            <InputAdornment position="start">
              <IconButton size="small" onClick={onCommit} edge="start">
                <SearchIcon fontSize="small" />
              </IconButton>
            </InputAdornment>
          ),
        },
      }}
      sx={{ mb: 2 }}
    />
  );
}

function LocalWordlistsPane({
  itemId,
  currentPath,
  onSelect,
}: {
  itemId: string;
  currentPath: string;
  onSelect: (path: string) => void;
}) {
  const [data, setData] = useState<GroupedWordlists | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [queryInput, setQueryInput] = useState("");
  const [query, setQuery] = useState("");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

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
    <Box>
      <SearchBox
        queryInput={queryInput}
        onInputChange={(v) => {
          setQueryInput(v);
          if (v === "") setQuery("");
        }}
        onCommit={() => setQuery(queryInput.trim())}
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
          Settings), use the &quot;SecLists (GitHub)&quot; tab to install individual files
          into this project on demand, or use surveil&apos;s bundled defaults.
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
                {visible.map((w) => {
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
                        <Typography variant="caption" color="text.disabled" noWrap title={w.path} display="block">
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
                  {expanded.has(group.category) ? "Show less" : `Show all ${group.wordlists.length}`}
                </Button>
              )}
            </Box>
          );
        })}
      </Stack>
    </Box>
  );
}

function RemoteWordlistsPane({
  itemId,
  currentPath,
  onSelect,
}: {
  itemId: string;
  currentPath: string;
  onSelect: (path: string) => void;
}) {
  const [data, setData] = useState<RemoteGroupedWordlists | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [queryInput, setQueryInput] = useState("");
  const [query, setQuery] = useState("");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [downloadingPath, setDownloadingPath] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState("");

  function fetchGroupsInner(q: string) {
    api
      .browseRemoteWordlists(itemId, q || undefined)
      .then((res) => {
        setData(res);
        setError("");
      })
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Could not reach GitHub to list SecLists.")
      )
      .finally(() => setLoading(false));
  }

  // Callers other than the initial mount need to flip loading back on
  // (the mount effect below relies on the useState(true) initial value
  // instead, so it doesn't need to call setState synchronously in the
  // effect body).
  function fetchGroups(q: string) {
    setLoading(true);
    fetchGroupsInner(q);
  }

  useEffect(() => {
    fetchGroupsInner("");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [itemId]);

  function toggleExpanded(category: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(category)) next.delete(category);
      else next.add(category);
      return next;
    });
  }

  async function handleSelect(path: string) {
    setDownloadingPath(path);
    setDownloadError("");
    try {
      const res = await api.downloadRemoteWordlist(path);
      onSelect(res.path);
    } catch (e) {
      setDownloadError(e instanceof Error ? e.message : `Could not download ${path}.`);
    } finally {
      setDownloadingPath(null);
    }
  }

  const groups: RemoteWordlistGroup[] = data?.groups ?? [];
  const totalCount = groups.reduce((sum, g) => sum + g.wordlists.length, 0);
  const isSearching = query.trim().length > 0;

  return (
    <Box>
      <SearchBox
        queryInput={queryInput}
        onInputChange={(v) => {
          setQueryInput(v);
          if (v === "") {
            setQuery("");
            fetchGroups("");
          }
        }}
        onCommit={() => {
          const q = queryInput.trim();
          setQuery(q);
          fetchGroups(q);
        }}
      />

      <Typography variant="caption" color="text.disabled" display="block" mb={2}>
        Installs only the single file you pick from{" "}
        <Box component="span" sx={{ fontFamily: "var(--font-geist-mono)" }}>
          github.com/danielmiessler/SecLists
        </Box>{" "}
        into this project (<code>surveil/data/wordlists_downloaded/</code>) — not the whole
        repository.
      </Typography>

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

      {!loading && !error && downloadError && (
        <Typography color="error" variant="body2" mb={1.5}>
          {downloadError}
        </Typography>
      )}

      {!loading && !error && totalCount === 0 && (
        <Typography variant="body2" color="text.secondary">
          {isSearching ? `No SecLists files match "${query}".` : "No files found."}
        </Typography>
      )}

      <Stack spacing={2.5}>
        {groups.map((group) => {
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
                <Chip label={group.total} size="small" variant="outlined" />
                {group.truncated && (
                  <Typography variant="caption" color="text.disabled">
                    showing first {group.wordlists.length} of {group.total} — search to narrow
                  </Typography>
                )}
              </Stack>
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
                  gap: 1,
                }}
              >
                {visible.map((w) => {
                  const selected = w.path === currentPath;
                  const isDownloading = downloadingPath === w.path;
                  return (
                    <Box
                      key={w.path}
                      role="button"
                      tabIndex={0}
                      onClick={() => !downloadingPath && handleSelect(w.path)}
                      onKeyDown={(e) => {
                        if ((e.key === "Enter" || e.key === " ") && !downloadingPath) handleSelect(w.path);
                      }}
                      sx={{
                        cursor: downloadingPath ? "default" : "pointer",
                        opacity: downloadingPath && !isDownloading ? 0.5 : 1,
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
                        "&:hover": { borderColor: downloadingPath ? undefined : "#22c55e" },
                      }}
                    >
                      {isDownloading ? (
                        <CircularProgress size={16} sx={{ mt: 0.5 }} />
                      ) : w.downloaded ? (
                        <CloudDoneOutlinedIcon
                          fontSize="small"
                          sx={{ color: selected ? "#22c55e" : "text.secondary", mt: 0.25 }}
                        />
                      ) : (
                        <CloudDownloadOutlinedIcon fontSize="small" sx={{ color: "text.disabled", mt: 0.25 }} />
                      )}
                      <Box minWidth={0}>
                        <Typography
                          variant="body2"
                          noWrap
                          title={w.label}
                          sx={{ fontFamily: "var(--font-geist-mono)", fontSize: 13 }}
                        >
                          {w.label.split("/").pop()}
                        </Typography>
                        <Typography variant="caption" color="text.disabled" noWrap title={w.path} display="block">
                          {w.path} · {formatSize(w.size)}
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
                  {expanded.has(group.category) ? "Show less" : `Show all ${group.wordlists.length}`}
                </Button>
              )}
            </Box>
          );
        })}
      </Stack>
    </Box>
  );
}

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
  const [tab, setTab] = useState<"local" | "remote">("local");

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="md">
      <DialogTitle>Select wordlist</DialogTitle>
      <Tabs
        value={tab}
        onChange={(_, v) => setTab(v)}
        sx={{ px: 3, minHeight: 36, borderBottom: "1px solid", borderColor: "divider" }}
      >
        <Tab value="local" label="Local" sx={{ minHeight: 36, textTransform: "none" }} />
        <Tab value="remote" label="SecLists (GitHub)" sx={{ minHeight: 36, textTransform: "none" }} />
      </Tabs>
      <DialogContent>
        {tab === "local" ? (
          <LocalWordlistsPane itemId={itemId} currentPath={currentPath} onSelect={onSelect} />
        ) : (
          <RemoteWordlistsPane itemId={itemId} currentPath={currentPath} onSelect={onSelect} />
        )}
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose}>Cancel</Button>
      </DialogActions>
    </Dialog>
  );
}
