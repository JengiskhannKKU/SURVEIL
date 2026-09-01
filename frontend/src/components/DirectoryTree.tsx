"use client";

import { useState } from "react";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import FolderOutlinedIcon from "@mui/icons-material/FolderOutlined";
import InsertDriveFileOutlinedIcon from "@mui/icons-material/InsertDriveFileOutlined";
import PlayCircleOutlineIcon from "@mui/icons-material/PlayCircleOutline";
import Chip from "@mui/material/Chip";
import type { TreeNode } from "@/lib/pathTree";

// 401/403 mean the path exists but needs credentials/permission; 200 means
// it's reached and served with no auth at all — the two things a tester
// actually needs to tell apart at a glance in this tree, not just "found".
function StatusChip({ status }: { status: number | null }) {
  if (status === null) return null;
  const isOpen = status === 200;
  const isAuthWalled = status === 401 || status === 403;
  const color = isOpen ? "#22c55e" : isAuthWalled ? "#f59e0b" : "#64748b";
  const label = isOpen ? "200 open" : isAuthWalled ? `${status} needs auth` : String(status);
  return (
    <Chip
      label={label}
      size="small"
      sx={{
        height: 18,
        fontSize: 10.5,
        fontFamily: "var(--font-geist-mono)",
        color,
        borderColor: color,
        bgcolor: "transparent",
      }}
      variant="outlined"
    />
  );
}

function Node({
  node,
  depth,
  onRunHere,
}: {
  node: TreeNode;
  depth: number;
  onRunHere: (path: string) => void;
}) {
  const [open, setOpen] = useState(depth < 1);
  const hasChildren = node.children.length > 0;

  return (
    <Box>
      <Stack
        direction="row"
        alignItems="center"
        spacing={0.5}
        sx={{
          pl: depth * 2,
          py: 0.25,
          borderRadius: 0.5,
          "&:hover": { bgcolor: "rgba(255,255,255,0.04)" },
          "&:hover .run-here-btn": { opacity: 1 },
        }}
      >
        {hasChildren ? (
          <IconButton size="small" onClick={() => setOpen((o) => !o)} sx={{ p: 0.25 }}>
            {open ? <ExpandMoreIcon fontSize="small" /> : <ChevronRightIcon fontSize="small" />}
          </IconButton>
        ) : (
          <Box width={22} flexShrink={0} />
        )}
        {hasChildren ? (
          <FolderOutlinedIcon fontSize="small" sx={{ color: "#22c55e" }} />
        ) : (
          <InsertDriveFileOutlinedIcon fontSize="small" sx={{ color: "text.secondary" }} />
        )}
        <Typography
          variant="body2"
          noWrap
          title={node.path}
          sx={{ fontFamily: "var(--font-geist-mono)", fontSize: 12.5 }}
        >
          {node.name}
        </Typography>
        {node.observed && <StatusChip status={node.status} />}
        <Box flex={1} />
        <Tooltip title={`Run a tool against ${node.path}`}>
          <IconButton
            size="small"
            className="run-here-btn"
            onClick={() => onRunHere(node.path)}
            sx={{ p: 0.25, opacity: 0, transition: "opacity 0.1s" }}
          >
            <PlayCircleOutlineIcon fontSize="small" sx={{ color: "#22c55e" }} />
          </IconButton>
        </Tooltip>
      </Stack>
      {hasChildren && open && (
        <Box>
          {node.children.map((child) => (
            <Node key={child.path} node={child} depth={depth + 1} onRunHere={onRunHere} />
          ))}
        </Box>
      )}
    </Box>
  );
}

export function DirectoryTree({
  root,
  onRunHere,
  emptyMessage = "No directory/file paths could be parsed from this output.",
}: {
  root: TreeNode;
  onRunHere: (path: string) => void;
  emptyMessage?: string;
}) {
  if (root.children.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
        {emptyMessage}
      </Typography>
    );
  }
  return (
    <Box sx={{ maxHeight: 320, overflow: "auto" }}>
      {root.children.map((child) => (
        <Node key={child.path} node={child} depth={0} onRunHere={onRunHere} />
      ))}
    </Box>
  );
}
