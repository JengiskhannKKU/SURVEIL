"use client";

import { useState } from "react";
import Link from "next/link";
import AppBar from "@mui/material/AppBar";
import Toolbar from "@mui/material/Toolbar";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Box from "@mui/material/Box";
import SettingsOutlinedIcon from "@mui/icons-material/SettingsOutlined";
import BuildOutlinedIcon from "@mui/icons-material/BuildOutlined";
import { SettingsDialog } from "@/components/SettingsDialog";
import { ToolsCatalog } from "@/components/ToolsCatalog";

export function NavBar() {
  const [showSettings, setShowSettings] = useState(false);
  const [showTools, setShowTools] = useState(false);

  return (
    <AppBar position="static" elevation={0}>
      <Toolbar sx={{ maxWidth: 1200, width: "100%", mx: "auto", px: { xs: 2, sm: 3 } }}>
        <Typography
          component={Link}
          href="/"
          sx={{
            fontFamily: "var(--font-geist-mono)",
            fontWeight: 700,
            letterSpacing: 3,
            fontSize: 14,
            color: "text.primary",
            textDecoration: "none",
            flexShrink: 0,
          }}
        >
          [ SURVEIL ]
        </Typography>
        <Box flex={1} />
        <Button
          component={Link}
          href="/engagements"
          size="small"
          sx={{ fontSize: 12.5, letterSpacing: 1 }}
        >
          DASHBOARD
        </Button>
        <IconButton
          size="small"
          onClick={() => setShowTools(true)}
          title="Tools"
          sx={{ ml: 1, color: "text.secondary" }}
        >
          <BuildOutlinedIcon fontSize="small" />
        </IconButton>
        <IconButton
          size="small"
          onClick={() => setShowSettings(true)}
          title="Settings"
          sx={{ ml: 1, color: "text.secondary" }}
        >
          <SettingsOutlinedIcon fontSize="small" />
        </IconButton>
      </Toolbar>

      {showSettings && <SettingsDialog onClose={() => setShowSettings(false)} />}
      {showTools && <ToolsCatalog onClose={() => setShowTools(false)} />}
    </AppBar>
  );
}
