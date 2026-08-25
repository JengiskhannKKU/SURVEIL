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
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/Badge";
import { FindingsPanel } from "@/components/FindingsPanel";
import { RunToolDialog } from "@/components/RunToolDialog";
import { ChecklistItemDialog } from "@/components/ChecklistItemDialog";
import { HighlightedOutput } from "@/components/HighlightedOutput";
import { DirectoryTree } from "@/components/DirectoryTree";
import { ItemToolsHelpDialog } from "@/components/ItemToolsHelpDialog";
import { parseDiscoveredPaths, buildPathTree } from "@/lib/pathTree";
import { useToast } from "@/lib/toast";
import type { ChecklistItem, ToolInfo } from "@/lib/types";

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
  const [activeOutput, setActiveOutput] = useState<string | null>(
    Object.keys(item.tool_outputs)[0] ?? null
  );
  const [busyAction, setBusyAction] = useState<"markDone" | "skip" | "reset" | null>(null);
  const [outputView, setOutputView] = useState<"raw" | "tree">("raw");
  const [runAtPath, setRunAtPath] = useState<string | null>(null);

  const discoveredTree = useMemo(() => {
    if (!activeOutput) return null;
    const paths = parseDiscoveredPaths(item.tool_outputs[activeOutput] ?? "", activeOutput);
    return paths.length > 0 ? buildPathTree(paths) : null;
  }, [activeOutput, item.tool_outputs]);
  // Falls back to raw whenever the active output has no parseable tree —
  // switching tabs away from a ffuf/gobuster/katana result to e.g. an nmap
  // one shouldn't leave a stale "tree" selection rendering nothing.
  const effectiveOutputView = discoveredTree ? outputView : "raw";

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
            {hasRunnableTools && (
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
                {discoveredTree && (
                  <ToggleButtonGroup
                    size="small"
                    exclusive
                    value={outputView}
                    onChange={(_, v) => v && setOutputView(v)}
                    sx={{ "& .MuiToggleButton-root": { px: 1.25, py: 0.25, fontSize: 11, textTransform: "none" } }}
                  >
                    <ToggleButton value="raw">Raw</ToggleButton>
                    <ToggleButton value="tree">Tree</ToggleButton>
                  </ToggleButtonGroup>
                )}
              </Stack>
              <Tabs
                value={activeOutput}
                onChange={(_, v) => setActiveOutput(v)}
                variant="scrollable"
                sx={{ minHeight: 32, mb: 1, "& .MuiTab-root": { minHeight: 32, py: 0.5 } }}
              >
                {Object.keys(item.tool_outputs).map((t) => (
                  <Tab key={t} value={t} label={t} sx={{ fontSize: 12 }} />
                ))}
              </Tabs>
              {activeOutput && effectiveOutputView === "raw" && (
                <Box
                  component="pre"
                  sx={{
                    m: 0,
                    maxHeight: 320,
                    overflow: "auto",
                    borderRadius: 1,
                    bgcolor: "#000",
                    border: "1px solid rgba(255,255,255,0.08)",
                    px: 1.5,
                    py: 1,
                    fontFamily: "var(--font-geist-mono), monospace",
                    fontSize: 12,
                    lineHeight: 1.6,
                    color: "rgba(255,255,255,0.8)",
                  }}
                >
                  <HighlightedOutput text={item.tool_outputs[activeOutput]} />
                </Box>
              )}
              {activeOutput && effectiveOutputView === "tree" && discoveredTree && (
                <Box
                  sx={{
                    borderRadius: 1,
                    bgcolor: "#000",
                    border: "1px solid rgba(255,255,255,0.08)",
                    px: 1,
                    py: 0.5,
                  }}
                >
                  <DirectoryTree root={discoveredTree} onRunHere={runToolAt} />
                </Box>
              )}
            </Box>
          )}

          <Box mb={3}>
            <FindingsPanel engagementId={engagementId} item={item} onChange={onChange} />
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
            setActiveOutput(Object.keys(updated.tool_outputs).slice(-1)[0] ?? null);
          }}
        />
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
