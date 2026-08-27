"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import Box from "@mui/material/Box";
import Container from "@mui/material/Container";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import TerminalIcon from "@mui/icons-material/Terminal";
import BoltIcon from "@mui/icons-material/Bolt";
import ChecklistIcon from "@mui/icons-material/Checklist";
import DescriptionIcon from "@mui/icons-material/Description";
import { GREEN } from "@/lib/theme";

const FEATURES = [
  {
    icon: ChecklistIcon,
    title: "OWASP WSTG",
    body: "20 structured Information Gathering & Configuration Management items, with room to add your own.",
  },
  {
    icon: TerminalIcon,
    title: "16 integrated tools",
    body: "nmap, httpx, nuclei, ffuf, subfinder, and more — real subprocess execution, not simulated by default.",
  },
  {
    icon: BoltIcon,
    title: "Live streaming output",
    body: "Watch tool output arrive line-by-line over a WebSocket as a scan runs, with syntax highlighting.",
  },
  {
    icon: DescriptionIcon,
    title: "CVSS-scored reporting",
    body: "Findings auto-extracted where possible, CVSS v3.1 scoring, and one-click Markdown or Word reports.",
  },
];

function FadeIn({ children, delay = 0 }: { children: React.ReactNode; delay?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay, ease: "easeOut" }}
    >
      {children}
    </motion.div>
  );
}

function CornerBracket({ side }: { side: "left" | "right" }) {
  const flip = side === "right";
  return (
    <Box
      aria-hidden
      sx={{
        position: "absolute",
        top: 24,
        [side]: 24,
        width: 32,
        height: 32,
        borderTop: `2px solid ${GREEN}88`,
        ...(flip ? { borderRight: `2px solid ${GREEN}88` } : { borderLeft: `2px solid ${GREEN}88` }),
        display: { xs: "none", sm: "block" },
      }}
    />
  );
}

export default function LandingPage() {
  return (
    <Box sx={{ position: "relative", flex: 1, overflowY: "auto" }}>
      <CornerBracket side="left" />
      <CornerBracket side="right" />

      <Container maxWidth="md" sx={{ py: { xs: 8, sm: 12 } }}>
        <Stack alignItems="center" textAlign="center" spacing={2} mb={{ xs: 8, sm: 10 }}>
          <FadeIn>
            <Box
              component="img"
              src="/logo.svg"
              alt="surveil"
              width={88}
              height={88}
              sx={{ filter: `drop-shadow(0 0 16px ${GREEN}77) drop-shadow(0 0 40px ${GREEN}33)` }}
            />
          </FadeIn>

          <FadeIn delay={0.04}>
            <Typography
              sx={{
                fontFamily: "var(--font-geist-mono)",
                fontSize: 12,
                letterSpacing: 3,
                color: "text.secondary",
              }}
            >
              [ SURVEIL ]
            </Typography>
          </FadeIn>

          <FadeIn delay={0.08}>
            <Typography
              component="h1"
              sx={{
                fontFamily: "var(--font-geist-mono)",
                fontSize: { xs: 56, sm: 96 },
                fontWeight: 700,
                lineHeight: 0.95,
                letterSpacing: { xs: 0, sm: 2 },
                color: GREEN,
                textShadow: `0 0 24px ${GREEN}99, 0 0 60px ${GREEN}55`,
              }}
            >
              SURVEIL
            </Typography>
          </FadeIn>

          <FadeIn delay={0.14}>
            <Typography
              sx={{
                fontFamily: "var(--font-geist-mono)",
                fontSize: { xs: 26, sm: 38 },
                fontWeight: 700,
                letterSpacing: { xs: 1, sm: 4 },
                color: "text.primary",
              }}
            >
              PENTESTING
            </Typography>
          </FadeIn>

          <FadeIn delay={0.2}>
            <Typography
              sx={{
                fontFamily: "var(--font-geist-mono)",
                fontSize: 13,
                letterSpacing: 3,
                color: GREEN,
                opacity: 0.85,
              }}
            >
              SCAN &nbsp;·&nbsp; VERIFY &nbsp;·&nbsp; REPORT
            </Typography>
          </FadeIn>

          <FadeIn delay={0.28}>
            <Typography
              sx={{
                fontFamily: "var(--font-geist-mono)",
                fontSize: 14.5,
                lineHeight: 1.8,
                color: "text.secondary",
                maxWidth: 560,
                pt: 1,
              }}
            >
              Work the OWASP WSTG checklist with real tool execution, not guesswork.
              <br />
              Track findings, verify evidence, and generate CVSS-scored reports.
            </Typography>
          </FadeIn>

          <FadeIn delay={0.38}>
            <Button
              component={Link}
              href="/engagements"
              variant="outlined"
              color="primary"
              size="large"
              sx={{
                mt: 2,
                fontFamily: "var(--font-geist-mono)",
                fontSize: 14,
                letterSpacing: 1,
                px: 3.5,
                py: 1.4,
              }}
              endIcon={
                <motion.span
                  animate={{ opacity: [1, 0.15, 1] }}
                  transition={{ duration: 1.1, repeat: Infinity }}
                  style={{
                    display: "inline-block",
                    width: 8,
                    height: 16,
                    backgroundColor: GREEN,
                    marginLeft: 2,
                  }}
                />
              }
            >
              Open Dashboard
            </Button>
          </FadeIn>
        </Stack>

        {/* <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
            gap: 2,
          }}
        >
          {FEATURES.map((f, i) => (
            <FadeIn key={f.title} delay={0.46 + i * 0.06}>
              <Paper sx={{ p: 3, height: "100%" }}>
                <f.icon sx={{ color: GREEN, mb: 1.5 }} />
                <Typography
                  fontWeight={700}
                  mb={0.5}
                  sx={{ fontFamily: "var(--font-geist-mono)", letterSpacing: 0.5 }}
                >
                  {f.title.toUpperCase()}
                </Typography>
                <Typography variant="body2" color="text.secondary" lineHeight={1.6}>
                  {f.body}
                </Typography>
              </Paper>
            </FadeIn>
          ))}
        </Box> */}

        <FadeIn delay={0.75}>
          <Typography
            variant="body2"
            color="text.secondary"
            textAlign="center"
            mt={6}
            sx={{ fontFamily: "var(--font-geist-mono)", fontSize: 12.5 }}
          >
            Also available as a CLI and terminal UI — see{" "}
            <Typography
              component="code"
              sx={{ fontFamily: "var(--font-geist-mono)", fontSize: "0.95em", color: "text.primary" }}
            >
              README.md
            </Typography>{" "}
            for setup.
          </Typography>
        </FadeIn>
      </Container>
    </Box>
  );
}
