"use client";

import { useState } from "react";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogContent from "@mui/material/DialogContent";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import TextField from "@mui/material/TextField";
import MenuItem from "@mui/material/MenuItem";
import Collapse from "@mui/material/Collapse";
import AddIcon from "@mui/icons-material/Add";
import RestoreIcon from "@mui/icons-material/Restore";
import CloseIcon from "@mui/icons-material/Close";
import { sensitivePortLabel } from "@/lib/engagementPorts";
import type { EngagementPortEntry } from "@/lib/engagementPorts";

export function PortsDialog({
  entries,
  removedPorts,
  onAdd,
  onRemove,
  onRestore,
  onClose,
}: {
  entries: EngagementPortEntry[];
  removedPorts: string[];
  onAdd: (port: number, protocol: string, service: string, note: string) => Promise<void>;
  onRemove: (port: number, protocol: string) => void;
  onRestore: (key: string) => void;
  onClose: () => void;
}) {
  const [showHidden, setShowHidden] = useState(false);
  const [newPort, setNewPort] = useState("");
  const [newProtocol, setNewProtocol] = useState("tcp");
  const [newService, setNewService] = useState("");
  const [newNote, setNewNote] = useState("");
  const [adding, setAdding] = useState(false);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!newPort.trim()) return;
    setAdding(true);
    try {
      await onAdd(Number(newPort.trim()), newProtocol, newService.trim(), newNote.trim());
      setNewPort("");
      setNewService("");
      setNewNote("");
    } finally {
      setAdding(false);
    }
  }

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="sm" slotProps={{ paper: { sx: { height: "75vh" } } }}>
      <Stack
        direction="row"
        alignItems="center"
        justifyContent="space-between"
        sx={{ px: 2.5, py: 1.5, borderBottom: "1px solid", borderColor: "divider" }}
      >
        <Box>
          <Typography variant="subtitle1" fontWeight={700}>
            Ports
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {entries.length} open across every tool run in this engagement — updates live as scans
            finish.
          </Typography>
        </Box>
        <IconButton size="small" onClick={onClose}>
          <CloseIcon fontSize="small" />
        </IconButton>
      </Stack>
      <DialogContent sx={{ display: "flex", flexDirection: "column", overflow: "hidden", p: 2.5 }}>
        <Box component="form" onSubmit={handleAdd} mb={1.5}>
          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
            <TextField
              size="small"
              placeholder="port"
              value={newPort}
              onChange={(e) => setNewPort(e.target.value.replace(/[^0-9]/g, ""))}
              sx={{ width: 90 }}
            />
            <TextField
              size="small"
              select
              value={newProtocol}
              onChange={(e) => setNewProtocol(e.target.value)}
              sx={{ width: 90 }}
            >
              <MenuItem value="tcp">tcp</MenuItem>
              <MenuItem value="udp">udp</MenuItem>
            </TextField>
            <TextField
              size="small"
              placeholder="service (optional)"
              value={newService}
              onChange={(e) => setNewService(e.target.value)}
              sx={{ width: 140 }}
            />
            <TextField
              size="small"
              placeholder="note (optional)"
              value={newNote}
              onChange={(e) => setNewNote(e.target.value)}
              sx={{ flex: 1, minWidth: 120 }}
            />
            <IconButton
              type="submit"
              size="small"
              disabled={!newPort.trim() || adding}
              sx={{ border: "1px solid", borderColor: "primary.main", borderRadius: 1 }}
            >
              <AddIcon fontSize="small" />
            </IconButton>
          </Stack>
        </Box>

        <Box
          sx={{
            flex: 1,
            overflow: "auto",
            borderRadius: 1,
            bgcolor: "#000",
            border: "1px solid rgba(255,255,255,0.08)",
          }}
        >
          {entries.length === 0 ? (
            <Typography variant="body2" color="text.secondary" sx={{ p: 2 }}>
              No open ports discovered yet — run nmap or naabu, or add one above.
            </Typography>
          ) : (
            <Stack>
              {entries.map((e) => {
                const key = `${e.port}/${e.protocol}`;
                const sensitive = sensitivePortLabel(e.port);
                return (
                  <Stack
                    key={key}
                    direction="row"
                    alignItems="center"
                    spacing={1}
                    sx={{
                      px: 1.5,
                      py: 0.75,
                      borderBottom: "1px solid rgba(255,255,255,0.06)",
                      "&:hover .row-hover-btn": { opacity: 1 },
                    }}
                  >
                    <Typography
                      variant="body2"
                      sx={{ fontFamily: "var(--font-geist-mono)", fontSize: 12.5, width: 90 }}
                    >
                      {e.port}/{e.protocol}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ fontSize: 12.5, width: 100 }} noWrap>
                      {e.service || "—"}
                    </Typography>
                    <Typography
                      variant="body2"
                      color="text.disabled"
                      sx={{ fontSize: 11.5, flex: 1 }}
                      noWrap
                      title={e.version}
                    >
                      {e.version}
                      {e.note ? ` ${e.note}` : ""}
                    </Typography>
                    {e.manual && (
                      <Chip
                        label="manual"
                        size="small"
                        sx={{ height: 18, fontSize: 10, color: "#a855f7", borderColor: "#a855f7" }}
                        variant="outlined"
                      />
                    )}
                    {sensitive && (
                      <Chip
                        label={sensitive}
                        size="small"
                        sx={{ height: 18, fontSize: 10, color: "#ef4444", borderColor: "#ef4444" }}
                        variant="outlined"
                      />
                    )}
                    <Tooltip title={`Remove ${key}`}>
                      <IconButton
                        size="small"
                        className="row-hover-btn"
                        onClick={() => onRemove(e.port, e.protocol)}
                        sx={{ p: 0.25, opacity: 0, transition: "opacity 0.1s" }}
                      >
                        <CloseIcon fontSize="small" sx={{ color: "#ef4444" }} />
                      </IconButton>
                    </Tooltip>
                  </Stack>
                );
              })}
            </Stack>
          )}
        </Box>

        {removedPorts.length > 0 && (
          <Box mt={1}>
            <Button
              size="small"
              onClick={() => setShowHidden((v) => !v)}
              sx={{ fontSize: 11, textTransform: "none", color: "text.secondary" }}
            >
              {showHidden ? "Hide" : "Show"} hidden ({removedPorts.length})
            </Button>
            <Collapse in={showHidden}>
              <Stack spacing={0.5} mt={0.5}>
                {removedPorts.map((p) => (
                  <Stack
                    key={p}
                    direction="row"
                    alignItems="center"
                    justifyContent="space-between"
                    sx={{ fontFamily: "var(--font-geist-mono)", fontSize: 12, color: "text.secondary", px: 1 }}
                  >
                    <span>{p}</span>
                    <Tooltip title="Restore">
                      <IconButton size="small" onClick={() => onRestore(p)}>
                        <RestoreIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </Stack>
                ))}
              </Stack>
            </Collapse>
          </Box>
        )}
      </DialogContent>
    </Dialog>
  );
}
