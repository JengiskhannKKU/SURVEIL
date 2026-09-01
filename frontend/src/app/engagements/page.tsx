"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import Paper from "@mui/material/Paper";
import Chip from "@mui/material/Chip";
import Skeleton from "@mui/material/Skeleton";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import Stack from "@mui/material/Stack";
import AddIcon from "@mui/icons-material/Add";
import SearchIcon from "@mui/icons-material/Search";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import InputAdornment from "@mui/material/InputAdornment";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import { api } from "@/lib/api";
import { useToast } from "@/lib/toast";
import { ProgressBar } from "@/components/SeverityBar";
import { ENGAGEMENT_ICONS, DEFAULT_ENGAGEMENT_ICON, engagementIcon } from "@/lib/engagementIcons";
import { METHODOLOGIES, DEFAULT_METHODOLOGY, methodologyLabel } from "@/lib/methodologies";
import type { EngagementSummary } from "@/lib/types";

function StatCard({ label, value, color, delay }: { label: string; value: string | number; color?: string; delay: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay }}
      style={{ flex: 1, minWidth: 130 }}
    >
      <Paper sx={{ px: 2.5, py: 2 }}>
        <Typography variant="h4" fontWeight={700} sx={{ color: color ?? "text.primary" }}>
          {value}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {label}
        </Typography>
      </Paper>
    </motion.div>
  );
}

function IconPicker({
  value,
  onChange,
}: {
  value: string;
  onChange: (key: string) => void;
}) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 0.75 }}>
        Icon
      </Typography>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        {Object.entries(ENGAGEMENT_ICONS).map(([key, meta]) => {
          const selected = key === value;
          const { Icon } = meta;
          return (
            <Tooltip key={key} title={meta.label}>
              <IconButton
                onClick={() => onChange(key)}
                sx={{
                  width: 40,
                  height: 40,
                  border: "1px solid",
                  borderColor: selected ? meta.color : "divider",
                  bgcolor: selected ? `${meta.color}22` : "transparent",
                  color: meta.color,
                }}
              >
                <Icon fontSize="small" />
              </IconButton>
            </Tooltip>
          );
        })}
      </Stack>
    </Box>
  );
}

function MethodologyPicker({
  value,
  onChange,
}: {
  value: string;
  onChange: (key: string) => void;
}) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 0.75 }}>
        Testing strategy / methodology
      </Typography>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap mb={0.75}>
        {Object.entries(METHODOLOGIES).map(([key, meta]) => {
          const selected = key === value;
          return (
            <Box
              key={key}
              role="button"
              tabIndex={0}
              onClick={() => onChange(key)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") onChange(key);
              }}
              sx={{
                cursor: "pointer",
                border: "1px solid",
                borderColor: selected ? "primary.main" : "divider",
                bgcolor: selected ? "rgba(94,234,212,0.1)" : "transparent",
                borderRadius: 1,
                px: 1.5,
                py: 0.75,
                "&:hover": { borderColor: "primary.main" },
              }}
            >
              <Typography variant="body2" fontWeight={selected ? 700 : 400}>
                {meta.label}
              </Typography>
            </Box>
          );
        })}
      </Stack>
      <Typography variant="caption" color="text.secondary">
        {METHODOLOGIES[value]?.description}
      </Typography>
    </Box>
  );
}

