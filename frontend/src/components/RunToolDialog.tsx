"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { api, WS_BASE } from "@/lib/api";
import { useToast } from "@/lib/toast";
import { HighlightedLine } from "@/components/HighlightedOutput";
import type { ChecklistItem, ToolInfo, WordlistInfo, WsMessage } from "@/lib/types";

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
  const [command, setCommand] = useState("");
  const [defaultCommand, setDefaultCommand] = useState("");
  const [wordlists, setWordlists] = useState<WordlistInfo[]>([]);
  const [wordlistPath, setWordlistPath] = useState("");
  const [lines, setLines] = useState<string[]>([]);
  const [running, setRunning] = useState(false);
  const [finished, setFinished] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const outputRef = useRef<HTMLDivElement | null>(null);

  const tool = availableTools.find((t) => t.name === toolName);

  useEffect(() => {
    if (!toolName) return;
    api.previewCommand(toolName, target, fast).then((res) => {
      const cmd = res.command.join(" ");
      setCommand(cmd);
      setDefaultCommand(cmd);
    });
    if (tool?.uses_wordlist) {
      api.listWordlists().then(setWordlists);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [toolName, fast, target]);

  useEffect(() => {
    outputRef.current?.scrollTo({ top: outputRef.current.scrollHeight });
  }, [lines]);

  useEffect(() => {
    return () => wsRef.current?.close();
  }, []);

  useEffect(() => {
    function handler(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  function applyWordlist(path: string) {
    setWordlistPath(path);
    if (!path) return;
    setCommand((prev) => {
      if (/-w\s+\S+/.test(prev)) return prev.replace(/-w\s+\S+/, `-w ${path}`);
      return `${prev} -w ${path}`;
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
      const isDefault = command.trim() === defaultCommand.trim();
      ws.send(
        JSON.stringify({
          tool: toolName,
          fast,
          custom_command: isDefault ? null : command,
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
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-lg bg-background shadow-xl border border-neutral-200 dark:border-neutral-800">
        <div className="flex items-center justify-between border-b border-neutral-200 px-5 py-3 dark:border-neutral-800">
          <h2 className="font-semibold">
            Run tool — {item.id}
            {running && (
              <span className="ml-2 inline-flex items-center gap-1 text-xs font-normal text-amber-500">
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-500" />
                running
              </span>
            )}
          </h2>
          <button onClick={onClose} className="text-neutral-500 hover:text-foreground">
            ✕
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4">
          <div className="mb-3 flex flex-wrap items-center gap-3">
            <label className="flex flex-col gap-1 text-sm">
              Tool
              <select
                value={toolName}
                onChange={(e) => setToolName(e.target.value)}
                disabled={running}
                className="rounded border border-neutral-300 bg-transparent px-2 py-1 dark:border-neutral-700"
              >
                {availableTools.map((t) => (
                  <option key={t.name} value={t.name}>
                    {t.name}
                  </option>
                ))}
              </select>
            </label>

            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={fast}
                disabled={running}
                onChange={(e) => setFast(e.target.checked)}
              />
              Fast scan
            </label>

            {tool?.uses_wordlist && (
              <label className="flex flex-col gap-1 text-sm">
                Wordlist
                <select
                  value={wordlistPath}
                  disabled={running}
                  onChange={(e) => applyWordlist(e.target.value)}
                  className="rounded border border-neutral-300 bg-transparent px-2 py-1 dark:border-neutral-700"
                >
                  <option value="">tool default</option>
                  {wordlists.map((w) => (
                    <option key={w.path} value={w.path}>
                      {w.label}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </div>

          {tool && (
            <p className="mb-3 rounded bg-neutral-100 px-3 py-2 text-xs text-neutral-600 dark:bg-neutral-900 dark:text-neutral-400">
              {tool.description}
              <br />
              <span className="font-mono">{tool.example}</span>
            </p>
          )}

          <label className="mb-1 block text-sm">Command</label>
          <div className="mb-1 flex gap-2">
            <input
              value={command}
              disabled={running}
              onChange={(e) => setCommand(e.target.value)}
              className="flex-1 rounded border border-neutral-300 bg-transparent px-2 py-1 font-mono text-sm outline-none focus:border-neutral-500 dark:border-neutral-700"
            />
            <button
              onClick={copyCommand}
              className="rounded border border-neutral-300 px-2 py-1 text-xs hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-900"
            >
              {copied ? "Copied" : "Copy"}
            </button>
            <button
              onClick={resetCommand}
              disabled={running}
              className="rounded border border-neutral-300 px-2 py-1 text-xs hover:bg-neutral-100 disabled:opacity-50 dark:border-neutral-700 dark:hover:bg-neutral-900"
            >
              Reset
            </button>
          </div>

          <div className="mb-3 flex justify-end">
            <button
              onClick={run}
              disabled={running || !toolName}
              className="rounded-md bg-foreground px-4 py-1.5 text-sm font-medium text-background transition hover:opacity-90 disabled:opacity-50"
            >
              {running ? "Running…" : "Run"}
            </button>
          </div>

          {error && (
            <p className="mb-3 rounded bg-red-100 px-3 py-2 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
              {error}
            </p>
          )}

          <div
            ref={outputRef}
            className="h-64 overflow-y-auto rounded bg-black px-3 py-2 font-mono text-xs leading-relaxed text-neutral-300"
          >
            {lines.length === 0 ? (
              <span className="text-neutral-500">Output will stream here…</span>
            ) : (
              lines.map((l, i) => <HighlightedLine key={i} line={l} />)
            )}
          </div>

          {finished && !error && (
            <p className="mt-3 text-sm text-emerald-600 dark:text-emerald-400">
              ✓ Done — output saved to this item.
            </p>
          )}
        </div>

        <div className="border-t border-neutral-200 px-5 py-3 text-right dark:border-neutral-800">
          <button
            onClick={onClose}
            className="rounded-md border border-neutral-300 px-4 py-1.5 text-sm transition hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-900"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
