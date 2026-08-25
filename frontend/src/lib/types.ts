export type Status = "pending" | "running" | "done" | "skipped" | "failed";

export type Severity = "critical" | "high" | "medium" | "low" | "info";

export interface Finding {
  id: string;
  checklist_item_id: string;
  title: string;
  severity: Severity;
  description: string;
  evidence: string;
  raw_output: string;
  owasp_category: string;
  cwe_id: string;
  cvss_vector: string;
  cvss_score: number;
  verified: boolean;
  remediation: string;
  tool: string;
  created_at: string;
}

export interface ChecklistItem {
  id: string;
  name: string;
  description: string;
  category: string;
  category_code: string;
  tools: string[];
  references: string[];
  status: Status;
  findings: Finding[];
  tool_outputs: Record<string, string>;
  started_at: string | null;
  completed_at: string | null;
  time_elapsed_seconds: number | null;
  owasp_ref: string;
  cwe_ids: string[];
  notes: string;
}

export interface Engagement {
  id: string;
  name: string;
  target: string;
  scope_notes: string;
  created_at: string;
  updated_at: string;
  checklist_items: ChecklistItem[];
}

export interface EngagementSummary {
  id: string;
  name: string;
  target: string;
  created_at: string;
  progress: string;
  findings: number;
  critical: number;
  high: number;
  medium: number;
}

export interface ToolInfo {
  name: string;
  description: string;
  example: string;
  uses_wordlist: boolean;
  available: boolean;
  install_hints: Record<string, string>;
  modes: Record<string, string>;
  domain_only: boolean;
}

export interface WordlistInfo {
  label: string;
  path: string;
}

export interface WordlistGroup {
  category: string;
  recommended: boolean;
  wordlists: WordlistInfo[];
}

export interface GroupedWordlists {
  recommended_category: string | null;
  recommended_category_label: string | null;
  groups: WordlistGroup[];
}

export interface RemoteWordlistInfo {
  label: string;
  path: string;
  size: number;
  downloaded: boolean;
}

export interface RemoteWordlistGroup {
  category: string;
  recommended: boolean;
  total: number;
  truncated: boolean;
  wordlists: RemoteWordlistInfo[];
}

export interface RemoteGroupedWordlists {
  recommended_category: string | null;
  recommended_category_label: string | null;
  groups: RemoteWordlistGroup[];
}

export interface AppConfig {
  wordlist_dir: string | null;
  wordlist_dir_env: string | null;
  default_wordlist: string;
  wordlists_found: number;
}

export interface RunResult {
  tool: string;
  command: string;
  exit_code: number;
  elapsed_seconds: number;
  simulated: boolean;
  success: boolean;
}

export type WsMessage =
  | { type: "line"; data: string }
  | { type: "done"; item: ChecklistItem; result: RunResult }
  | { type: "error"; message: string };
