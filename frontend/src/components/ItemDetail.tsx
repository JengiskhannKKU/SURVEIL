"use client";

import { useEffect, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";
import Link from "@mui/material/Link";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import TextField from "@mui/material/TextField";
import InputAdornment from "@mui/material/InputAdornment";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import SearchIcon from "@mui/icons-material/Search";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import OpenInFullIcon from "@mui/icons-material/OpenInFull";
import ZoomInIcon from "@mui/icons-material/ZoomIn";
import ZoomOutIcon from "@mui/icons-material/ZoomOut";
import CloseIcon from "@mui/icons-material/Close";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/Badge";
import { FindingsPanel } from "@/components/FindingsPanel";
import { EvidencePanel } from "@/components/EvidencePanel";
import { RunToolDialog } from "@/components/RunToolDialog";
import { ChecklistItemDialog } from "@/components/ChecklistItemDialog";
import { HighlightedOutput } from "@/components/HighlightedOutput";
import { DirectoryTree } from "@/components/DirectoryTree";
import { PrettyOutput } from "@/components/PrettyOutput";
import { ItemToolsHelpDialog } from "@/components/ItemToolsHelpDialog";
import {
  parseDiscoveredPaths,
  buildPathTree,
  collectStatuses,
  filterRawByStatus,
} from "@/lib/pathTree";
import { detectAndFormat } from "@/lib/prettyFormat";
import type { PrettyKind } from "@/lib/prettyFormat";
import { useToast } from "@/lib/toast";
import type { ChecklistItem, ToolInfo } from "@/lib/types";

// A plain icon-only IconButton with no border reads as inert/decorative
// next to bordered controls like the ToggleButtonGroup beside it (entry
// 38's expand/zoom/close row) — this outlines it the same way so it
// visibly reads as clickable, with the app's teal accent on hover.
const BORDERED_ICON_BUTTON_SX = {
  border: "1px solid rgba(255,255,255,0.14)",
  borderRadius: 1,
  "&:hover": { borderColor: "primary.main", bgcolor: "rgba(94,234,212,0.08)" },
  "&.Mui-disabled": { borderColor: "rgba(255,255,255,0.06)" },
};

const PRETTY_KIND_LABEL: Record<PrettyKind, string> = {
  json: "JSON",
  html: "HTML",
  xml: "XML",
  javascript: "JS",
};

export function ItemDetail({
  engagementId,
  target,
  item,
  allTools,
  categories,
  onChange,
  onDelete,
}: {
  engagementId: string;
  target: string;
  item: ChecklistItem;
  allTools: ToolInfo[];
  categories: string[];
  onChange: (item: ChecklistItem) => void;
  onDelete: () => void;
}) {
  const toast = useToast();
  const [showRun, setShowRun] = useState(false);
  const [showToolsHelp, setShowToolsHelp] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [notes, setNotes] = useState(item.notes);
  const [savingNotes, setSavingNotes] = useState(false);
  // The tester's own tab pick — kept separate from the *effective* active
  // tab below because this only updates on an explicit action (clicking a
  // tab, or a run finishing), not every time `item` changes. Without that
  // split, a background poll/update that changes `item.tool_outputs`
  // through any path other than those two (e.g. EvidencePanel's onChange
  // after an upload) left this pointing at a key that may no longer be
  // the first/only one, or — if `item.tool_outputs` was empty at mount —
  // stayed `null` even after tabs actually appeared. `null` is also not a
  // value MUI's Tabs accepts (confirmed via a real console error: "None
  // of the Tabs' children match with 'null'"), so passing it straight to
  // `value=` was doubly wrong.
  const [selectedOutput, setSelectedOutput] = useState<string | null>(
    Object.keys(item.tool_outputs)[0] ?? null
  );
  // Falls back to the first available tab whenever `selectedOutput` no
  // longer names a real one — same "derive a safe value at render time
  // instead of syncing state via an effect" idiom `effectiveOutputView`
  // below already uses.
  const activeOutput =
    selectedOutput !== null && item.tool_outputs[selectedOutput] !== undefined
      ? selectedOutput
      : (Object.keys(item.tool_outputs)[0] ?? null);
  const [busyAction, setBusyAction] = useState<"markDone" | "skip" | "reset" | null>(null);
  const [outputView, setOutputView] = useState<"raw" | "tree" | "pretty">("raw");
  const [runAtPath, setRunAtPath] = useState<string | null>(null);
  // Filters applied to the Tool output panel below — a plain substring
  // search (works against any tool's raw output) plus, when the active
  // output is ffuf/gobuster-shaped, a status-code filter (200/301/302/403/
  // ...) so a tester can isolate "what's publicly open" from "what needs
  // permission" without hand-reading the whole dump.
  const [filterQuery, setFilterQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<number | null>(null);
  // Popup for reading a result at a larger, adjustable scale — the inline
  // panel below is capped at a small maxHeight/font size so the rest of
  // the checklist item stays usable, which makes a long/dense result
  // (a big nmap scan, a huge ffuf tree) hard to actually read in place.
  const [showExpanded, setShowExpanded] = useState(false);
  const [zoom, setZoom] = useState(1);

  function selectOutputTab(name: string) {
    setSelectedOutput(name);
    // A status filter that made sense for ffuf shouldn't silently carry
    // over and hide everything in an unrelated nmap tab.
    setFilterQuery("");
    setStatusFilter(null);
  }

  const discoveredEntries = useMemo(() => {
    if (!activeOutput) return [];
    return parseDiscoveredPaths(item.tool_outputs[activeOutput] ?? "", activeOutput);
  }, [activeOutput, item.tool_outputs]);
  const hasDiscoveredPaths = discoveredEntries.length > 0;
  const availableStatuses = useMemo(() => collectStatuses(discoveredEntries), [discoveredEntries]);

  const filteredEntries = useMemo(() => {
    const q = filterQuery.trim().toLowerCase();
    return discoveredEntries.filter(
      (e) =>
        (statusFilter === null || e.status === statusFilter) &&
        (!q || e.path.toLowerCase().includes(q))
    );
  }, [discoveredEntries, filterQuery, statusFilter]);

  const discoveredTree = useMemo(
    () => (hasDiscoveredPaths ? buildPathTree(filteredEntries) : null),
    [hasDiscoveredPaths, filteredEntries]
  );

  const displayedRawOutput = useMemo(() => {
    if (!activeOutput) return "";
    let text = item.tool_outputs[activeOutput] ?? "";
    if (statusFilter !== null) text = filterRawByStatus(text, statusFilter);
    const q = filterQuery.trim().toLowerCase();
    if (q) {
      text = text
        .split("\n")
        .filter((line) => line.toLowerCase().includes(q))
        .join("\n");
    }
    return text;
  }, [activeOutput, item.tool_outputs, statusFilter, filterQuery]);
  // Detects embedded JSON/HTML in the active tab's output (e.g. a curl/wget
  // response body) and offers a reformatted, syntax-highlighted view of it.
  const prettyResult = useMemo(() => {
    if (!activeOutput) return null;
    return detectAndFormat(item.tool_outputs[activeOutput] ?? "");
  }, [activeOutput, item.tool_outputs]);
  // Falls back to raw whenever the active output has no parseable tree/JSON/
  // HTML for the currently selected view — switching tabs away from a
  // ffuf/gobuster/katana result (tree) or a curl/wget response (pretty) to
  // e.g. an nmap one shouldn't leave a stale selection rendering nothing.
  const effectiveOutputView =
    (outputView === "tree" && discoveredTree) || (outputView === "pretty" && prettyResult)
      ? outputView
      : "raw";

  // Shared between the inline panel and the expanded popup — same content,
  // just a different font size / max height so the popup can actually be
  // used for reading a large result up close.
  function renderOutputBody(fontSize: number, maxHeight: number | string) {
    if (!activeOutput) return null;
    if (effectiveOutputView === "raw") {
      return (
        <Box
          component="pre"
          sx={{
            m: 0,
            maxHeight,
            overflow: "auto",
            borderRadius: 1,
            bgcolor: "#000",
            border: "1px solid rgba(255,255,255,0.08)",
            px: 1.5,
            py: 1,
            fontFamily: "var(--font-geist-mono), monospace",
            fontSize,
            lineHeight: 1.6,
            color: "rgba(255,255,255,0.8)",
          }}
        >
          {displayedRawOutput.trim().length > 0 ? (
            <HighlightedOutput text={displayedRawOutput} />
          ) : (
            <Typography variant="body2" color="text.secondary">
              No output lines match this filter.
            </Typography>
          )}
        </Box>
      );
    }
    if (effectiveOutputView === "tree" && discoveredTree) {
      return (
        <Box
          sx={{
            borderRadius: 1,
            bgcolor: "#000",
            border: "1px solid rgba(255,255,255,0.08)",
            px: 1,
            py: 0.5,
            maxHeight,
            overflow: "auto",
            fontSize,
          }}
        >
          <DirectoryTree
            root={discoveredTree}
            onRunHere={runToolAt}
            emptyMessage={
              filterQuery || statusFilter !== null
                ? "No discovered paths match this filter."
                : undefined
            }
          />
        </Box>
      );
    }
    if (effectiveOutputView === "pretty" && prettyResult) {
      return (
        <Box
          component="pre"
          sx={{
            m: 0,
            maxHeight,
            overflow: "auto",
            borderRadius: 1,
            bgcolor: "#000",
            border: "1px solid rgba(255,255,255,0.08)",
            px: 1.5,
            py: 1,
            fontFamily: "var(--font-geist-mono), monospace",
            fontSize,
            lineHeight: 1.6,
            color: "rgba(255,255,255,0.8)",
            whiteSpace: "pre",
          }}
        >
          <PrettyOutput text={prettyResult.formatted} kind={prettyResult.kind} />
        </Box>
      );
    }
    return null;
  }

  function runToolAt(path: string) {
    setRunAtPath(path);
    setShowRun(true);
  }

  async function saveNotes() {
    if (notes === item.notes) return;
    setSavingNotes(true);
    try {
      const updated = await api.updateNotes(engagementId, item.id, notes);
      onChange(updated);
      toast.success("Notes saved");
    } catch {
      toast.error("Failed to save notes");
    } finally {
      setSavingNotes(false);
    }
  }

  async function act(action: "markDone" | "skip" | "reset") {
    setBusyAction(action);
    try {
      const updated = await api[action](engagementId, item.id);
      onChange(updated);
      const labels = { markDone: "Marked done", skip: "Skipped", reset: "Reset to pending" };
      toast.success(labels[action]);
    } catch {
      toast.error("Action failed");
    } finally {
      setBusyAction(null);
    }
  }

  async function handleDelete() {
    if (!confirm(`Delete checklist item "${item.id} — ${item.name}"? Its findings will be lost too.`))
      return;
    try {
      await api.deleteItem(engagementId, item.id);
      onDelete();
    } catch {
      toast.error("Failed to delete checklist item");
    }
  }

  const hasRunnableTools = item.tools.length > 0;
  const itemTools = useMemo(
    () => allTools.filter((t) => item.tools.includes(t.name)),
    [allTools, item.tools]
  );

  // "R" opens the Run Tool dialog for whichever item is currently
  // selected — documented in the README for a while before this was
  // actually wired up. Guarded the same way Checklist.tsx's ↑/↓
  // shortcut is: skip while focus is in a text field (including this
  // item's own Notes textarea) so typing the letter "r" anywhere never
  // gets hijacked.
  useEffect(() => {
    function handler(e: KeyboardEvent) {
      if (e.key !== "r" && e.key !== "R") return;
      const target = e.target as HTMLElement;
      if (["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)) return;
      if (!hasRunnableTools) return;
      setRunAtPath(null);
      setShowRun(true);
    }
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [hasRunnableTools]);

  return (
    <Box display="flex" flexDirection="column" flex={1} sx={{ overflow: "hidden" }}>
      <Box sx={{ borderBottom: "1px solid", borderColor: "divider", px: 3, py: 2 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start" spacing={2}>
          <Box>
            <Stack direction="row" alignItems="center" spacing={1} mb={0.5}>
              <Typography variant="h6" fontWeight={700}>
                {item.id} — {item.name}
              </Typography>
              <StatusBadge status={item.status} />
            </Stack>
            <Typography variant="body2" color="text.secondary">
              {item.category}
            </Typography>
          </Box>
          <Stack direction="row" spacing={1} flexShrink={0}>
            <Button size="small" variant="outlined" onClick={() => setShowEdit(true)}>
              Edit
            </Button>
            <Button size="small" variant="outlined" color="error" onClick={handleDelete}>
              Delete
            </Button>
          </Stack>
        </Stack>
      </Box>

      <Box flex={1} sx={{ overflowY: "auto", px: 3, py: 2.5 }}>
        <motion.div
          key={item.id}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
        >
          <Typography variant="body2" color="text.secondary" mb={2} lineHeight={1.7}>
            {item.description}
          </Typography>

          {item.references.length > 0 && (
            <Link
              href={item.references[0]}
              target="_blank"
              rel="noreferrer"
              variant="caption"
              underline="hover"
              sx={{ display: "block", mb: 2.5 }}
            >
              OWASP WSTG reference ↗
            </Link>
          )}

          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap mb={3}>
            {hasRunnableTools && item.status !== "running" && (
              <Button
                variant="contained"
                onClick={() => {
                  setRunAtPath(null);
                  setShowRun(true);
                }}
                endIcon={
                  <Box
                    component="kbd"
                    title="Keyboard shortcut: R"
                    sx={{
                      fontFamily: "var(--font-geist-mono)",
                      fontSize: 10,
                      lineHeight: 1,
                      border: "1px solid rgba(0,0,0,0.35)",
                      borderRadius: 0.5,
                      px: 0.5,
                      py: 0.25,
                      opacity: 0.7,
                    }}
                  >
                    R
                  </Box>
                }
              >
                Run tool
              </Button>
            )}
            {hasRunnableTools && item.status === "running" && (
              <Button
                variant="contained"
                onClick={() => {
                  setRunAtPath(null);
                  setShowRun(true);
                }}
                sx={{
                  bgcolor: "#f59e0b",
                  color: "#000",
                  "&:hover": { bgcolor: "#d97706" },
                }}
                startIcon={
                  <motion.div
                    animate={{ opacity: [1, 0.3, 1] }}
                    transition={{ duration: 1.1, repeat: Infinity }}
                    style={{ width: 7, height: 7, borderRadius: "50%", backgroundColor: "#000" }}
                  />
                }
              >
                Running in background…
              </Button>
            )}
            {hasRunnableTools && (
              <Button
                variant="outlined"
                startIcon={<HelpOutlineIcon fontSize="small" />}
                onClick={() => setShowToolsHelp(true)}
                title="What each tool for this test does, and its full command-line options"
              >
                Help
              </Button>
            )}
            <Button
              variant="outlined"
              onClick={() => act("markDone")}
              disabled={busyAction !== null}
            >
              {busyAction === "markDone" ? "Marking…" : "Mark done"}
            </Button>
            <Button variant="outlined" onClick={() => act("skip")} disabled={busyAction !== null}>
              {busyAction === "skip" ? "Skipping…" : "Skip"}
            </Button>
            <Button variant="outlined" onClick={() => act("reset")} disabled={busyAction !== null}>
              {busyAction === "reset" ? "Resetting…" : "Reset"}
            </Button>
          </Stack>

          {Object.keys(item.tool_outputs).length > 0 && (
            <Box mb={3}>
              <Stack direction="row" alignItems="center" justifyContent="space-between" mb={1}>
                <Typography variant="subtitle2" fontWeight={700}>
                  Tool output
                </Typography>
                <Stack direction="row" spacing={1} alignItems="center">
                  <ToggleButtonGroup
                    size="small"
                    exclusive
                    value={outputView}
                    onChange={(_, v) => v && setOutputView(v)}
                    sx={{ "& .MuiToggleButton-root": { px: 1.25, py: 0.25, fontSize: 11, textTransform: "none" } }}
                  >
                    <ToggleButton value="raw">Raw</ToggleButton>
                    {discoveredTree && <ToggleButton value="tree">Tree</ToggleButton>}
                    {prettyResult && (
                      <ToggleButton value="pretty">
                        Pretty {PRETTY_KIND_LABEL[prettyResult.kind]}
                      </ToggleButton>
                    )}
                  </ToggleButtonGroup>
                  <Tooltip title="Expand to a larger, zoomable view">
                    <IconButton size="medium" onClick={() => setShowExpanded(true)} sx={BORDERED_ICON_BUTTON_SX}>
                      <OpenInFullIcon sx={{ fontSize: 15 }} />
                    </IconButton>
                  </Tooltip>
                </Stack>
              </Stack>
              <Tabs
                value={activeOutput ?? false}
                onChange={(_, v) => selectOutputTab(v)}
                variant="scrollable"
                sx={{ minHeight: 32, mb: 1, "& .MuiTab-root": { minHeight: 32, py: 0.5 } }}
              >
                {Object.keys(item.tool_outputs).map((t) => (
                  <Tab key={t} value={t} label={t} sx={{ fontSize: 12 }} />
                ))}
              </Tabs>

              <Stack direction="row" alignItems="center" spacing={1} flexWrap="wrap" useFlexGap mb={1}>
                <TextField
                  size="small"
                  placeholder="Filter output…"
                  value={filterQuery}
                  onChange={(e) => setFilterQuery(e.target.value)}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <SearchIcon fontSize="small" sx={{ color: "text.secondary" }} />
                      </InputAdornment>
                    ),
                    sx: { fontSize: 12.5 },
                  }}
                  sx={{ width: 220 }}
                />
                {availableStatuses.length > 0 && (
                  <ToggleButtonGroup
                    size="small"
                    exclusive
                    value={statusFilter === null ? "all" : statusFilter}
                    onChange={(_, v) => setStatusFilter(v === "all" || v === null ? null : v)}
                    sx={{ "& .MuiToggleButton-root": { px: 1, py: 0.25, fontSize: 11, textTransform: "none" } }}
                  >
                    <ToggleButton value="all">All</ToggleButton>
                    {availableStatuses.map((s) => (
                      <ToggleButton
                        key={s}
                        value={s}
                        sx={{
                          color:
                            s === 200 ? "#22c55e" : s === 401 || s === 403 ? "#f59e0b" : undefined,
                        }}
                      >
                        {s}
                      </ToggleButton>
                    ))}
                  </ToggleButtonGroup>
                )}
              </Stack>

              {renderOutputBody(12, effectiveOutputView === "pretty" ? 480 : 320)}
            </Box>
          )}

          <Box mb={3}>
            <FindingsPanel engagementId={engagementId} item={item} onChange={onChange} />
          </Box>

          <Box mb={3}>
            <EvidencePanel engagementId={engagementId} item={item} onChange={onChange} />
          </Box>

          <Box mb={2}>
            <Typography variant="subtitle2" fontWeight={700} mb={1}>
              Notes
            </Typography>
            <Box
              component="textarea"
              value={notes}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setNotes(e.target.value)}
              onBlur={saveNotes}
              rows={3}
              placeholder="Tester notes…"
              sx={{
                width: "100%",
                borderRadius: 1,
                border: "1px solid",
                borderColor: "divider",
                bgcolor: "rgba(255,255,255,0.02)",
                color: "text.primary",
                fontFamily: "inherit",
                fontSize: 14,
                p: 1.25,
                resize: "vertical",
                "&:focus": { outline: "none", borderColor: "primary.main" },
              }}
            />
            {savingNotes && (
              <Typography variant="caption" color="text.secondary">
                Saving…
              </Typography>
            )}
          </Box>
        </motion.div>
      </Box>

      {showRun && (
        <RunToolDialog
          engagementId={engagementId}
          target={runAtPath ? `${target}${runAtPath}` : target}
          item={item}
          allTools={allTools}
          onClose={() => {
            setShowRun(false);
            setRunAtPath(null);
          }}
          onDone={(updated) => {
            onChange(updated);
            setSelectedOutput(Object.keys(updated.tool_outputs).slice(-1)[0] ?? null);
          }}
          onStart={() => {
            if (item.status !== "running") onChange({ ...item, status: "running" });
          }}
        />
      )}

      {showExpanded && (
        <Dialog
          open
          onClose={() => setShowExpanded(false)}
          fullWidth
          maxWidth="lg"
          slotProps={{ paper: { sx: { height: "85vh" } } }}
        >
          <Stack
            direction="row"
            alignItems="center"
            justifyContent="space-between"
            sx={{ px: 2.5, py: 1.5, borderBottom: "1px solid", borderColor: "divider" }}
          >
            <Typography variant="subtitle1" fontWeight={700}>
              {activeOutput} output
            </Typography>
            <Stack direction="row" spacing={0.5} alignItems="center">
              <Tooltip title="Zoom out">
                <span>
                  <IconButton
                    size="small"
                    disabled={zoom <= 0.75}
                    onClick={() => setZoom((z) => Math.max(0.75, +(z - 0.25).toFixed(2)))}
                    sx={BORDERED_ICON_BUTTON_SX}
                  >
                    <ZoomOutIcon fontSize="small" />
                  </IconButton>
                </span>
              </Tooltip>
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ minWidth: 38, textAlign: "center", fontFamily: "var(--font-geist-mono)" }}
              >
                {Math.round(zoom * 100)}%
              </Typography>
              <Tooltip title="Zoom in">
                <span>
                  <IconButton
                    size="small"
                    disabled={zoom >= 2.5}
                    onClick={() => setZoom((z) => Math.min(2.5, +(z + 0.25).toFixed(2)))}
                    sx={BORDERED_ICON_BUTTON_SX}
                  >
                    <ZoomInIcon fontSize="small" />
                  </IconButton>
                </span>
              </Tooltip>
              <IconButton
                size="small"
                onClick={() => setShowExpanded(false)}
                sx={{ ...BORDERED_ICON_BUTTON_SX, ml: 1 }}
              >
                <CloseIcon fontSize="small" />
              </IconButton>
            </Stack>
          </Stack>
          <DialogContent sx={{ display: "flex", flexDirection: "column", overflow: "hidden", p: 2.5 }}>
            <Stack direction="row" alignItems="center" spacing={1} flexWrap="wrap" useFlexGap mb={1.5}>
              <TextField
                size="small"
                placeholder="Filter output…"
                value={filterQuery}
                onChange={(e) => setFilterQuery(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon fontSize="small" sx={{ color: "text.secondary" }} />
                    </InputAdornment>
                  ),
                  sx: { fontSize: 12.5 },
                }}
                sx={{ width: 220 }}
              />
              {availableStatuses.length > 0 && (
                <ToggleButtonGroup
                  size="small"
                  exclusive
                  value={statusFilter === null ? "all" : statusFilter}
                  onChange={(_, v) => setStatusFilter(v === "all" || v === null ? null : v)}
                  sx={{ "& .MuiToggleButton-root": { px: 1, py: 0.25, fontSize: 11, textTransform: "none" } }}
                >
                  <ToggleButton value="all">All</ToggleButton>
                  {availableStatuses.map((s) => (
                    <ToggleButton
                      key={s}
                      value={s}
                      sx={{
                        color: s === 200 ? "#22c55e" : s === 401 || s === 403 ? "#f59e0b" : undefined,
                      }}
                    >
                      {s}
                    </ToggleButton>
                  ))}
                </ToggleButtonGroup>
              )}
            </Stack>
            <Box flex={1} sx={{ overflow: "hidden" }}>
              {renderOutputBody(12 * zoom, "100%")}
            </Box>
          </DialogContent>
        </Dialog>
      )}

      {showToolsHelp && (
        <ItemToolsHelpDialog tools={itemTools} onClose={() => setShowToolsHelp(false)} />
      )}

      {showEdit && (
        <ChecklistItemDialog
          mode="edit"
          item={item}
          categories={categories}
          allTools={allTools}
          onClose={() => setShowEdit(false)}
          onSubmit={async (values) => {
            try {
              const updated = await api.updateItem(engagementId, item.id, values);
              onChange(updated);
              toast.success("Checklist item updated");
              setShowEdit(false);
            } catch {
              toast.error("Failed to update checklist item");
            }
          }}
        />
      )}
    </Box>
  );
}
