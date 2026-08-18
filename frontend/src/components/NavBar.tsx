"use client";

import Link from "next/link";
import AppBar from "@mui/material/AppBar";
import Toolbar from "@mui/material/Toolbar";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import Box from "@mui/material/Box";

export function NavBar() {
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
      </Toolbar>
    </AppBar>
  );
}
