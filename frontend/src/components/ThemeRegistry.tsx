"use client";

import { AppRouterCacheProvider } from "@mui/material-nextjs/v16-appRouter";
import { ThemeProvider } from "@mui/material/styles";
import CssBaseline from "@mui/material/CssBaseline";
import Box from "@mui/material/Box";
import { theme } from "@/lib/theme";
import { GridBackground } from "@/components/GridBackground";
import { NavBar } from "@/components/NavBar";
import { ToastProvider } from "@/lib/toast";

export function ThemeRegistry({ children }: { children: React.ReactNode }) {
  return (
    <AppRouterCacheProvider options={{ key: "mui" }}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <GridBackground />
        <ToastProvider>
          <Box sx={{ height: "100dvh", display: "flex", flexDirection: "column" }}>
            <NavBar />
            <Box sx={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
              {children}
            </Box>
          </Box>
        </ToastProvider>
      </ThemeProvider>
    </AppRouterCacheProvider>
  );
}
