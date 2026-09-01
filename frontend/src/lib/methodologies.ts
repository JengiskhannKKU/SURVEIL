// Testing strategy/methodology chosen at engagement creation. Every
// option currently builds the exact same real OWASP WSTG checklist
// underneath (oculus/checklist.py's build_checklist()) — this is a tag
// stored on the engagement for now, not yet a different checklist
// generator. A genuine distinct OSCP-style checklist needs its own
// properly-sourced content rather than a guessed one, so it's a
// deliberate follow-up, not part of this feature.
export interface MethodologyMeta {
  label: string;
  description: string;
}

export const METHODOLOGIES: Record<string, MethodologyMeta> = {
  wstg: {
    label: "OWASP WSTG",
    description: "The full 97-item OWASP Web Security Testing Guide v4.2 checklist.",
  },
  oscp: {
    label: "OSCP-style",
    description:
      "OSCP/PWK-style engagement. Builds the same OWASP WSTG checklist for now — a distinct " +
      "OSCP-style checklist is a planned follow-up, not yet implemented.",
  },
  other: {
    label: "Other / Custom",
    description:
      "Any other methodology. Builds the same OWASP WSTG checklist as a starting point — add " +
      "or remove checklist items freely to match your own strategy.",
  },
};

export const DEFAULT_METHODOLOGY = "wstg";

export function methodologyLabel(key: string): string {
  return METHODOLOGIES[key]?.label ?? key;
}
