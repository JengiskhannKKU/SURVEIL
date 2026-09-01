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
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import StopIcon from "@mui/icons-material/Stop";
import IconButton from "@mui/material/IconButton";
import { motion } from "framer-motion";
import { api, WS_BASE } from "@/lib/api";
import { useToast } from "@/lib/toast";
import { HighlightedLine } from "@/components/HighlightedOutput";
import { InstallHints } from "@/components/InstallHints";
import { WordlistPickerDialog } from "@/components/WordlistPickerDialog";
import { ToolHelpDialog } from "@/components/ToolHelpDialog";
import { ToolLogo } from "@/components/ToolLogo";
import { isIpAddress } from "@/lib/target";
import type { ChecklistItem, ToolInfo, WsMessage } from "@/lib/types";

export function RunToolDialog({
  engagementId,
  target,
  item,
  allTools,
  onClose,
  onDone,
  onStart,
}: {
  engagementId: string;
  target: string;
  item: ChecklistItem;
  allTools: ToolInfo[];
  onClose: () => void;
  onDone: (updated: ChecklistItem) => void;
  // Fired the moment a run actually starts (the backend has accepted it and
  // is executing), so the caller can optimistically flip this item's local
  // status to "running" — the run keeps going server-side even if this
  // dialog is closed before onDone ever fires, and without this the
  // checklist sidebar/header would have no way to know that happened until
  // a full page reload re-fetches the engagement from scratch.
  onStart?: () => void;
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
  const [helpOpen, setHelpOpen] = useState(false);
  const [recommendedCategoryLabel, setRecommendedCategoryLabel] = useState<string | null>(null);
  const [nucleiTags, setNucleiTags] = useState<string | null>(null);
  const [lines, setLines] = useState<string[]>([]);
  const [running, setRunning] = useState(false);
  const [finished, setFinished] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [cancelled, setCancelled] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const outputRef = useRef<HTMLDivElement | null>(null);

  const tool = availableTools.find((t) => t.name === toolName);
  const hasModes = Object.keys(tool?.modes ?? {}).length > 0;
  const wordlistName = wordlistPath ? wordlistPath.split("/").pop() : "tool default";

  // item.status === "running" but this dialog's own `running` is still
  // false means a run was started earlier (possibly from a Run Tool
  // dialog that's since been closed) and is still executing server-side —
  // it keeps going in the background regardless of whether any dialog is
  // open to watch it. Starting a second one now would just be rejected by
  // the backend, so head that off with a clear explanation instead of a
  // raw error after the fact.
  const alreadyRunningElsewhere = item.status === "running" && !running && !finished;

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
        setNucleiTags(res.nuclei_tags);
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
    setCancelled(false);
    setRunning(true);
    let startNotified = false;

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
        // The first real line back from the server is proof the backend
        // accepted this run (a rejection — e.g. already running — arrives
        // as an "error" message instead, with no "line" ever sent) and is
        // now executing, so it's safe to tell the parent to reflect
        // "running" locally.
        if (!startNotified) {
          startNotified = true;
          onStart?.();
        }
        setLines((prev) => [...prev, msg.data]);
      } else if (msg.type === "done") {
        setRunning(false);
        setFinished(true);
        setCancelling(false);
        setCancelled(msg.result.cancelled);
        onDone(msg.item);
        if (msg.result.cancelled) {
          toast.success(`${toolName} stopped`);
        } else {
          toast.success(`${toolName} finished (${msg.result.elapsed_seconds.toFixed(1)}s)`);
        }
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

  async function stop() {
    setCancelling(true);
    try {
      await api.cancelRun(engagementId, item.id);
      // Nothing else to do here — the running subprocess gets killed
      // server-side, and this dialog's own WebSocket (if it's the one
      // watching this run) will get the resulting "done" message and flip
      // `running`/`finished` itself. If this run was started from a
      // different dialog/tab (alreadyRunningElsewhere), there's no live ws
      // here to react to — the item prop updates once the parent's polling
      // (or a reopen of this dialog) re-fetches it.
      if (alreadyRunningElsewhere) {
        toast.success(`Stopping ${toolName || "the running tool"}…`);
      }
    } catch (err) {
      setCancelling(false);
      toast.error(err instanceof Error ? err.message : "Could not stop the tool.");
    }
  }

  return (
    <Dialog open onClose={onClose} fullWidth maxWidth="md">
      <DialogTitle sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <Box>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
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
          </Box>
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ fontFamily: "var(--font-geist-mono)" }}
          >
            Target: {target}
          </Typography>
        </Box>
      </DialogTitle>
      <DialogContent>
        {alreadyRunningElsewhere && (
          <Alert
            severity="warning"
            sx={{ mt: 2, mb: 1 }}
            action={
              <Button
                color="warning"
                size="small"
                startIcon={<StopIcon fontSize="small" />}
                onClick={stop}
                disabled={cancelling}
              >
                {cancelling ? "Stopping…" : "Stop it"}
              </Button>
            }
          >
            A tool is already running on {item.id} in the background — started earlier and still
            going even though no dialog was open to watch it. Its result will land here (and in
            the checklist sidebar) once it finishes; starting another run now would be rejected —
            stop it first if you&apos;d rather run something else.
          </Alert>
        )}
        <Stack direction="row" spacing={2} flexWrap="wrap" useFlexGap alignItems="center" mb={2} mt={2}>
          <TextField
            select
            size="small"
            label="Tool"
            value={toolName}
            disabled={running}
            onChange={(e) => setToolName(e.target.value)}
            slotProps={{ select: { renderValue: (v) => String(v) } }}
            sx={{ minWidth: 160 }}
          >
            {availableTools.map((t) => (
              <MenuItem key={t.name} value={t.name} sx={{ py: 1 }}>
                <Stack direction="row" spacing={1.25} alignItems="center" sx={{ width: 320, maxWidth: "100%" }}>
                  <ToolLogo name={t.name} size={26} dim={!t.available} />
                  <Box minWidth={0} flex={1}>
                    <Typography
                      variant="body2"
                      sx={{ fontFamily: "var(--font-geist-mono)", fontWeight: 600, lineHeight: 1.3 }}
                    >
                      {t.name}
                      {!t.available && (
                        <Typography component="span" variant="caption" color="text.disabled" ml={0.75}>
                          (not installed)
                        </Typography>
                      )}
                    </Typography>
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      noWrap
                      display="block"
                      sx={{ lineHeight: 1.3 }}
                    >
                      {t.description}
                    </Typography>
                  </Box>
                </Stack>
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
            <Alert severity="info" variant="outlined" icon={<ToolLogo name={tool.name} size={22} />}>
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
            {toolName === "nuclei" && nucleiTags && (
              <Alert severity="success" variant="outlined">
                Using template tags scoped to this test —{" "}
                <strong>
                  <code>{nucleiTags}</code>
                </strong>{" "}
                — instead of nuclei&apos;s generic misconfig/exposure scan. Edit the command below
                to widen or narrow it.
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

        <Box display="flex" justifyContent="flex-end" gap={1} mb={2}>
          {tool && (
            <Button
              variant="outlined"
              size="small"
              startIcon={<HelpOutlineIcon fontSize="small" />}
              onClick={() => setHelpOpen(true)}
              title={`Show ${toolName}'s real --help output and every option it supports`}
            >
              Help
            </Button>
          )}
          {running && (
            <Button
              variant="outlined"
              color="error"
              startIcon={<StopIcon fontSize="small" />}
              onClick={stop}
              disabled={cancelling}
            >
              {cancelling ? "Stopping…" : "Stop"}
            </Button>
          )}
          <Button
            variant="contained"
            onClick={run}
            disabled={running || !toolName || alreadyRunningElsewhere}
          >
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

        {finished && !error && cancelled && (
          <Typography variant="body2" sx={{ mt: 1.5, color: "#f59e0b" }}>
            ■ Stopped — partial output saved to this item. Edit the command above (e.g. lower a
            timeout/thread flag) and hit Run again to try a faster pass.
          </Typography>
        )}
        {finished && !error && !cancelled && (
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

      {helpOpen && tool && <ToolHelpDialog tool={tool} onClose={() => setHelpOpen(false)} />}
    </Dialog>
  );
}
