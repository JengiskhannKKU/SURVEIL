"use client";

import { createTheme } from "@mui/material/styles";

// Terminal / hacker-console theme: near-black background, monospace
// everywhere, single mint-green accent (glow text, outlined-pill buttons).
export const GREEN = "#5eead4";
export const GREEN_LIGHT = "#99f6e4";
export const GREEN_DARK = "#2dd4bf";
export const GREEN_DIM = "#134e4a";

const MONO = "var(--font-geist-mono), ui-monospace, 'SFMono-Regular', Menlo, monospace";

export const theme = createTheme({
  palette: {
    mode: "dark",
    background: {
      default: "#000000",
      paper: "#0a0d0d",
    },
    primary: { main: GREEN, light: GREEN_LIGHT, dark: GREEN_DARK },
    secondary: { main: GREEN, light: GREEN_LIGHT, dark: GREEN_DARK },
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
    fontFamily: MONO,
    button: { textTransform: "none", fontWeight: 600, letterSpacing: 0.5 },
    h1: { fontFamily: MONO },
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
          backgroundColor: "rgba(4,6,6,0.7)",
          backdropFilter: "blur(14px)",
          borderBottom: "1px solid rgba(255,255,255,0.08)",
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: { borderRadius: 999, paddingLeft: 20, paddingRight: 20 },
        containedPrimary: {
          color: "#000",
          boxShadow: `0 0 0 1px ${GREEN}66, 0 0 16px ${GREEN}40`,
          "&:hover": {
            boxShadow: `0 0 0 1px ${GREEN}, 0 0 24px ${GREEN}66`,
          },
        },
        outlinedPrimary: {
          borderColor: `${GREEN}88`,
          "&:hover": {
            borderColor: GREEN,
            backgroundColor: `${GREEN}14`,
            boxShadow: `0 0 16px ${GREEN}33`,
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { fontWeight: 600, fontFamily: MONO },
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
          backgroundColor: "rgba(8,10,10,0.96)",
          backgroundImage: "none",
          backdropFilter: "blur(20px)",
        },
      },
    },
  },
});