function EngagementCard({
  engagement,
  onDelete,
  delay,
}: {
  engagement: EngagementSummary;
  onDelete: () => void;
  delay: number;
}) {
  const [done, total] = engagement.progress.split("/").map(Number);
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, delay }}
      style={{ height: "100%" }}
    >
      <Paper
        component={Link}
        href={`/engagements/${engagement.id}`}
        sx={{
          display: "flex",
          flexDirection: "column",
          height: "100%",
          p: 2.5,
          textDecoration: "none",
          color: "inherit",
          transition: "border-color 0.15s, box-shadow 0.15s, transform 0.15s",
          "&:hover": {
            borderColor: "primary.main",
            boxShadow: "0 0 0 1px rgba(94,234,212,0.35), 0 0 20px rgba(94,234,212,0.13)",
            transform: "translateY(-2px)",
          },
        }}
      >
        <Stack direction="row" justifyContent="space-between" alignItems="flex-start" mb={1.5} spacing={1}>
          <Stack direction="row" spacing={1.25} alignItems="center" minWidth={0}>
            {(() => {
              const { Icon, color, label } = engagementIcon(engagement.icon);
              return (
                <Tooltip title={label}>
                  <Box
                    sx={{
                      width: 34,
                      height: 34,
                      borderRadius: 1,
                      flexShrink: 0,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      bgcolor: `${color}1a`,
                      color,
                    }}
                  >
                    <Icon fontSize="small" />
                  </Box>
                </Tooltip>
              );
            })()}
            <Box minWidth={0}>
              <Stack direction="row" alignItems="center" spacing={0.75}>
                <Typography variant="subtitle1" fontWeight={700} noWrap>
                  {engagement.name}
                </Typography>
                <Chip
                  label={methodologyLabel(engagement.methodology)}
                  size="small"
                  variant="outlined"
                  sx={{ height: 18, fontSize: 10, flexShrink: 0 }}
                />
              </Stack>
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ fontFamily: "var(--font-geist-mono)" }}
              >
                {engagement.id}
              </Typography>
            </Box>
          </Stack>
          <IconButton
            size="small"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onDelete();
            }}
            sx={{ color: "text.secondary", flexShrink: 0, "&:hover": { color: "#ef4444" } }}
          >
            <DeleteOutlineIcon fontSize="small" />
          </IconButton>
        </Stack>

        <Typography
          variant="body2"
          color="text.secondary"
          noWrap
          mb={2}
          sx={{ fontFamily: "var(--font-geist-mono)" }}
        >
          {engagement.target}
        </Typography>

        <Box mb={2} mt="auto">
          <ProgressBar done={done || 0} total={total || 0} />
        </Box>

        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Stack direction="row" spacing={0.75} alignItems="center" flexWrap="wrap" useFlexGap>
            <Typography variant="body2">
              {engagement.findings} finding{engagement.findings === 1 ? "" : "s"}
            </Typography>
            {engagement.critical > 0 && (
              <Chip
                size="small"
                label={`${engagement.critical} crit`}
                sx={{ bgcolor: "#dc2626", color: "#fff", height: 20, fontSize: 11 }}
              />
            )}
            {engagement.high > 0 && (
              <Chip
                size="small"
                label={`${engagement.high} high`}
                sx={{ bgcolor: "#f97316", color: "#fff", height: 20, fontSize: 11 }}
              />
            )}
          </Stack>
          <Typography variant="caption" color="text.disabled" flexShrink={0}>
            {engagement.created_at}
          </Typography>
        </Stack>
      </Paper>
    </motion.div>
  );
}

