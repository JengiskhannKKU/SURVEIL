"use client";

import { useEffect, useMemo, useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import Button from "@mui/material/Button";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api } from "@/lib/api";
import { GREEN, GREEN_LIGHT } from "@/lib/theme";

// The report is one long markdown string with top-level "## " sections
// (see oculus/report.py: Executive Summary, Checklist Coverage,
// Detailed Findings, Appendix — Raw Tool Output). Splitting it client-side
// and rendering each as a collapsible Accordion — rather than one
// unbroken scroll — is what actually makes a 97-item checklist + a raw
// tool-output appendix "easier to read": the long, skimmable-only-once
// sections collapse out of the way by default, and the two sections a
// tester actually opens this for (the summary and the findings
// themselves) stay expanded.
interface ReportSection {
  title: string;
  body: string;
}

function splitIntoSections(markdown: string): ReportSection[] {
  const lines = markdown.split("\n");
  const sections: ReportSection[] = [];
  let currentTitle = "Overview";
  let currentLines: string[] = [];

  for (const line of lines) {
    const match = /^##\s+(.+)$/.exec(line);
    if (match) {
      sections.push({ title: currentTitle, body: currentLines.join("\n").trim() });
      currentTitle = match[1].trim();
      currentLines = [];
    } else {
      currentLines.push(line);
    }
  }
  sections.push({ title: currentTitle, body: currentLines.join("\n").trim() });

  return sections.filter((s) => s.body.length > 0);
}

// Sections collapsed by default — the two genuinely long ones a tester
// skims once rather than reads (the full checklist and raw tool logs).
// Everything else (Overview, Executive Summary, Detailed Findings)
// starts expanded, since that's the "what did we find" a tester opens
// this dialog to see.
const COLLAPSED_BY_DEFAULT = new Set(["Checklist Coverage", "Appendix — Raw Tool Output"]);

const SEVERITY_BORDER: Record<string, string> = {
  "🔴": "#ef4444",
  "🟠": "#f97316",
  "🟡": "#eab308",
  "🔵": "#3b82f6",
  "⚪": "rgba(255,255,255,0.25)",
};

function textOf(node: React.ReactNode): string {
  if (typeof node === "string") return node;
  if (Array.isArray(node)) return node.map(textOf).join("");
  if (node && typeof node === "object" && "props" in node) {
    return textOf((node as { props: { children?: React.ReactNode } }).props.children);
  }
  return "";
}

// Custom renderers so the report reads like the rest of this app's
// terminal/hacker-console theme instead of react-markdown's plain
// browser-default styling.
const MARKDOWN_COMPONENTS = {
  h1: (props: React.ComponentProps<"h1">) => (
    <Typography
      variant="h5"
      fontWeight={700}
      sx={{ fontFamily: "var(--font-geist-mono)", color: GREEN, mt: 0, mb: 1.5 }}
      {...props}
    />
  ),
  h3: (props: React.ComponentProps<"h3">) => {
    const text = textOf(props.children);
    const emoji = Object.keys(SEVERITY_BORDER).find((e) => text.startsWith(e));
    const borderColor = emoji ? SEVERITY_BORDER[emoji] : "divider";
    return (
      <Box
        sx={{
          mt: 2.5,
          mb: 1.5,
          pl: 1.5,
          py: 0.5,
          borderLeft: "3px solid",
          borderColor,
        }}
      >
        <Typography
          variant="subtitle1"
          fontWeight={700}
          sx={{ fontFamily: "var(--font-geist-mono)" }}
          {...props}
        />
      </Box>
    );
  },
  h4: (props: React.ComponentProps<"h4">) => (
    <Typography
      variant="subtitle2"
      fontWeight={700}
      sx={{ fontFamily: "var(--font-geist-mono)", color: GREEN_LIGHT, mt: 2, mb: 0.75 }}
      {...props}
    />
  ),
  p: (props: React.ComponentProps<"p">) => (
    <Typography variant="body2" sx={{ mb: 1.5, lineHeight: 1.7 }} {...props} />
  ),
  hr: () => <Box sx={{ borderTop: "1px solid", borderColor: "divider", my: 2.5 }} />,
  a: (props: React.ComponentProps<"a">) => (
    <Box component="a" sx={{ color: GREEN, textDecoration: "underline" }} {...props} />
  ),
  code: ({ className, ...props }: React.ComponentProps<"code"> & { className?: string }) => {
    const isBlock = Boolean(className); // react-markdown sets a language- class on fenced blocks
    return isBlock ? (
      <Box
        component="code"
        className={className}
        sx={{ fontFamily: "var(--font-geist-mono)", fontSize: 12.5, display: "block" }}
        {...props}
      />
    ) : (
      <Box
        component="code"
        sx={{
          fontFamily: "var(--font-geist-mono)",
          fontSize: 12.5,
          bgcolor: "rgba(255,255,255,0.06)",
          px: 0.6,
          py: 0.1,
          borderRadius: 0.5,
        }}
        {...props}
      />
    );
  },
  pre: (props: React.ComponentProps<"pre">) => (
    <Box
      component="pre"
      sx={{
        m: 0,
        mb: 1.5,
        p: 1.5,
        borderRadius: 1,
        bgcolor: "#000",
        border: "1px solid rgba(255,255,255,0.08)",
        maxHeight: 320,
        overflow: "auto",
        color: "rgba(255,255,255,0.85)",
      }}
      {...props}
    />
  ),
  table: (props: React.ComponentProps<"table">) => (
    <Box sx={{ overflowX: "auto", mb: 2, maxHeight: 420, overflowY: "auto" }}>
      <Box
        component="table"
        sx={{
          width: "100%",
          borderCollapse: "collapse",
          fontSize: 13,
          "& th, & td": {
            border: "1px solid",
            borderColor: "divider",
            px: 1.25,
            py: 0.75,
            textAlign: "left",
          },
          "& th": {
            fontFamily: "var(--font-geist-mono)",
            color: "text.secondary",
            bgcolor: "rgba(255,255,255,0.03)",
            position: "sticky",
            top: 0,
          },
        }}
        {...props}
      />
    </Box>
  ),
  li: (props: React.ComponentProps<"li">) => (
    <Typography component="li" variant="body2" sx={{ mb: 0.5, lineHeight: 1.6 }} {...props} />
  ),
};

