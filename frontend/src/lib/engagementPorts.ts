// Aggregates open ports across every checklist item's tool output
// (nmap's table, naabu's silent "host:port" lines) into one combined
// list — the port-summary counterpart to engagementPaths.ts, backing the
// engagement page's "Ports" button.
import type { ChecklistItem, ManualPortEntry } from "./types";

export interface EngagementPortEntry {
  port: number;
  protocol: string; // "tcp" | "udp"
  service: string;
  version: string;
  tool: string;
  itemId: string | null; // null for a manually-added entry
  manual: boolean;
  note?: string;
}

// Mirrors oculus/findings_extractor.py's _INTERESTING_PORTS — the same
// "worth flagging" ports, kept in sync deliberately so a port badge in
// this summary matches what the auto-finding extractor would flag.
const SENSITIVE_PORTS: Record<number, string> = {
  21: "FTP",
  23: "Telnet (unencrypted)",
  3306: "MySQL",
  5432: "PostgreSQL",
  6379: "Redis",
  27017: "MongoDB",
  9200: "Elasticsearch",
  2375: "Docker API (unauthenticated)",
  5900: "VNC",
  3389: "RDP",
};

export function sensitivePortLabel(port: number): string | null {
  return SENSITIVE_PORTS[port] ?? null;
}

// nmap's default table output: "80/tcp   open  http      nginx 1.18.0 (Ubuntu)"
const NMAP_PORT_RE = /^(\d+)\/(tcp|udp)\s+(\S+)\s+(\S+)(?:\s+(.*))?$/;

function normalizeKey(port: number, protocol: string): string {
  return `${port}/${protocol}`;
}

export function collectEngagementPorts(
  items: ChecklistItem[],
  manualPorts: ManualPortEntry[] = [],
  removedPorts: string[] = []
): EngagementPortEntry[] {
  const removed = new Set(removedPorts);
  const byKey = new Map<string, EngagementPortEntry>();

  for (const item of items) {
    for (const [tool, output] of Object.entries(item.tool_outputs)) {
      for (const raw of output.split("\n")) {
        const line = raw.trim();

        const nmapMatch = line.match(NMAP_PORT_RE);
        if (nmapMatch) {
          const [, portStr, protocol, state, service, version] = nmapMatch;
          if (!state.startsWith("open")) continue;
          const port = Number(portStr);
          const key = normalizeKey(port, protocol);
          if (removed.has(key)) continue;
          const existing = byKey.get(key);
          if (!existing || (version && !existing.version)) {
            byKey.set(key, {
              port,
              protocol,
              service,
              version: version ?? "",
              tool,
              itemId: item.id,
              manual: false,
            });
          }
          continue;
        }

        // naabu's real `-silent` output (and this app's own mock_output())
        // is just a bare "host:port" line, one per open port — no
        // protocol/service/version at all. Gated to naabu specifically,
        // same reasoning as pathTree.ts's tool-gated fallbacks: a bare
        // "word:number" shape is too generic to assume elsewhere.
        if (tool === "naabu") {
          const naabuMatch = line.match(/^\S+:(\d+)$/);
          if (naabuMatch) {
            const port = Number(naabuMatch[1]);
            const key = normalizeKey(port, "tcp");
            if (removed.has(key)) continue;
            if (!byKey.has(key)) {
              byKey.set(key, {
                port,
                protocol: "tcp",
                service: "",
                version: "",
                tool,
                itemId: item.id,
                manual: false,
              });
            }
          }
        }
      }
    }
  }

  for (const m of manualPorts) {
    const key = normalizeKey(m.port, m.protocol);
    if (removed.has(key)) continue;
    byKey.set(key, {
      port: m.port,
      protocol: m.protocol,
      service: m.service,
      version: "",
      tool: "manual",
      itemId: null,
      manual: true,
      note: m.note,
    });
  }

  return Array.from(byKey.values()).sort((a, b) => a.port - b.port);
}
