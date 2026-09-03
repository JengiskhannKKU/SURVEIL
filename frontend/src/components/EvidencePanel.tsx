"use client";

import { useRef, useState } from "react";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import CircularProgress from "@mui/material/CircularProgress";
import CloudUploadOutlinedIcon from "@mui/icons-material/CloudUploadOutlined";
import InsertDriveFileOutlinedIcon from "@mui/icons-material/InsertDriveFileOutlined";
import CloseIcon from "@mui/icons-material/Close";
import DownloadOutlinedIcon from "@mui/icons-material/DownloadOutlined";
import { api } from "@/lib/api";
import { useToast } from "@/lib/toast";
import type { ChecklistItem, EvidenceFile } from "@/lib/types";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function EvidenceCard({
  engagementId,
  itemId,
  evidence,
  onChange,
}: {
  engagementId: string;
  itemId: string;
  evidence: EvidenceFile;
  onChange: (item: ChecklistItem) => void;
}) {
  const toast = useToast();
  const [description, setDescription] = useState(evidence.description);
  const [saving, setSaving] = useState(false);
  const isImage = evidence.content_type.startsWith("image/");
  const fileUrl = api.evidenceFileUrl(engagementId, itemId, evidence.id);

  async function saveDescription() {
    if (description === evidence.description) return;
    setSaving(true);
    try {
      const updated = await api.updateEvidenceDescription(engagementId, itemId, evidence.id, description);
      onChange(updated);
    } catch {
      toast.error("Failed to save description");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    try {
      const updated = await api.deleteEvidence(engagementId, itemId, evidence.id);
      onChange(updated);
      toast.success(`Removed ${evidence.filename}`);
    } catch {
      toast.error("Failed to remove evidence");
    }
  }

  return (
    <Box
      sx={{
        border: "1px solid",
        borderColor: "divider",
        borderRadius: 1,
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
        bgcolor: "background.paper",
        "&:hover .evidence-actions": { opacity: 1 },
      }}
    >
      <Box
        component="a"
        href={fileUrl}
        target="_blank"
        rel="noreferrer"
        sx={{
          position: "relative",
          height: 110,
          bgcolor: "#000",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {isImage ? (
          // Arbitrary uploaded-file URL from our own backend, not a
          // build-time-known asset Next's <Image> optimizer could handle.
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={fileUrl}
            alt={evidence.filename}
            style={{ maxHeight: "100%", maxWidth: "100%", objectFit: "contain" }}
          />
        ) : (
          <InsertDriveFileOutlinedIcon sx={{ fontSize: 36, color: "text.secondary" }} />
        )}
        <Stack
          direction="row"
          spacing={0.5}
          className="evidence-actions"
          sx={{ position: "absolute", top: 4, right: 4, opacity: 0, transition: "opacity 0.1s" }}
        >
          <Tooltip title="Open / download">
            <IconButton
              size="small"
              component="span"
              sx={{ bgcolor: "rgba(0,0,0,0.6)", "&:hover": { bgcolor: "rgba(0,0,0,0.8)" } }}
            >
              <DownloadOutlinedIcon fontSize="small" sx={{ color: "#fff" }} />
            </IconButton>
          </Tooltip>
          <Tooltip title="Remove">
            <IconButton
              size="small"
              component="span"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                handleDelete();
              }}
              sx={{ bgcolor: "rgba(0,0,0,0.6)", "&:hover": { bgcolor: "rgba(239,68,68,0.8)" } }}
            >
              <CloseIcon fontSize="small" sx={{ color: "#fff" }} />
            </IconButton>
          </Tooltip>
        </Stack>
      </Box>
      <Box sx={{ p: 1 }}>
        <Typography
          variant="caption"
          noWrap
          title={evidence.filename}
          sx={{ display: "block", fontFamily: "var(--font-geist-mono)" }}
        >
          {evidence.filename}
        </Typography>
        <Typography variant="caption" color="text.disabled" sx={{ display: "block", mb: 0.5 }}>
          {formatSize(evidence.size_bytes)}
        </Typography>
        <TextField
          size="small"
          fullWidth
          multiline
          minRows={1}
          maxRows={3}
          placeholder="Describe this evidence…"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          onBlur={saveDescription}
          disabled={saving}
          sx={{ "& .MuiInputBase-input": { fontSize: 12.5 } }}
        />
      </Box>
    </Box>
  );
}

export function EvidencePanel({
  engagementId,
  item,
  onChange,
}: {
  engagementId: string;
  item: ChecklistItem;
  onChange: (item: ChecklistItem) => void;
}) {
  const toast = useToast();
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(0);
  const inputRef = useRef<HTMLInputElement | null>(null);

  async function uploadFiles(files: FileList | File[]) {
    const list = Array.from(files);
    if (list.length === 0) return;
    setUploading((n) => n + list.length);
    let latest: ChecklistItem | null = null;
    for (const file of list) {
      try {
        latest = await api.uploadEvidence(engagementId, item.id, file, "");
      } catch {
        toast.error(`Failed to upload ${file.name}`);
      } finally {
        setUploading((n) => n - 1);
      }
    }
    if (latest) {
      onChange(latest);
      toast.success(`${list.length} file${list.length === 1 ? "" : "s"} uploaded`);
    }
  }

  return (
    <Box>
      <Typography variant="subtitle2" fontWeight={700} mb={1}>
        Evidence{item.evidence.length > 0 ? ` (${item.evidence.length})` : ""}
      </Typography>

      <Box
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragActive(false);
          if (e.dataTransfer.files.length > 0) uploadFiles(e.dataTransfer.files);
        }}
        sx={{
          cursor: "pointer",
          border: "1px dashed",
          borderColor: dragActive ? "primary.main" : "divider",
          bgcolor: dragActive ? "rgba(94,234,212,0.08)" : "transparent",
          borderRadius: 1,
          px: 2,
          py: 2.5,
          textAlign: "center",
          transition: "border-color 0.15s, background-color 0.15s",
          mb: item.evidence.length > 0 || uploading > 0 ? 1.5 : 0,
          "&:hover": { borderColor: "primary.main" },
        }}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          hidden
          onChange={(e) => {
            if (e.target.files) uploadFiles(e.target.files);
            e.target.value = "";
          }}
        />
        <CloudUploadOutlinedIcon sx={{ color: "text.secondary", mb: 0.5 }} />
        <Typography variant="body2" color="text.secondary">
          Drag & drop screenshots, files, or anything else here — or click to browse
        </Typography>
      </Box>

      {uploading > 0 && (
        <Stack direction="row" alignItems="center" spacing={1} mb={1.5}>
          <CircularProgress size={14} />
          <Typography variant="caption" color="text.secondary">
            Uploading {uploading} file{uploading === 1 ? "" : "s"}…
          </Typography>
        </Stack>
      )}

      {item.evidence.length > 0 && (
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
            gap: 1.25,
          }}
        >
          {item.evidence.map((ev) => (
            <EvidenceCard
              key={ev.id}
              engagementId={engagementId}
              itemId={item.id}
              evidence={ev}
              onChange={onChange}
            />
          ))}
        </Box>
      )}
    </Box>
  );
}
