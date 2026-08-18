"use client";

import { createTheme } from "@mui/material/styles";

// Red team / blue team duotone, on a black "terminal" background.
export const RED = "#ef4444";
export const RED_DIM = "#7f1d1d";
export const BLUE = "#3b82f6";
export const BLUE_DIM = "#1e3a5f";

export const theme = createTheme({
  palette: {
    mode: "dark",
    background: {
      default: "#000000",
      paper: "#0a0b0d",
    },
    primary: { main: BLUE, light: "#60a5fa", dark: "#1d4ed8" },
    secondary: { main: RED, light: "#f87171", dark: "#b91c1c" },
    error: { main: "#dc2626" },
    warning: { main: "#f97316" },
    info: { main: "#0ea5e9" },
    success: { main: "#22c55e" },
    divider: "rgba(255,255,255,0.09)",
    text: {
      primary: "rgba(255,255,255,0.92)",
      secondary: "rgba(255,255,255,0.58)",
    },
  },
  shape: { borderRadius: 10 },
  typography: {
    fontFamily: "var(--font-geist-sans), ui-sans-serif, system-ui, sans-serif",
    button: { textTransform: "none", fontWeight: 600 },
    h1: { fontFamily: "var(--font-geist-mono), monospace" },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: { backgroundColor: "transparent" },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: "none",
          backgroundColor: "rgba(12,13,16,0.72)",
          backdropFilter: "blur(14px)",
          border: "1px solid rgba(255,255,255,0.08)",
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundImage: "none",
          backgroundColor: "rgba(6,7,9,0.75)",
          backdropFilter: "blur(14px)",
          borderBottom: "1px solid rgba(255,255,255,0.08)",
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: { borderRadius: 8 },
        containedPrimary: {
          boxShadow: `0 0 0 1px rgba(59,130,246,0.4), 0 0 16px rgba(59,130,246,0.25)`,
          "&:hover": {
            boxShadow: `0 0 0 1px rgba(59,130,246,0.6), 0 0 22px rgba(59,130,246,0.4)`,
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { fontWeight: 600 },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: { borderColor: "rgba(255,255,255,0.08)" },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          backgroundColor: "rgba(255,255,255,0.02)",
        },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          backgroundColor: "rgba(10,11,14,0.96)",
          backgroundImage: "none",
          backdropFilter: "blur(20px)",
        },
      },
    },
  },
});
