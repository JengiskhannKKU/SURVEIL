"use client";

import { useEffect, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import TextField from "@mui/material/TextField";
import IconButton from "@mui/material/IconButton";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import Collapse from "@mui/material/Collapse";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import InputAdornment from "@mui/material/InputAdornment";
import AddIcon from "@mui/icons-material/Add";
import SearchIcon from "@mui/icons-material/Search";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { api } from "@/lib/api";
import { useToast } from "@/lib/toast";
import { ChecklistItemDialog } from "@/components/ChecklistItemDialog";
import type { ChecklistItem, ToolInfo } from "@/lib/types";

const STATUS_COLOR: Record<string, string> = {
  pending: "rgba(255,255,255,0.35)",
  running: "#f59e0b",
  done: "#22c55e",
  skipped: "rgba(255,255,255,0.35)",
  failed: "#ef4444",
};

const STATUS_ICON: Record<string, string> = {
  pending: "○",
  running: "◎",
  done: "✓",
  skipped: "—",
  failed: "✗",
};

export function Checklist({
  engagementId,
  items,
  selectedId,
  onSelect,
  categories,
  allTools,
  onCreate,
}: {
  engagementId: string;
  items: ChecklistItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  categories: string[];
  allTools: ToolInfo[];
  onCreate: (item: ChecklistItem) => void;
}) {
  const toast = useToast();
  const [query, setQuery] = useState("");
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [showAdd, setShowAdd] = useState(false);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter(
      (i) =>
        i.name.toLowerCase().includes(q) ||
        i.id.toLowerCase().includes(q) ||
        i.category.toLowerCase().includes(q)
    );
  }, [items, query]);

  const byCategory = useMemo(() => {
    const map = new Map<string, ChecklistItem[]>();
    for (const item of filtered) {
      const list = map.get(item.category) ?? [];
      list.push(item);
      map.set(item.category, list);
    }
    return map;
  }, [filtered]);

  useEffect(() => {
    function handler(e: KeyboardEvent) {
      if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
      const target = e.target as HTMLElement;
      if (["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)) return;
      e.preventDefault();
      const flat = [...byCategory.values()].flat();
      const idx = flat.findIndex((i) => i.id === selectedId);
      const next =
        e.key === "ArrowDown"
          ? flat[Math.min(idx + 1, flat.length - 1)]
          : flat[Math.max(idx - 1, 0)];
      if (next) onSelect(next.id);
    }
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [byCategory, selectedId, onSelect]);

  function toggleCategory(cat: string) {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });
  }

  return (
    <Box display="flex" flexDirection="column" height="100%">
      <Stack direction="row" spacing={1} mb={1.5}>
        <TextField
          size="small"
          fullWidth
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Filter… (↑↓ to navigate)"
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
        <IconButton
          size="small"
          onClick={() => setShowAdd(true)}
          title="Add checklist item"
          sx={{ border: "1px solid", borderColor: "divider", borderRadius: 1 }}
        >
          <AddIcon fontSize="small" />
        </IconButton>
      </Stack>

      <Box flex={1} sx={{ overflowY: "auto" }}>
        {[...byCategory.entries()].map(([category, catItems]) => {
          const isCollapsed = collapsed.has(category);
          const doneCount = catItems.filter((i) => ["done", "skipped"].includes(i.status)).length;
          return (
            <Box key={category} mb={1}>
              <ListItemButton
                onClick={() => toggleCategory(category)}
                dense
                sx={{ borderRadius: 1, py: 0.25 }}
              >
                <ExpandMoreIcon
                  fontSize="small"
                  sx={{
                    color: "text.secondary",
                    mr: 0.5,
                    transform: isCollapsed ? "rotate(-90deg)" : "none",
                    transition: "transform 0.15s",
                  }}
                />
                <Typography
                  variant="caption"
                  sx={{ flex: 1, fontWeight: 700, letterSpacing: 0.5, color: "text.secondary" }}
                >
                  {category.toUpperCase()}
                </Typography>
                <Typography variant="caption" color="text.disabled">
                  {doneCount}/{catItems.length}
                </Typography>
              </ListItemButton>
              <Collapse in={!isCollapsed}>
                <List dense disablePadding>
                  {catItems.map((item) => (
                    <ListItemButton
                      key={item.id}
                      selected={selectedId === item.id}
                      onClick={() => onSelect(item.id)}
                      sx={{
                        borderRadius: 1,
                        py: 0.6,
                        "&.Mui-selected": {
                          backgroundColor: "rgba(59,130,246,0.14)",
                          "&:hover": { backgroundColor: "rgba(59,130,246,0.2)" },
                        },
                      }}
                    >
                      <Box sx={{ flex: 1, minWidth: 0 }}>
                        <Typography
                          variant="body2"
                          noWrap
                          sx={{ color: selectedId === item.id ? "text.primary" : "text.secondary" }}
                        >
                          <Box component="span" sx={{ color: "text.disabled", mr: 0.5 }}>
                            {item.id}
                          </Box>
                          {item.name}
                        </Typography>
                      </Box>
                      <Stack direction="row" spacing={0.5} alignItems="center" flexShrink={0} ml={1}>
                        {item.findings.length > 0 && (
                          <Chip
                            size="small"
                            label={item.findings.length}
                            sx={{ height: 18, fontSize: 10, bgcolor: "rgba(255,255,255,0.12)" }}
                          />
                        )}
                        <Typography sx={{ color: STATUS_COLOR[item.status], fontSize: 13 }}>
                          {STATUS_ICON[item.status]}
                        </Typography>
                      </Stack>
                    </ListItemButton>
                  ))}
                </List>
              </Collapse>
            </Box>
          );
        })}
        {filtered.length === 0 && (
          <Typography variant="body2" color="text.secondary" px={1}>
            No items match &ldquo;{query}&rdquo;.
          </Typography>
        )}
      </Box>

      {showAdd && (
        <ChecklistItemDialog
          mode="create"
          categories={categories}
          allTools={allTools}
          onClose={() => setShowAdd(false)}
          onSubmit={async (values) => {
            try {
              const created = await api.createItem(engagementId, values);
              onCreate(created);
              toast.success(`Added ${created.id}`);
              setShowAdd(false);
            } catch {
              toast.error("Failed to add checklist item");
            }
          }}
        />
      )}
    </Box>
  );
}
