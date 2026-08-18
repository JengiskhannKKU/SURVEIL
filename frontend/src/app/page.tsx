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
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
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
import { api } from "@/lib/api";
import { useToast } from "@/lib/toast";
import { ProgressBar } from "@/components/SeverityBar";
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

export default function Home() {
  const router = useRouter();
  const toast = useToast();
  const [engagements, setEngagements] = useState<EngagementSummary[] | null>(null);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [query, setQuery] = useState("");
  const [target, setTarget] = useState("");
  const [name, setName] = useState("");
  const [notes, setNotes] = useState("");
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
      const eng = await api.createEngagement(target.trim(), name.trim(), notes.trim());
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
    <Container maxWidth="md" sx={{ py: 6, flex: 1 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start" mb={4}>
        <Box>
          <Typography
            variant="h1"
            sx={{
              fontSize: 30,
              fontWeight: 700,
              background: "linear-gradient(90deg, #f87171, #60a5fa)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              letterSpacing: -0.5,
            }}
          >
            surveil
          </Typography>
          <Typography variant="body2" color="text.secondary">
            OWASP WSTG checklist-driven web application penetration testing
          </Typography>
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
        <Paper sx={{ overflow: "hidden" }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Target</TableCell>
                <TableCell>Progress</TableCell>
                <TableCell>Findings</TableCell>
                <TableCell>Created</TableCell>
                <TableCell />
              </TableRow>
            </TableHead>
            <TableBody>
              {loading ? (
                Array.from({ length: 3 }).map((_, i) => (
                  <TableRow key={i}>
                    {Array.from({ length: 6 }).map((__, j) => (
                      <TableCell key={j}>
                        <Skeleton variant="text" width={j === 5 ? 20 : 90} />
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              ) : filtered.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} align="center" sx={{ color: "text.secondary", py: 3 }}>
                    No engagements match &ldquo;{query}&rdquo;.
                  </TableCell>
                </TableRow>
              ) : (
                filtered.map((e, i) => {
                  const [done, total] = e.progress.split("/").map(Number);
                  return (
                    <motion.tr
                      key={e.id}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ duration: 0.2, delay: Math.min(i * 0.03, 0.3) }}
                      style={{ display: "table-row" }}
                      className="row-hover"
                    >
                      <TableCell>
                        <Typography
                          component={Link}
                          href={`/engagements/${e.id}`}
                          variant="body2"
                          fontWeight={600}
                          sx={{ color: "text.primary", textDecoration: "none", "&:hover": { color: "primary.light" } }}
                        >
                          {e.name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {e.id}
                        </Typography>
                      </TableCell>
                      <TableCell sx={{ color: "text.secondary" }}>{e.target}</TableCell>
                      <TableCell>
                        <ProgressBar done={done || 0} total={total || 0} />
                      </TableCell>
                      <TableCell>
                        <Stack direction="row" spacing={0.75} alignItems="center">
                          <Typography variant="body2">{e.findings}</Typography>
                          {e.critical > 0 && (
                            <Chip
                              size="small"
                              label={`${e.critical} crit`}
                              sx={{ bgcolor: "#dc2626", color: "#fff", height: 20, fontSize: 11 }}
                            />
                          )}
                        </Stack>
                      </TableCell>
                      <TableCell sx={{ color: "text.secondary" }}>{e.created_at}</TableCell>
                      <TableCell align="right">
                        <IconButton
                          size="small"
                          onClick={() => handleDelete(e.id, e.name)}
                          sx={{ color: "text.secondary", "&:hover": { color: "#ef4444" } }}
                        >
                          <DeleteOutlineIcon fontSize="small" />
                        </IconButton>
                      </TableCell>
                    </motion.tr>
                  );
                })
              )}
            </TableBody>
          </Table>
        </Paper>
      )}
    </Container>
  );
}
