"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import Stack from "@mui/material/Stack";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import TextField from "@mui/material/TextField";
import MenuItem from "@mui/material/MenuItem";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import Typography from "@mui/material/Typography";
import Alert from "@mui/material/Alert";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import CheckIcon from "@mui/icons-material/Check";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import ListAltIcon from "@mui/icons-material/ListAlt";
import IconButton from "@mui/material/IconButton";
import { motion } from "framer-motion";
import { api, WS_BASE } from "@/lib/api";
import { useToast } from "@/lib/toast";
import { HighlightedLine } from "@/components/HighlightedOutput";
import { InstallHints } from "@/components/InstallHints";
import { WordlistPickerDialog } from "@/components/WordlistPickerDialog";
import { isIpAddress } from "@/lib/target";
import type { ChecklistItem, ToolInfo, WsMessage } from "@/lib/types";

export function RunToolDialog({
  engagementId,
  target,
  item,
  allTools,
  onClose,
  onDone,
}: {
  engagementId: string;
  target: string;
  item: ChecklistItem;
  allTools: ToolInfo[];
  onClose: () => void;
  onDone: (updated: ChecklistItem) => void;
}) {
  const toast = useToast();
  const availableTools = useMemo(
    () => allTools.filter((t) => item.tools.includes(t.name)),
    [allTools, item.tools]
  );
  const [toolName, setToolName] = useState(availableTools[0]?.name ?? "");
  const [fast, setFast] = useState(false);
  const [mode, setMode] = useState("full");
  const [command, setCommand] = useState("");
  const [defaultCommand, setDefaultCommand] = useState("");
  const [wordlistPath, setWordlistPath] = useState("");
  const [wordlistPickerOpen, setWordlistPickerOpen] = useState(false);
  const [recommendedCategoryLabel, setRecommendedCategoryLabel] = useState<string | null>(null);
  const [lines, setLines] = useState<string[]>([]);
  const [running, setRunning] = useState(false);
  const [finished, setFinished] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const outputRef = useRef<HTMLDivElement | null>(null);

  const tool = availableTools.find((t) => t.name === toolName);
  const hasModes = Object.keys(tool?.modes ?? {}).length > 0;
  const wordlistName = wordlistPath ? wordlistPath.split("/").pop() : "tool default";

  // Switching tools resets the mode to "full" so a stale mode key from a
  // previous tool (e.g. nmap's "udp") never leaks into one without it.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- resetting local UI state when the selected tool changes
    setMode("full");
  }, [toolName]);

  useEffect(() => {
    if (!toolName) return;
    api
      .previewCommand(toolName, target, fast, hasModes ? mode : undefined, item.id)
      .then((res) => {
        const cmd = res.command.join(" ");
        setCommand(cmd);
        setDefaultCommand(cmd);
        setRecommendedCategoryLabel(res.recommended_category_label);
      })
      .catch(() => toast.error("Could not reach the backend to preview the command."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [toolName, fast, hasModes, mode, target]);

  useEffect(() => {
    outputRef.current?.scrollTo({ top: outputRef.current.scrollHeight });
  }, [lines]);

  useEffect(() => {
    return () => wsRef.current?.close();
  }, []);

  function applyWordlist(path: string) {
    setWordlistPath(path);
    // Empty path ("use tool default") reverts to whatever wordlist the
    // recommendation/backend preview already put in defaultCommand, rather
    // than leaving the previously-picked -w value in place.
    const target = path || defaultCommand.match(/-w\s+(\S+)/)?.[1];
    if (!target) return;
    setCommand((prev) => {
      if (/-w\s+\S+/.test(prev)) return prev.replace(/-w\s+\S+/, `-w ${target}`);
      return `${prev} -w ${target}`;
    });
  }

  function resetCommand() {
    setCommand(defaultCommand);
    setWordlistPath("");
  }

  function copyCommand() {
    navigator.clipboard?.writeText(command);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  function run() {
    setLines([]);
    setError("");
    setFinished(false);
    setRunning(true);

    const ws = new WebSocket(
      `${WS_BASE}/ws/engagements/${engagementId}/items/${item.id}/run`
    );
    wsRef.current = ws;

    ws.onopen = () => {
      // A named scan mode (e.g. nmap's "UDP scan") has no simulated-output
      // equivalent that would actually reflect it, so always run it for
      // real rather than falling back to the generic simulated demo data
      // for tools without the binary installed. Plain Fast/Full keeps the
      // existing behavior: unedited default command -> `fast` flag (so a
      // missing binary still falls back to simulated output).
      const isDefault = command.trim() === defaultCommand.trim();
      ws.send(
        JSON.stringify({
          tool: toolName,
          fast,
          custom_command: hasModes || !isDefault ? command : null,
        })
      );
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data) as WsMessage;
      if (msg.type === "line") {
        setLines((prev) => [...prev, msg.data]);
      } else if (msg.type === "done") {
        setRunning(false);
        setFinished(true);
        onDone(msg.item);
        toast.success(`${toolName} finished (${msg.result.elapsed_seconds.toFixed(1)}s)`);
      } else if (msg.type === "error") {
        setRunning(false);
        setFinished(true);
        setError(msg.message);
        toast.error(`${toolName} failed`);
      }
    };

    ws.onerror = () => {
      setRunning(false);
      setError("WebSocket connection failed.");
      toast.error("WebSocket connection failed");
    };
  }

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="md">
      <DialogTitle sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        Run tool — {item.id}
        {running && (
          <Stack direction="row" spacing={0.75} alignItems="center">
            <motion.div
              animate={{ opacity: [1, 0.3, 1] }}
              transition={{ duration: 1.2, repeat: Infinity }}
              style={{ width: 7, height: 7, borderRadius: "50%", backgroundColor: "#f59e0b" }}
            />
            <Typography variant="caption" sx={{ color: "#f59e0b", fontWeight: 600 }}>
              running
            </Typography>
          </Stack>
        )}
      </DialogTitle>
      <DialogContent>
        <Stack direction="row" spacing={2} flexWrap="wrap" useFlexGap alignItems="center" mb={2} mt={2}>
          <TextField
            select
            size="small"
            label="Tool"
            value={toolName}
            disabled={running}
            onChange={(e) => setToolName(e.target.value)}
            sx={{ minWidth: 140 }}
          >
            {availableTools.map((t) => (
              <MenuItem key={t.name} value={t.name}>
                {t.name}
                {!t.available && (
                  <Typography component="span" variant="caption" color="text.disabled" ml={0.75}>
                    (not installed)
                  </Typography>
                )}
              </MenuItem>
            ))}
          </TextField>

          {hasModes ? (
            <TextField
              select
              size="small"
              label="Scan mode"
              value={mode}
              disabled={running}
              onChange={(e) => setMode(e.target.value)}
              sx={{ minWidth: 240 }}
            >
              {Object.entries(tool!.modes).map(([key, label]) => (
                <MenuItem key={key} value={key}>
                  {label}
                </MenuItem>
              ))}
            </TextField>
          ) : (
            <FormControlLabel
              control={
                <Switch
                  checked={fast}
                  disabled={running}
                  onChange={(e) => setFast(e.target.checked)}
                />
              }
              label="Fast scan"
            />
          )}

          {tool?.uses_wordlist && (
            <Button
              variant="outlined"
              size="small"
              disabled={running}
              startIcon={<ListAltIcon fontSize="small" />}
              onClick={() => setWordlistPickerOpen(true)}
              sx={{
                textTransform: "none",
                fontFamily: "var(--font-geist-mono)",
                fontSize: 13,
                maxWidth: 280,
              }}
            >
              <Box component="span" sx={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                Wordlist: {wordlistName}
              </Box>
            </Button>
          )}
        </Stack>

        {tool && (
          <Stack spacing={1.5} mb={2}>
            <Alert severity="info" variant="outlined">
              {tool.description}
              <br />
              <Typography component="span" sx={{ fontFamily: "var(--font-geist-mono)", fontSize: 12 }}>
                {tool.example}
              </Typography>
            </Alert>
            {!tool.available && (
              <InstallHints toolName={tool.name} hints={tool.install_hints} />
            )}
            {tool.uses_wordlist && recommendedCategoryLabel && wordlistPath === "" && (
              <Alert severity="success" variant="outlined">
                Using a wordlist recommended for this test —{" "}
                <strong>{recommendedCategoryLabel}</strong>. Pick a different one from the
                Wordlist dropdown above to override.
              </Alert>
            )}
            {tool.domain_only && isIpAddress(target) && (
              <Alert severity="warning" variant="outlined">
                <strong>{tool.name}</strong> does subdomain/DNS enumeration against a{" "}
                <em>domain name</em> — it can&apos;t enumerate subdomains of an IP address like{" "}
                <code>{target}</code>. It will run successfully but return nothing. Use it against
                a hostname instead, or pick a different tool for this target.
              </Alert>
            )}
            {hasModes && (mode === "os_detect" || mode === "aggressive") && (
              <Alert severity="warning" variant="outlined">
                OS detection (<code>-O</code>) typically needs root/administrator privileges —
                run the backend with elevated permissions, or this scan may fail/skip that part.
              </Alert>
            )}
          </Stack>
        )}

        <Typography variant="body2" mb={0.5}>
          Command
        </Typography>
        <Stack direction="row" spacing={1} mb={2}>
          <TextField
            fullWidth
            size="small"
            value={command}
            disabled={running}
            onChange={(e) => setCommand(e.target.value)}
            slotProps={{ input: { sx: { fontFamily: "var(--font-geist-mono)", fontSize: 13 } } }}
          />
          <IconButton onClick={copyCommand} title="Copy command" sx={{ border: "1px solid", borderColor: "divider" }}>
            {copied ? <CheckIcon fontSize="small" color="success" /> : <ContentCopyIcon fontSize="small" />}
          </IconButton>
          <IconButton
            onClick={resetCommand}
            disabled={running}
            title="Reset to default"
            sx={{ border: "1px solid", borderColor: "divider" }}
          >
            <RestartAltIcon fontSize="small" />
          </IconButton>
        </Stack>

        <Box display="flex" justifyContent="flex-end" mb={2}>
          <Button variant="contained" onClick={run} disabled={running || !toolName}>
            {running ? "Running…" : "Run"}
          </Button>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Box
          ref={outputRef}
          sx={{
            height: 280,
            overflowY: "auto",
            borderRadius: 1,
            bgcolor: "#000",
            border: "1px solid rgba(255,255,255,0.08)",
            px: 1.5,
            py: 1,
            fontFamily: "var(--font-geist-mono), monospace",
            fontSize: 12,
            lineHeight: 1.6,
            color: "rgba(255,255,255,0.8)",
          }}
        >
          {lines.length === 0 ? (
            <Typography variant="caption" color="text.disabled">
              Output will stream here…
            </Typography>
          ) : (
            lines.map((l, i) => <HighlightedLine key={i} line={l} />)
          )}
        </Box>

        {finished && !error && (
          <Typography variant="body2" sx={{ mt: 1.5, color: "#22c55e" }}>
            ✓ Done — output saved to this item.
          </Typography>
        )}
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2.5 }}>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>

      {wordlistPickerOpen && (
        <WordlistPickerDialog
          itemId={item.id}
          currentPath={wordlistPath}
          onClose={() => setWordlistPickerOpen(false)}
          onSelect={(path) => {
            applyWordlist(path);
            setWordlistPickerOpen(false);
          }}
        />
      )}
    </Dialog>
  );
}