function Section({ section, defaultExpanded }: { section: ReportSection; defaultExpanded: boolean }) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  // A rough count so a collapsed section still communicates its size
  // ("97 rows", "12 tool outputs") without opening it — counts markdown
  // table rows / "###"/"####" sub-headings, whichever the section has.
  const itemCount = useMemo(() => {
    const rows = section.body.match(/^\|.+\|$/gm)?.length ?? 0;
    const headings = section.body.match(/^#{3,4}\s/gm)?.length ?? 0;
    return Math.max(rows > 2 ? rows - 2 : 0, headings); // -2 for a table's header+separator rows
  }, [section.body]);

  return (
    <Accordion
      expanded={expanded}
      onChange={(_, isExpanded) => setExpanded(isExpanded)}
      disableGutters
      sx={{
        bgcolor: "transparent",
        "&:before": { display: "none" },
        border: "1px solid",
        borderColor: "divider",
        borderRadius: "8px !important",
        mb: 1.5,
        overflow: "hidden",
      }}
    >
      <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ px: 2 }}>
        <Stack direction="row" spacing={1.5} alignItems="center">
          <Typography
            variant="subtitle1"
            fontWeight={700}
            sx={{ fontFamily: "var(--font-geist-mono)" }}
          >
            {section.title}
          </Typography>
          {itemCount > 0 && <Chip label={itemCount} size="small" variant="outlined" />}
        </Stack>
      </AccordionSummary>
      <AccordionDetails sx={{ px: 2, pt: 0, pb: 2 }}>
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={MARKDOWN_COMPONENTS}>
          {section.body}
        </ReactMarkdown>
      </AccordionDetails>
    </Accordion>
  );
}

export function ReportView({
  engagementId,
  onClose,
}: {
  engagementId: string;
  onClose: () => void;
}) {
  const [content, setContent] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    api
      .getReportContent(engagementId)
      .then((res) => {
        if (!cancelled) setContent(res.content);
      })
      .catch(() => {
        if (!cancelled) setError("Could not load the report.");
      });
    return () => {
      cancelled = true;
    };
  }, [engagementId]);

  const sections = useMemo(() => (content ? splitIntoSections(content) : []), [content]);

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="lg" scroll="paper">
      <DialogTitle>Report</DialogTitle>
      <DialogContent dividers sx={{ bgcolor: "background.default" }}>
        {!content && !error && (
          <Stack alignItems="center" py={6}>
            <CircularProgress size={28} />
          </Stack>
        )}
        {error && (
          <Typography color="error" variant="body2">
            {error}
          </Typography>
        )}
        {sections.map((section) => (
          <Section
            key={section.title}
            section={section}
            defaultExpanded={!COLLAPSED_BY_DEFAULT.has(section.title)}
          />
        ))}
      </DialogContent>
      <DialogActions sx={{ px: 3, py: 1.5 }}>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}
