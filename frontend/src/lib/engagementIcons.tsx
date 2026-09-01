// Fixed set of selectable icons for an engagement — picked at creation time
// (see the New Engagement dialog in app/engagements/page.tsx) so a tester
// can tell engagements apart at a glance in the dashboard grid, the same
// way each tool gets a distinct colored badge in toolLogos.ts. A curated
// set keyed by what kind of target a pentest engagement actually is (web,
// API, mobile, cloud, network, ...) rather than an open-ended icon picker —
// simpler to store (a short key, not free text) and every option is
// genuinely relevant to this app's domain.
import type { ComponentType } from "react";
import type { SvgIconProps } from "@mui/material/SvgIcon";
import LanguageIcon from "@mui/icons-material/Language";
import ApiIcon from "@mui/icons-material/Api";
import PhoneIphoneIcon from "@mui/icons-material/PhoneIphone";
import CloudIcon from "@mui/icons-material/Cloud";
import RouterIcon from "@mui/icons-material/Router";
import StorageIcon from "@mui/icons-material/Storage";
import MemoryIcon from "@mui/icons-material/Memory";
import LockIcon from "@mui/icons-material/Lock";
import ShoppingCartIcon from "@mui/icons-material/ShoppingCart";
import BusinessIcon from "@mui/icons-material/Business";
import TerminalIcon from "@mui/icons-material/Terminal";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";

export interface EngagementIconMeta {
  label: string;
  color: string;
  Icon: ComponentType<SvgIconProps>;
}

export const ENGAGEMENT_ICONS: Record<string, EngagementIconMeta> = {
  web:       { label: "Website",         color: "#5eead4", Icon: LanguageIcon },
  api:       { label: "API",             color: "#a855f7", Icon: ApiIcon },
  mobile:    { label: "Mobile app",      color: "#ec4899", Icon: PhoneIphoneIcon },
  cloud:     { label: "Cloud/infra",     color: "#3b82f6", Icon: CloudIcon },
  network:   { label: "Network",         color: "#f97316", Icon: RouterIcon },
  database:  { label: "Database",        color: "#22c55e", Icon: StorageIcon },
  iot:       { label: "IoT/embedded",    color: "#06b6d4", Icon: MemoryIcon },
  auth:      { label: "Auth/identity",   color: "#dc2626", Icon: LockIcon },
  ecommerce: { label: "E-commerce",      color: "#eab308", Icon: ShoppingCartIcon },
  corporate: { label: "Corporate/internal", color: "#8b5cf6", Icon: BusinessIcon },
  cli:       { label: "CLI/service",     color: "#14b8a6", Icon: TerminalIcon },
  other:     { label: "Other",           color: "#6b7280", Icon: HelpOutlineIcon },
};

export const DEFAULT_ENGAGEMENT_ICON = "web";

export function engagementIcon(key: string): EngagementIconMeta {
  return ENGAGEMENT_ICONS[key] ?? ENGAGEMENT_ICONS[DEFAULT_ENGAGEMENT_ICON];
}