export default function EngagementsPage() {
  const router = useRouter();
  const toast = useToast();
  const [engagements, setEngagements] = useState<EngagementSummary[] | null>(null);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [query, setQuery] = useState("");
  const [target, setTarget] = useState("");
  const [name, setName] = useState("");
  const [notes, setNotes] = useState("");
  const [icon, setIcon] = useState(DEFAULT_ENGAGEMENT_ICON);
  const [methodology, setMethodology] = useState(DEFAULT_METHODOLOGY);
  const [creating, setCreating] = useState(false);

  async function refresh() {
    try {
      setEngagements(await api.listEngagements());
      setError("");
    } catch {
      setError("Could not reach the backend API. Is it running?");
      setEngagements([]);
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- initial data fetch on mount
    refresh();
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!target.trim()) return;
    setCreating(true);
    try {
      const eng = await api.createEngagement(target.trim(), name.trim(), notes.trim(), icon, methodology);
      toast.success(`Engagement "${eng.name}" created`);
      router.push(`/engagements/${eng.id}`);
    } catch {
      toast.error("Failed to create engagement.");
      setCreating(false);
    }
  }

  async function handleDelete(id: string, name: string) {
    if (!confirm(`Delete engagement "${name}"? This cannot be undone.`)) return;
    try {
      await api.deleteEngagement(id);
      toast.success(`Deleted "${name}"`);
      refresh();
    } catch {
      toast.error("Failed to delete engagement.");
    }
  }

  const filtered = useMemo(() => {
    if (!engagements) return [];
    const q = query.trim().toLowerCase();
    if (!q) return engagements;
    return engagements.filter(
      (e) => e.name.toLowerCase().includes(q) || e.target.toLowerCase().includes(q)
    );
  }, [engagements, query]);

  const totals = useMemo(() => {
    if (!engagements) return { count: 0, findings: 0, critical: 0, high: 0 };
    return engagements.reduce(
      (acc, e) => ({
        count: acc.count + 1,
        findings: acc.findings + e.findings,
        critical: acc.critical + e.critical,
        high: acc.high + e.high,
      }),
      { count: 0, findings: 0, critical: 0, high: 0 }
    );
  }, [engagements]);

  const loading = engagements === null;

  return (
    <Container maxWidth="lg" sx={{ py: 6, flex: 1 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start" mb={4}>
        <Box>
          <Typography
            component={Link}
            href="/"
            variant="caption"
            sx={{ color: "text.secondary", textDecoration: "none", "&:hover": { color: "text.primary" } }}
          >
            ← oculus
          </Typography>
          <Stack direction="row" alignItems="center" spacing={1}>
            <Box
              component="img"
              src="/logo.svg"
              alt=""
              width={26}
              height={26}
              sx={{ filter: "drop-shadow(0 0 4px rgba(94,234,212,0.5))" }}
            />
            <Typography variant="h5" fontWeight={700}>
              Engagements
            </Typography>
          </Stack>
        </Box>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => setShowForm(true)}>
          New Engagement
        </Button>
      </Stack>

      {!loading && engagements.length > 0 && (
        <Stack direction="row" spacing={2} mb={4} flexWrap="wrap" useFlexGap>
          <StatCard label="Engagements" value={totals.count} delay={0} />
          <StatCard label="Total findings" value={totals.findings} delay={0.05} />
          <StatCard
            label="Critical"
            value={totals.critical}
            color={totals.critical > 0 ? "#ef4444" : undefined}
            delay={0.1}
          />
          <StatCard
            label="High"
            value={totals.high}
            color={totals.high > 0 ? "#f97316" : undefined}
            delay={0.15}
          />
        </Stack>
      )}

      <Dialog open={showForm} onClose={() => setShowForm(false)} fullWidth maxWidth="sm">
        <form onSubmit={handleCreate}>
          <DialogTitle>New engagement</DialogTitle>
          <DialogContent>
            <Stack spacing={2} mt={1}>
              <TextField
                required
                autoFocus
                fullWidth
                label="Target"
                placeholder="example.com"
                value={target}
                onChange={(e) => setTarget(e.target.value)}
              />
              <TextField
                fullWidth
                label="Name"
                placeholder="defaults to target"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
              <TextField
                fullWidth
                multiline
                minRows={2}
                label="Scope notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
              <IconPicker value={icon} onChange={setIcon} />
              <MethodologyPicker value={methodology} onChange={setMethodology} />
            </Stack>
          </DialogContent>
          <DialogActions sx={{ px: 3, pb: 2.5 }}>
            <Button onClick={() => setShowForm(false)}>Cancel</Button>
            <Button type="submit" variant="contained" disabled={creating}>
              {creating ? "Creating…" : "Create engagement"}
            </Button>
          </DialogActions>
        </form>
      </Dialog>

      {error && (
        <Typography
          variant="body2"
          sx={{ mb: 3, px: 2, py: 1.2, borderRadius: 1, bgcolor: "rgba(239,68,68,0.12)", color: "#f87171" }}
        >
          {error}
        </Typography>
      )}

      {!loading && engagements.length > 0 && (
        <TextField
          size="small"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by name or target…"
          sx={{ mb: 2, maxWidth: 320 }}
          slotProps={{
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" sx={{ color: "text.secondary" }} />
                </InputAdornment>
              ),
            },
          }}
        />
      )}

      {!loading && engagements.length === 0 ? (
        <Paper
          sx={{
            px: 4,
            py: 8,
            textAlign: "center",
            borderStyle: "dashed",
          }}
        >
          <Typography fontWeight={600} mb={0.5}>
            No engagements yet
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Create one to start working through the OWASP WSTG checklist.
          </Typography>
        </Paper>
      ) : (
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", sm: "repeat(2, 1fr)", md: "repeat(3, 1fr)" },
            gap: 2,
          }}
        >
          {loading
            ? Array.from({ length: 6 }).map((_, i) => (
                <Paper key={i} sx={{ p: 2.5 }}>
                  <Skeleton variant="text" width="65%" height={28} />
                  <Skeleton variant="text" width="40%" sx={{ mb: 2 }} />
                  <Skeleton variant="rounded" height={6} sx={{ mb: 2, borderRadius: 3 }} />
                  <Skeleton variant="text" width="45%" />
                </Paper>
              ))
            : filtered.length === 0 ? (
                <Box sx={{ gridColumn: "1 / -1" }}>
                  <Typography color="text.secondary" textAlign="center" py={4}>
                    No engagements match &ldquo;{query}&rdquo;.
                  </Typography>
                </Box>
              ) : (
                filtered.map((e, i) => (
                  <EngagementCard
                    key={e.id}
                    engagement={e}
                    onDelete={() => handleDelete(e.id, e.name)}
                    delay={Math.min(i * 0.04, 0.3)}
                  />
                ))
              )}
        </Box>
      )}
    </Container>
  );
}
