// Testing strategy/methodology chosen at engagement creation — decides
// which checklist gets built (see backend/routers/engagements.py's
// _CHECKLIST_BUILDERS / oculus/checklist.py's build_checklist() vs.
// build_oscp_checklist()). Only consulted at creation time, not re-applied
// afterward.
import type { ComponentType } from "react";
import type { SvgIconProps } from "@mui/material/SvgIcon";
import SecurityIcon from "@mui/icons-material/Security";
import TerminalIcon from "@mui/icons-material/Terminal";
import TuneIcon from "@mui/icons-material/Tune";

export interface MethodologyMeta {
  label: string;
  description: string;
  Icon: ComponentType<SvgIconProps>;
  color: string;
}

export const METHODOLOGIES: Record<string, MethodologyMeta> = {
  wstg: {
    label: "OWASP WSTG",
    description: "The full 97-item OWASP Web Security Testing Guide v4.2 checklist.",
    Icon: SecurityIcon,
    color: "#5eead4",
  },
  oscp: {
    label: "OSCP-style",
    description:
      "OSCP/PEN-200-style engagement.",
    Icon: TerminalIcon,
    color: "#f97316",
  },
  other: {
    label: "Other / Custom",
    description:
      "Any other methodology. Builds the same OWASP WSTG checklist as a starting point — add " +
      "or remove checklist items freely to match your own strategy.",
    Icon: TuneIcon,
    color: "#a855f7",
  },
};

export const DEFAULT_METHODOLOGY = "wstg";

export function methodologyLabel(key: string): string {
  return METHODOLOGIES[key]?.label ?? key;
}
