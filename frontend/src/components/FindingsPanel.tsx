"use client";

import { useState } from "react";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import MenuItem from "@mui/material/MenuItem";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import Paper from "@mui/material/Paper";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { AnimatePresence, motion } from "framer-motion";
import { api } from "@/lib/api";
import { SeverityBadge } from "@/components/Badge";
import { useToast } from "@/lib/toast";
import { SEVERITY_ORDER, sortBySeverity } from "@/lib/severity";
import type { ChecklistItem, Finding, Severity } from "@/lib/types";

export function FindingsPanel({
  engagementId,
  item,
  onChange,
}: {
  engagementId: string;
  item: ChecklistItem;
  onChange: (item: ChecklistItem) => void;
}) {
  const toast = useToast();
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [severity, setSeverity] = useState<Severity>("medium");
  const [description, setDescription] = useState("");
  const [remediation, setRemediation] = useState("");
  const [cvssVector, setCvssVector] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setSaving(true);
    try {
      const finding = await api.addFinding(engagementId, item.id, {
        title: title.trim(),
        severity,
        description: description.trim(),
        remediation: remediation.trim(),
        cvss_vector: cvssVector.trim(),
      });
      onChange({ ...item, findings: [...item.findings, finding] });
      setTitle("");
      setDescription("");
      setRemediation("");
      setCvssVector("");
      setSeverity("medium");
      setShowForm(false);
      toast.success("Finding added");
    } catch {
      toast.error("Failed to add finding");
    } finally {
      setSaving(false);
    }
  }

  async function toggleVerified(f: Finding) {
    try {
      const updated = await api.updateFinding(engagementId, item.id, f.id, {
        verified: !f.verified,
      });
      onChange({
        ...item,
        findings: item.findings.map((x) => (x.id === f.id ? updated : x)),
      });
      toast.success(updated.verified ? "Marked verified" : "Marked unverified");
    } catch {
      toast.error("Failed to update finding");
    }
  }

  async function handleDelete(f: Finding) {
    if (!confirm(`Delete finding "${f.title}"?`)) return;
    try {
      await api.deleteFinding(engagementId, item.id, f.id);
      onChange({ ...item, findings: item.findings.filter((x) => x.id !== f.id) });
      toast.success("Finding deleted");
    } catch {
      toast.error("Failed to delete finding");
    }
  }

  const findings = sortBySeverity(item.findings);

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" mb={1.5}>
        <Typography variant="subtitle2" fontWeight={700}>
          Findings ({item.findings.length})
        </Typography>
        <Button size="small" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancel" : "+ Add finding"}
        </Button>
      </Stack>

      <AnimatePresence initial={false}>
        {showForm && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            style={{ overflow: "hidden" }}
          >
            <Paper component="form" onSubmit={handleAdd} sx={{ p: 2, mb: 2 }}>
              <Stack spacing={1.5}>
                <Stack direction="row" spacing={1.5}>
                  <TextField
                    required
                    autoFocus
                    fullWidth
                    size="small"
                    label="Title"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                  />
                  <TextField
                    select
                    size="small"
                    label="Severity"
                    value={severity}
                    onChange={(e) => setSeverity(e.target.value as Severity)}
                    sx={{ minWidth: 140 }}
                  >
                    {SEVERITY_ORDER.map((s) => (
                      <MenuItem key={s} value={s}>
                        {s}
                      </MenuItem>
                    ))}
                  </TextField>
                </Stack>
                <TextField
                  fullWidth
                  multiline
                  minRows={2}
                  size="small"
                  label="Description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
                <Stack direction="row" spacing={1.5}>
                  <TextField
                    fullWidth
                    size="small"
                    label="CVSS vector (optional)"
                    value={cvssVector}
                    onChange={(e) => setCvssVector(e.target.value)}
                    slotProps={{ input: { sx: { fontFamily: "var(--font-geist-mono)", fontSize: 13 } } }}
                  />
                  <TextField
                    fullWidth
                    size="small"
                    label="Remediation"
                    value={remediation}
                    onChange={(e) => setRemediation(e.target.value)}
                  />
                </Stack>
                <Box>
                  <Button type="submit" size="small" variant="contained" disabled={saving}>
                    {saving ? "Saving…" : "Save finding"}
                  </Button>
                </Box>
              </Stack>
            </Paper>
          </motion.div>
        )}
      </AnimatePresence>

      {findings.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          No findings on this item yet.
        </Typography>
      ) : (
        <Stack spacing={1}>
          {findings.map((f) => (
            <Accordion
              key={f.id}
              disableGutters
              sx={{
                bgcolor: "rgba(255,255,255,0.02)",
                border: "1px solid",
                borderColor: "divider",
                "&:before": { display: "none" },
              }}
            >
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Stack direction="row" spacing={1.25} alignItems="center" sx={{ minWidth: 0 }}>
                  <SeverityBadge severity={f.severity} />
                  <Typography variant="body2" fontWeight={600} noWrap>
                    {f.title}
                  </Typography>
                  {f.verified && (
                    <Typography variant="caption" sx={{ color: "#22c55e", flexShrink: 0 }}>
                      ✓ verified
                    </Typography>
                  )}
                  <Typography variant="caption" color="text.disabled" flexShrink={0}>
                    ({f.tool})
                  </Typography>
                </Stack>
              </AccordionSummary>
              <AccordionDetails>
                <Stack spacing={1.25}>
                  {f.description && (
                    <Typography variant="body2" color="text.secondary">
                      {f.description}
                    </Typography>
                  )}
                  {f.evidence && (
                    <Box
                      component="pre"
                      sx={{
                        m: 0,
                        p: 1.25,
                        borderRadius: 1,
                        bgcolor: "rgba(0,0,0,0.4)",
                        fontSize: 12,
                        whiteSpace: "pre-wrap",
                        overflowWrap: "anywhere",
                        overflowX: "auto",
                      }}
                    >
                      {f.evidence}
                    </Box>
                  )}
                  {f.remediation && (
                    <Typography variant="body2" color="text.secondary">
                      <Box component="span" fontWeight={600} color="text.primary">
                        Remediation:{" "}
                      </Box>
                      {f.remediation}
                    </Typography>
                  )}
                  {f.cvss_vector && (
                    <Typography variant="caption" sx={{ fontFamily: "var(--font-geist-mono)" }}>
                      {f.cvss_vector} ({f.cvss_score})
                    </Typography>
                  )}
                  <Stack direction="row" spacing={2}>
                    <Button size="small" onClick={() => toggleVerified(f)}>
                      {f.verified ? "Unverify" : "Verify"}
                    </Button>
                    <Button size="small" color="error" onClick={() => handleDelete(f)}>
                      Delete
                    </Button>
                  </Stack>
                </Stack>
              </AccordionDetails>
            </Accordion>
          ))}
        </Stack>
      )}
    </Box>
  );
}
