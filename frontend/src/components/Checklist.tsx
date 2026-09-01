"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import Box from "@mui/material/Box";
import TextField from "@mui/material/TextField";
import IconButton from "@mui/material/IconButton";
import ListItemButton from "@mui/material/ListItemButton";
import Collapse from "@mui/material/Collapse";
import Card from "@mui/material/Card";
import CardActionArea from "@mui/material/CardActionArea";
import CardContent from "@mui/material/CardContent";
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
import { GREEN } from "@/lib/theme";
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
  // `categories` is empty on this component's first render (the parent
  // engagement page hasn't fetched yet) — collapsing everything has to
  // wait until the real category list actually arrives, but should only
  // run that one time, not every time `categories` re-renders afterward
  // (which would stomp a tab the tester deliberately reopened).
  const didDefaultCollapse = useRef(false);
  useEffect(() => {
    if (didDefaultCollapse.current || categories.length === 0) return;
    didDefaultCollapse.current = true;
    setCollapsed(new Set(categories));
  }, [categories]);

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
                <Stack spacing={0.75} pb={0.5}>
                  {catItems.map((item) => {
                    const isSelected = selectedId === item.id;
                    return (
                      <motion.div
                        key={item.id}
                        whileHover={{ scale: 1.015 }}
                        whileTap={{ scale: 0.985 }}
                        transition={{ duration: 0.12 }}
                      >
                        <Card
                          variant="outlined"
                          sx={{
                            borderLeft: "3px solid",
                            borderLeftColor: STATUS_COLOR[item.status],
                            borderColor: isSelected ? "primary.main" : "divider",
                            backgroundColor: isSelected ? `${GREEN}1a` : "background.paper",
                            boxShadow: isSelected
                              ? `0 0 0 1px ${GREEN}59, 0 0 14px ${GREEN}2e`
                              : "none",
                            transition: "border-color 0.15s, box-shadow 0.15s, background-color 0.15s",
                          }}
                        >
                          <CardActionArea onClick={() => onSelect(item.id)}>
                            <CardContent sx={{ py: 1, px: 1.25, "&:last-child": { pb: 1 } }}>
                              <Stack direction="row" alignItems="center" spacing={1}>
                                <Box sx={{ flex: 1, minWidth: 0 }}>
                                  <Typography
                                    variant="caption"
                                    display="block"
                                    color="text.disabled"
                                    sx={{ fontFamily: "var(--font-geist-mono)", fontSize: 10.5, lineHeight: 1.4 }}
                                  >
                                    {item.id}
                                  </Typography>
                                  <Typography
                                    variant="body2"
                                    noWrap
                                    fontWeight={isSelected ? 600 : 400}
                                    sx={{ color: isSelected ? "text.primary" : "text.secondary" }}
                                  >
                                    {item.name}
                                  </Typography>
                                </Box>
                                <Stack alignItems="flex-end" spacing={0.5} flexShrink={0}>
                                  {item.status === "running" ? (
                                    <motion.div
                                      animate={{ opacity: [1, 0.35, 1] }}
                                      transition={{ duration: 1.1, repeat: Infinity }}
                                      style={{
                                        color: STATUS_COLOR.running,
                                        fontSize: 14,
                                        lineHeight: 1,
                                      }}
                                    >
                                      {STATUS_ICON.running}
                                    </motion.div>
                                  ) : (
                                    <Typography sx={{ color: STATUS_COLOR[item.status], fontSize: 14, lineHeight: 1 }}>
                                      {STATUS_ICON[item.status]}
                                    </Typography>
                                  )}
                                  {item.findings.length > 0 && (
                                    <Chip
                                      size="small"
                                      label={item.findings.length}
                                      sx={{ height: 16, fontSize: 10, bgcolor: "rgba(255,255,255,0.12)" }}
                                    />
                                  )}
                                </Stack>
                              </Stack>
                            </CardContent>
                          </CardActionArea>
                        </Card>
                      </motion.div>
                    );
                  })}
                </Stack>
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
