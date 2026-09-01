"use client";

// Node-link visualization of a discovered-path tree — an alternative to
// DirectoryTree's indented folder list for the same TreeNode data,
// requested alongside the ability to add/remove entries (see the
// engagement page's Paths/Endpoints dialog). Deliberately hand-rolled
// (plain SVG, no graph-layout library): the tree is shallow and narrow
// enough (a handful of path segments deep) that a simple depth-as-x,
// leaf-order-as-y layout reads fine without a real force-directed engine.
import { useMemo } from "react";
import Box from "@mui/material/Box";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import type { TreeNode } from "@/lib/pathTree";

const ROW_HEIGHT = 30;
const COL_WIDTH = 170;
const NODE_WIDTH = 130;
const NODE_HEIGHT = 22;

interface LayoutNode {
  node: TreeNode;
  x: number;
  y: number;
  parent: LayoutNode | null;
}

function layout(roots: TreeNode[]) {
  const nodes: LayoutNode[] = [];
  let leafCount = 0;

  function visit(node: TreeNode, depth: number, parent: LayoutNode | null): number {
    const entry: LayoutNode = { node, x: depth * COL_WIDTH, y: 0, parent };
    nodes.push(entry);
    if (node.children.length === 0) {
      entry.y = leafCount * ROW_HEIGHT;
      leafCount += 1;
    } else {
      const childYs = node.children.map((c) => visit(c, depth + 1, entry));
      entry.y = (Math.min(...childYs) + Math.max(...childYs)) / 2;
    }
    return entry.y;
  }

  for (const root of roots) visit(root, 0, null);

  const width = Math.max(...nodes.map((n) => n.x), 0) + COL_WIDTH;
  const height = Math.max(...nodes.map((n) => n.y), 0) + ROW_HEIGHT;
  return { nodes, width, height };
}

function statusColor(status: number | null, manual: boolean): string {
  if (manual) return "#a855f7";
  if (status === 200) return "#22c55e";
  if (status === 401 || status === 403) return "#f59e0b";
  if (status === null) return "#64748b";
  return "#3b82f6";
}

export function PathGraph({
  root,
  onRemove,
  emptyMessage = "No directory/file paths could be parsed from this output.",
  maxHeight = 320,
}: {
  root: TreeNode;
  onRemove?: (path: string) => void;
  emptyMessage?: string;
  maxHeight?: number | string;
}) {
  const { nodes, width, height } = useMemo(() => layout(root.children), [root]);

  if (root.children.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
        {emptyMessage}
      </Typography>
    );
  }

  const svgWidth = Math.max(width, 200);
  const svgHeight = Math.max(height, 60);

  return (
    <Box sx={{ maxHeight, overflow: "auto" }}>
      <Box sx={{ position: "relative", width: svgWidth, height: svgHeight }}>
      <svg width={svgWidth} height={svgHeight}>
        {nodes.map(
          (n) =>
            n.parent && (
              <path
                key={`edge-${n.node.path}`}
                d={`M ${n.parent.x + NODE_WIDTH} ${n.parent.y + NODE_HEIGHT / 2}
                    C ${n.parent.x + NODE_WIDTH + 30} ${n.parent.y + NODE_HEIGHT / 2},
                      ${n.x - 30} ${n.y + NODE_HEIGHT / 2},
                      ${n.x} ${n.y + NODE_HEIGHT / 2}`}
                fill="none"
                stroke="rgba(255,255,255,0.18)"
                strokeWidth={1.5}
              />
            )
        )}
        {nodes.map((n) => {
          const color = statusColor(n.node.status, n.node.manual);
          const canRemove = onRemove && n.node.observed;
          return (
            <g key={n.node.path || "root"} transform={`translate(${n.x}, ${n.y})`}>
              <title>
                {n.node.path || "/"}
                {n.node.status !== null ? ` — HTTP ${n.node.status}` : ""}
                {n.node.manual ? " (manual)" : ""}
              </title>
              <rect
                width={NODE_WIDTH}
                height={NODE_HEIGHT}
                rx={4}
                fill={n.node.observed ? `${color}22` : "rgba(255,255,255,0.04)"}
                stroke={n.node.observed ? color : "rgba(255,255,255,0.2)"}
                strokeWidth={1}
              />
              <text
                x={8}
                y={NODE_HEIGHT / 2 + 4}
                fontSize={11}
                fontFamily="var(--font-geist-mono), monospace"
                fill="rgba(255,255,255,0.85)"
              >
                {n.node.name.length > 16 ? `${n.node.name.slice(0, 15)}…` : n.node.name}
              </text>
              {canRemove && (
                <g
                  transform={`translate(${NODE_WIDTH - 14}, 4)`}
                  style={{ cursor: "pointer" }}
                  onClick={() => onRemove!(n.node.path)}
                >
                  <circle cx={7} cy={7} r={7} fill="rgba(239,68,68,0.15)" />
                  <text x={7} y={10.5} fontSize={10} textAnchor="middle" fill="#ef4444">
                    ×
                  </text>
                </g>
              )}
            </g>
          );
        })}
      </svg>
      {/* Real DOM tooltips (SVG <title> only shows on native hover-delay) for
          nodes that carry a status, since that's the detail worth surfacing
          fastest — the color already distinguishes open/auth-walled/other. */}
      {nodes
        .filter((n) => n.node.observed && n.node.status !== null)
        .map((n) => (
          <Tooltip key={`tip-${n.node.path}`} title={`HTTP ${n.node.status}`} placement="top">
            <Box
              sx={{
                position: "absolute",
                left: n.x,
                // Leave the top-right "×" remove circle uncovered so its
                // click still lands on the SVG element underneath.
                width: NODE_WIDTH - 18,
                top: n.y,
                height: NODE_HEIGHT,
                cursor: "default",
              }}
            />
          </Tooltip>
        ))}
      </Box>
    </Box>
  );
}
