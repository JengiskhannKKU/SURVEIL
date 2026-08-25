"use client";

import { useEffect, useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import Button from "@mui/material/Button";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api } from "@/lib/api";
import { GREEN, GREEN_LIGHT } from "@/lib/theme";

// Custom renderers so the report reads like the rest of this app's
// terminal/hacker-console theme instead of react-markdown's plain
// browser-default styling.
const MARKDOWN_COMPONENTS = {
  h1: (props: React.ComponentProps<"h1">) => (
    <Typography
      variant="h5"
      fontWeight={700}
      sx={{ fontFamily: "var(--font-geist-mono)", color: GREEN, mt: 3, mb: 1.5 }}
      {...props}
    />
  ),
  h2: (props: React.ComponentProps<"h2">) => (
    <Typography
      variant="h6"
      fontWeight={700}
      sx={{
        fontFamily: "var(--font-geist-mono)",
        mt: 3,
        mb: 1.5,
        pb: 0.75,
        borderBottom: "1px solid",
        borderColor: "divider",
      }}
      {...props}
    />
  ),
  h3: (props: React.ComponentProps<"h3">) => (
    <Typography
      variant="subtitle1"
      fontWeight={700}
      sx={{ fontFamily: "var(--font-geist-mono)", mt: 2.5, mb: 1 }}
      {...props}
    />
  ),
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
        overflowX: "auto",
        color: "rgba(255,255,255,0.85)",
      }}
      {...props}
    />
  ),
  table: (props: React.ComponentProps<"table">) => (
    <Box sx={{ overflowX: "auto", mb: 2 }}>
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

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="md" scroll="paper">
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
        {content && (
          <Box sx={{ "& > *:first-of-type": { mt: 0 } }}>
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={MARKDOWN_COMPONENTS}>
              {content}
            </ReactMarkdown>
          </Box>
        )}
      </DialogContent>
      <DialogActions sx={{ px: 3, py: 1.5 }}>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}
