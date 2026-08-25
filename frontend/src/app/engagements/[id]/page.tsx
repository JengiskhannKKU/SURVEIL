"use client";

import { use, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import Skeleton from "@mui/material/Skeleton";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import ArticleOutlinedIcon from "@mui/icons-material/ArticleOutlined";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { api } from "@/lib/api";
import { Checklist } from "@/components/Checklist";
import { ItemDetail } from "@/components/ItemDetail";
import { ReportView } from "@/components/ReportView";
import { ProgressBar, SeverityBar } from "@/components/SeverityBar";
import { useToast } from "@/lib/toast";
import { severityCounts } from "@/lib/severity";
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

  const sev = useMemo(
    () => severityCounts(engagement?.checklist_items.flatMap((i) => i.findings) ?? []),
    [engagement]
  );
  const done = useMemo(
    () =>
      engagement?.checklist_items.filter((i) => ["done", "skipped"].includes(i.status)).length ?? 0,
    [engagement]
  );
  const categories = useMemo(
    () => [...new Set(engagement?.checklist_items.map((i) => i.category) ?? [])],
    [engagement]
  );
  const selected = engagement?.checklist_items.find((i) => i.id === selectedId) ?? null;

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
            <Stack direction="row" spacing={3} flexWrap="wrap" useFlexGap>
              <ProgressBar done={done} total={engagement.checklist_items.length} />
              <SeverityBar counts={sev} />
            </Stack>
          </Box>
          <Stack direction="row" spacing={1}>
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
    </Box>
  );
}
