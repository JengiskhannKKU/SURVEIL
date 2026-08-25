"use client";

import { useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import Button from "@mui/material/Button";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import { ToolLogo } from "@/components/ToolLogo";
import { ToolHelpDialog } from "@/components/ToolHelpDialog";
import type { ToolInfo } from "@/lib/types";

// Lets a tester see what every tool mapped to this checklist item actually
// does — and each one's full real --help output — before opening the Run
// Tool dialog and committing to a specific tool/command. Scoped to just
// this item's tools (item.tools), unlike the nav bar's full 18-tool
// ToolsCatalog.
export function ItemToolsHelpDialog({
  tools,
  onClose,
}: {
  tools: ToolInfo[];
  onClose: () => void;
}) {
  const [helpTool, setHelpTool] = useState<ToolInfo | null>(null);

  return (
    <>
      <Dialog open onClose={onClose} fullWidth maxWidth="sm">
        <DialogTitle>
          Tools for this test
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.25 }}>
            What each tool does, and its real command-line options
          </Typography>
        </DialogTitle>
        <DialogContent dividers sx={{ bgcolor: "background.default" }}>
          <Stack spacing={1.5}>
            {tools.map((tool) => (
              <Box
                key={tool.name}
                sx={{
                  border: "1px solid",
                  borderColor: "divider",
                  borderRadius: 1.5,
                  p: 1.5,
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 1.5,
                }}
              >
                <ToolLogo name={tool.name} size={30} dim={!tool.available} />
                <Box flex={1} minWidth={0}>
                  <Stack direction="row" spacing={1} alignItems="center" mb={0.25}>
                    <Typography
                      variant="subtitle2"
                      fontWeight={700}
                      sx={{ fontFamily: "var(--font-geist-mono)" }}
                    >
                      {tool.name}
                    </Typography>
                    <Chip
                      label={tool.available ? "installed" : "not installed"}
                      size="small"
                      color={tool.available ? "success" : "default"}
                      variant={tool.available ? "filled" : "outlined"}
                      sx={{ height: 18, fontSize: 10 }}
                    />
                  </Stack>
                  <Typography variant="body2" color="text.secondary">
                    {tool.description}
                  </Typography>
                </Box>
                <Button
                  size="small"
                  variant="outlined"
                  startIcon={<HelpOutlineIcon fontSize="small" />}
                  onClick={() => setHelpTool(tool)}
                  sx={{ flexShrink: 0, whiteSpace: "nowrap" }}
                >
                  Options
                </Button>
              </Box>
            ))}
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, py: 1.5 }}>
          <Button onClick={onClose}>Close</Button>
        </DialogActions>
      </Dialog>

      {helpTool && <ToolHelpDialog tool={helpTool} onClose={() => setHelpTool(null)} />}
    </>
  );
}
