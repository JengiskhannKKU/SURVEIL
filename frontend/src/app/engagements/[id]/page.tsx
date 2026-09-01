"use client";

import { use, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import Skeleton from "@mui/material/Skeleton";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import ArticleOutlinedIcon from "@mui/icons-material/ArticleOutlined";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import AccountTreeOutlinedIcon from "@mui/icons-material/AccountTreeOutlined";
import SettingsEthernetIcon from "@mui/icons-material/SettingsEthernet";
import { api } from "@/lib/api";
import { Checklist } from "@/components/Checklist";
import { ItemDetail } from "@/components/ItemDetail";
import { ReportView } from "@/components/ReportView";
import { ProgressBar, SeverityBar } from "@/components/SeverityBar";
import { PathsDialog } from "@/components/PathsDialog";
import { PortsDialog } from "@/components/PortsDialog";
import { useToast } from "@/lib/toast";
import { severityCounts } from "@/lib/severity";
import { collectEngagementPaths } from "@/lib/engagementPaths";
import { collectEngagementPorts } from "@/lib/engagementPorts";
import type { ChecklistItem, Engagement, ToolInfo } from "@/lib/types";

function HeaderSkeleton() {
  return (
    <Box sx={{ borderBottom: "1px solid", borderColor: "divider", px: 3, py: 2 }}>
      <Skeleton variant="text" width={100} height={16} sx={{ mb: 1 }} />
      <Skeleton variant="text" width={220} height={28} sx={{ mb: 1 }} />
      <Skeleton variant="text" width={280} height={16} />
    </Box>
  );
}

export default function EngagementPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const toast = useToast();
  const [engagement, setEngagement] = useState<Engagement | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [tools, setTools] = useState<ToolInfo[]>([]);
  const [error, setError] = useState("");
  const [showReport, setShowReport] = useState(false);
  const [showPaths, setShowPaths] = useState(false);
  const [showPorts, setShowPorts] = useState(false);

  useEffect(() => {
    api
      .getEngagement(id)
      .then((eng) => {
        setEngagement(eng);
        setSelectedId(eng.checklist_items[0]?.id ?? null);
      })
      .catch(() => setError("Engagement not found."));
    api
      .listTools()
      .then(setTools)
      .catch(() => toast.error("Could not reach the backend to load the tool list."));
  }, [id, toast]);

  const updateItem = useCallback((updated: ChecklistItem) => {
    setEngagement((prev) =>
      prev
        ? {
            ...prev,
            checklist_items: prev.checklist_items.map((it) =>
              it.id === updated.id ? updated : it
            ),
          }
        : prev
    );
  }, []);

  const addItem = useCallback((created: ChecklistItem) => {
    setEngagement((prev) =>
      prev ? { ...prev, checklist_items: [...prev.checklist_items, created] } : prev
    );
    setSelectedId(created.id);
  }, []);

  const removeItem = useCallback((itemId: string) => {
    setEngagement((prev) => {
      if (!prev) return prev;
      const remaining = prev.checklist_items.filter((i) => i.id !== itemId);
      setSelectedId((current) => (current === itemId ? (remaining[0]?.id ?? null) : current));
      return { ...prev, checklist_items: remaining };
    });
  }, []);

  const jumpToNextPending = useCallback(() => {
    setEngagement((prev) => {
      if (!prev) return prev;
      const next = prev.checklist_items.find((i) => i.status === "pending");
      if (next) setSelectedId(next.id);
      return prev;
    });
  }, []);

  useEffect(() => {
    function handler(e: KeyboardEvent) {
      const target = e.target as HTMLElement;
      if (["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)) return;
      if (e.key === "n" || e.key === "N") jumpToNextPending();
    }
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [jumpToNextPending]);

  // A tool that's still running keeps executing server-side even after this
  // page (or the Run Tool dialog) is closed/navigated away from — poll while
  // anything is running so the checklist sidebar's status flips from
  // "running" to "done" on its own once it finishes, instead of only ever
  // updating when a Run Tool dialog happens to be open to receive it live.
  const anyRunning = useMemo(
    () => engagement?.checklist_items.some((i) => i.status === "running") ?? false,
    [engagement]
  );

  useEffect(() => {
    if (!anyRunning) return;
    const interval = setInterval(() => {
      api.getEngagement(id).then(setEngagement).catch(() => {});
    }, 3000);
    return () => clearInterval(interval);
  }, [anyRunning, id]);

  const sev = useMemo(
    () => severityCounts(engagement?.checklist_items.flatMap((i) => i.findings) ?? []),
    [engagement]
  );
  const done = useMemo(
    () =>
      engagement?.checklist_items.filter((i) => ["done", "skipped"].includes(i.status)).length ?? 0,
    [engagement]
  );
  const runningCount = useMemo(
    () => engagement?.checklist_items.filter((i) => i.status === "running").length ?? 0,
    [engagement]
  );
  const categories = useMemo(
    () => [...new Set(engagement?.checklist_items.map((i) => i.category) ?? [])],
    [engagement]
  );
  const selected = engagement?.checklist_items.find((i) => i.id === selectedId) ?? null;

  // Discovered paths/endpoints, aggregated across every checklist item's
  // tool output (ffuf/gobuster/katana) for this whole engagement — backs
  // the "Paths" summary button below. Recomputes from `engagement` on
  // every change, which already happens live: the 3s polling loop above
  // while a tool is running (and RunToolDialog's onDone/onStart callbacks
  // the rest of the time) keep `engagement` current, so this and the
  // notification effect below just ride that existing real-time plumbing
  // rather than adding a second one.
  const pathEntries = useMemo(
    () =>
      engagement
        ? collectEngagementPaths(
            engagement.checklist_items,
            engagement.manual_paths,
            engagement.removed_paths
          )
        : [],
    [engagement]
  );

  // Same idea, for open ports (nmap's table, naabu's bare "host:port"
  // lines) — backs the "Ports" summary button below.
  const portEntries = useMemo(
    () =>
      engagement
        ? collectEngagementPorts(
            engagement.checklist_items,
            engagement.manual_ports,
            engagement.removed_ports
          )
        : [],
    [engagement]
  );

  async function handleAddPath(path: string, status: number | null, note: string) {
    if (!engagement) return;
    try {
      const updated = await api.addManualPath(engagement.id, path, status, note);
      setEngagement(updated);
      toast.success(`Added ${path.startsWith("/") ? path : `/${path}`}`);
    } catch {
      toast.error("Failed to add path");
      throw new Error("add path failed");
    }
  }

  function handleRemovePath(path: string) {
    if (!engagement) return;
    api
      .removePath(engagement.id, path)
      // Once hidden, `removed_paths` on the returned engagement makes
      // `collectEngagementPaths()` exclude this path entirely — so it
      // simply won't be in `pathEntries` on the next recompute, and the
      // notification effect below never sees it to re-toast as "new".
      .then((updated) => {
        setEngagement(updated);
        toast.success(`Removed ${path}`);
      })
      .catch(() => toast.error("Failed to remove path"));
  }

  function handleRestorePath(path: string) {
    if (!engagement) return;
    api
      .restorePath(engagement.id, path)
      .then((updated) => {
        setEngagement(updated);
        toast.success(`Restored ${path}`);
      })
      .catch(() => toast.error("Failed to restore path"));
  }

  async function handleAddPort(port: number, protocol: string, service: string, note: string) {
    if (!engagement) return;
    try {
      const updated = await api.addManualPort(engagement.id, port, protocol, service, note);
      setEngagement(updated);
      toast.success(`Added ${port}/${protocol}`);
    } catch {
      toast.error("Failed to add port");
      throw new Error("add port failed");
    }
  }

  function handleRemovePort(port: number, protocol: string) {
    if (!engagement) return;
    api
      .removePort(engagement.id, port, protocol)
      .then((updated) => {
        setEngagement(updated);
        toast.success(`Removed ${port}/${protocol}`);
      })
      .catch(() => toast.error("Failed to remove port"));
  }

  function handleRestorePort(key: string) {
    if (!engagement) return;
    const [portStr, protocol] = key.split("/");
    api
      .restorePort(engagement.id, Number(portStr), protocol)
      .then((updated) => {
        setEngagement(updated);
        toast.success(`Restored ${key}`);
      })
      .catch(() => toast.error("Failed to restore port"));
  }

  // Toasts when a run turns up paths this session hasn't seen yet. `null`
  // means "not yet initialized" — the very first computation (on initial
  // load, or after switching engagements) seeds the known set silently so
  // opening a page with 40 pre-existing paths doesn't toast 40 times.
  const knownPathsRef = useRef<Set<string> | null>(null);
  useEffect(() => {
    knownPathsRef.current = null;
  }, [id]);
  useEffect(() => {
    const current = new Set(pathEntries.map((e) => e.path));
    if (knownPathsRef.current === null) {
      knownPathsRef.current = current;
      return;
    }
    const newly = pathEntries.filter((e) => !knownPathsRef.current!.has(e.path));
    if (newly.length > 0) {
      const tools = [...new Set(newly.map((e) => e.tool))].join(", ");
      toast.info(
        `${newly.length} new path${newly.length === 1 ? "" : "s"} discovered (${tools})`
      );
    }
    knownPathsRef.current = current;
  }, [pathEntries, toast]);

  // Same notification pattern, for newly discovered open ports.
  const knownPortsRef = useRef<Set<string> | null>(null);
  useEffect(() => {
    knownPortsRef.current = null;
  }, [id]);
  useEffect(() => {
    const current = new Set(portEntries.map((e) => `${e.port}/${e.protocol}`));
    if (knownPortsRef.current === null) {
      knownPortsRef.current = current;
      return;
    }
    const newly = portEntries.filter((e) => !knownPortsRef.current!.has(`${e.port}/${e.protocol}`));
    if (newly.length > 0) {
      const tools = [...new Set(newly.map((e) => e.tool))].join(", ");
      toast.info(
        `${newly.length} new port${newly.length === 1 ? "" : "s"} discovered (${tools})`
      );
    }
    knownPortsRef.current = current;
  }, [portEntries, toast]);

  if (error) {
    return (
      <Box p={4}>
        <Typography color="error" mb={1}>
          {error}
        </Typography>
        <Button component={Link} href="/engagements" startIcon={<ArrowBackIcon />} size="small">
          Back to engagements
        </Button>
      </Box>
    );
  }

  if (!engagement) {
    return (
      <Box display="flex" flexDirection="column" flex={1}>
        <HeaderSkeleton />
        <Box flex={1} display="flex" alignItems="center" justifyContent="center">
          <Typography color="text.secondary">Loading engagement…</Typography>
        </Box>
      </Box>
    );
  }

  return (
    <Box display="flex" flexDirection="column" flex={1} height="100%">
      <Box sx={{ borderBottom: "1px solid", borderColor: "divider", px: 3, py: 2 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start" flexWrap="wrap" gap={2}>
          <Box>
            <Typography
              component={Link}
              href="/engagements"
              variant="caption"
              sx={{ color: "text.secondary", textDecoration: "none", "&:hover": { color: "text.primary" } }}
            >
              ← All engagements
            </Typography>
            <Typography variant="h6" fontWeight={700}>
              {engagement.name}
            </Typography>
            <Typography variant="caption" color="text.secondary" display="block" mb={1}>
              {engagement.target}
            </Typography>
            <Stack direction="row" spacing={3} flexWrap="wrap" useFlexGap alignItems="center">
              <ProgressBar done={done} total={engagement.checklist_items.length} />
              <SeverityBar counts={sev} />
              {runningCount > 0 && (
                <Stack direction="row" spacing={0.75} alignItems="center">
                  <motion.div
                    animate={{ opacity: [1, 0.3, 1] }}
                    transition={{ duration: 1.2, repeat: Infinity }}
                    style={{ width: 7, height: 7, borderRadius: "50%", backgroundColor: "#f59e0b" }}
                  />
                  <Typography variant="caption" sx={{ color: "#f59e0b", fontWeight: 600 }}>
                    {runningCount} running in background
                  </Typography>
                </Stack>
              )}
            </Stack>
          </Box>
          <Stack direction="row" spacing={1}>
            <Button
              variant="outlined"
              size="small"
              startIcon={<AccountTreeOutlinedIcon />}
              onClick={() => setShowPaths(true)}
            >
              Paths{pathEntries.length > 0 ? ` (${pathEntries.length})` : ""}
            </Button>
            <Button
              variant="outlined"
              size="small"
              startIcon={<SettingsEthernetIcon />}
              onClick={() => setShowPorts(true)}
            >
              Ports{portEntries.length > 0 ? ` (${portEntries.length})` : ""}
            </Button>
            <Button
              variant="contained"
              size="small"
              startIcon={<VisibilityOutlinedIcon />}
              onClick={() => setShowReport(true)}
            >
              View Report
            </Button>
            <Button
              variant="outlined"
              size="small"
              startIcon={<ArticleOutlinedIcon />}
              href={api.reportUrl(engagement.id, "md")}
            >
              Markdown
            </Button>
            <Button
              variant="outlined"
              size="small"
              startIcon={<DescriptionOutlinedIcon />}
              href={api.reportUrl(engagement.id, "docx")}
            >
              Word
            </Button>
          </Stack>
        </Stack>
      </Box>

      <Box display="flex" flex={1} sx={{ overflow: "hidden" }}>
        <Box
          sx={{
            width: 288,
            flexShrink: 0,
            display: "flex",
            flexDirection: "column",
            borderRight: "1px solid",
            borderColor: "divider",
            px: 1.5,
            py: 2,
          }}
        >
          <Checklist
            engagementId={engagement.id}
            items={engagement.checklist_items}
            selectedId={selectedId}
            onSelect={setSelectedId}
            categories={categories}
            allTools={tools}
            onCreate={addItem}
          />
        </Box>

        {selected ? (
          <ItemDetail
            key={selected.id}
            engagementId={engagement.id}
            target={engagement.target}
            item={selected}
            allTools={tools}
            categories={categories}
            onChange={updateItem}
            onDelete={() => {
              removeItem(selected.id);
              toast.success(`Deleted ${selected.id}`);
            }}
          />
        ) : (
          <Box flex={1} p={4}>
            <Typography color="text.secondary">
              {engagement.checklist_items.length === 0
                ? "No checklist items yet — add one from the sidebar."
                : "Select a checklist item."}
            </Typography>
          </Box>
        )}
      </Box>

      {showReport && (
        <ReportView engagementId={engagement.id} onClose={() => setShowReport(false)} />
      )}

      {showPaths && (
        <PathsDialog
          entries={pathEntries}
          removedPaths={engagement.removed_paths}
          onAdd={handleAddPath}
          onRemove={handleRemovePath}
          onRestore={handleRestorePath}
          onClose={() => setShowPaths(false)}
        />
      )}

      {showPorts && (
        <PortsDialog
          entries={portEntries}
          removedPorts={engagement.removed_ports}
          onAdd={handleAddPort}
          onRemove={handleRemovePort}
          onRestore={handleRestorePort}
          onClose={() => setShowPorts(false)}
        />
      )}
    </Box>
  );
}
