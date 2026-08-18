"use client";

import { useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import TextField from "@mui/material/TextField";
import Autocomplete from "@mui/material/Autocomplete";
import Stack from "@mui/material/Stack";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import type { ChecklistItem, ToolInfo } from "@/lib/types";

export interface ChecklistItemFormValues {
  name: string;
  description: string;
  category: string;
  category_code: string;
  tools: string[];
  references: string[];
}

function toFormValues(item?: ChecklistItem): ChecklistItemFormValues {
  return {
    name: item?.name ?? "",
    description: item?.description ?? "",
    category: item?.category ?? "",
    category_code: item?.category_code ?? "",
    tools: item?.tools ?? [],
    references: item?.references ?? [],
  };
}

export function ChecklistItemDialog({
  mode,
  item,
  categories,
  allTools,
  onClose,
  onSubmit,
}: {
  mode: "create" | "edit";
  item?: ChecklistItem;
  categories: string[];
  allTools: ToolInfo[];
  onClose: () => void;
  onSubmit: (values: ChecklistItemFormValues) => Promise<void>;
}) {
  const [values, setValues] = useState<ChecklistItemFormValues>(toFormValues(item));
  const [referencesText, setReferencesText] = useState((item?.references ?? []).join("\n"));
  const [saving, setSaving] = useState(false);

  function toggleTool(name: string) {
    setValues((prev) => ({
      ...prev,
      tools: prev.tools.includes(name)
        ? prev.tools.filter((t) => t !== name)
        : [...prev.tools, name],
    }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!values.name.trim() || !values.category.trim()) return;
    setSaving(true);
    try {
      await onSubmit({
        ...values,
        name: values.name.trim(),
        category: values.category.trim(),
        references: referencesText
          .split("\n")
          .map((r) => r.trim())
          .filter(Boolean),
      });
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="sm">
      <form onSubmit={handleSubmit}>
        <DialogTitle>{mode === "create" ? "Add checklist item" : `Edit ${item?.id}`}</DialogTitle>
        <DialogContent>
          <Stack spacing={2.25} mt={0.5}>
            <TextField
              required
              autoFocus
              fullWidth
              label="Name"
              value={values.name}
              onChange={(e) => setValues((v) => ({ ...v, name: e.target.value }))}
            />
            <TextField
              fullWidth
              multiline
              minRows={2}
              label="Description"
              value={values.description}
              onChange={(e) => setValues((v) => ({ ...v, description: e.target.value }))}
            />
            <Stack direction="row" spacing={2}>
              <Autocomplete
                freeSolo
                fullWidth
                options={categories}
                inputValue={values.category}
                onInputChange={(_, v) => setValues((prev) => ({ ...prev, category: v }))}
                renderInput={(params) => <TextField {...params} required label="Category" />}
              />
              <TextField
                fullWidth
                label="Category code"
                placeholder="auto"
                value={values.category_code}
                onChange={(e) => setValues((v) => ({ ...v, category_code: e.target.value }))}
              />
            </Stack>

            <Box>
              <Typography variant="body2" mb={1} color="text.secondary">
                Tools
              </Typography>
              <Stack direction="row" flexWrap="wrap" useFlexGap gap={1}>
                {allTools.map((t) => {
                  const selected = values.tools.includes(t.name);
                  return (
                    <Tooltip
                      key={t.name}
                      title={t.available ? "Installed on the backend host" : "Not installed — will use simulated output"}
                    >
                      <Chip
                        label={t.name}
                        clickable
                        onClick={() => toggleTool(t.name)}
                        color={selected ? "primary" : "default"}
                        variant={selected ? "filled" : "outlined"}
                        size="small"
                        sx={{ opacity: t.available ? 1 : 0.55 }}
                      />
                    </Tooltip>
                  );
                })}
              </Stack>
            </Box>

            <TextField
              fullWidth
              multiline
              minRows={2}
              label="References (one URL per line)"
              value={referencesText}
              onChange={(e) => setReferencesText(e.target.value)}
              slotProps={{ input: { sx: { fontFamily: "var(--font-geist-mono)", fontSize: 13 } } }}
            />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="contained" disabled={saving}>
            {saving ? "Saving…" : mode === "create" ? "Add item" : "Save changes"}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
}
