"""CVSS v3.1 base-score calculator and severity helpers."""
from __future__ import annotations

import math
from typing import Optional


# ---------------------------------------------------------------------------
# CVSS v3.1 metric weights
# ---------------------------------------------------------------------------
_AV  = {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.20}
_AC  = {"L": 0.77, "H": 0.44}
_PR_U = {"N": 0.85, "L": 0.62, "H": 0.27}   # Scope Unchanged
_PR_C = {"N": 0.85, "L": 0.68, "H": 0.50}   # Scope Changed
_UI  = {"N": 0.85, "R": 0.62}
_CIA = {"H": 0.56, "L": 0.22, "N": 0.00}


def _roundup(x: float) -> float:
    """CVSS-specific round-up to 1 decimal place."""
    return math.ceil(x * 10) / 10


def calculate_base_score(
    av: str, ac: str, pr: str, ui: str, s: str,
    c: str, i: str, a: str,
) -> float:
    """Return the CVSS v3.1 base score (0.0 – 10.0)."""
    av_v  = _AV[av]
    ac_v  = _AC[ac]
    pr_v  = (_PR_C if s == "C" else _PR_U)[pr]
    ui_v  = _UI[ui]

    iss = 1 - (1 - _CIA[c]) * (1 - _CIA[i]) * (1 - _CIA[a])

    if iss <= 0:
        return 0.0

    if s == "U":
        impact = 6.42 * iss
    else:
        impact = 7.52 * (iss - 0.029) - 3.25 * ((iss - 0.02) ** 15)

    exploitability = 8.22 * av_v * ac_v * pr_v * ui_v

    if s == "U":
        base = min(impact + exploitability, 10.0)
    else:
        base = min(1.08 * (impact + exploitability), 10.0)

    return _roundup(base)


def score_from_vector(vector: str) -> Optional[float]:
    """Parse 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H' → float."""
    try:
        parts: dict[str, str] = {}
        for segment in vector.split("/")[1:]:        # skip "CVSS:3.1"
            k, v = segment.split(":")
            parts[k] = v
        return calculate_base_score(
            av=parts["AV"], ac=parts["AC"], pr=parts["PR"],
            ui=parts["UI"], s=parts["S"],
            c=parts["C"], i=parts["I"], a=parts["A"],
        )
    except (KeyError, ValueError):
        return None


def severity_from_score(score: float) -> str:
    if score >= 9.0:
        return "critical"
    elif score >= 7.0:
        return "high"
    elif score >= 4.0:
        return "medium"
    elif score > 0.0:
        return "low"
    return "info"


# ---------------------------------------------------------------------------
# Common CVSS vectors for quick reference
# ---------------------------------------------------------------------------
COMMON_VECTORS = {
    "server_version_disclosure":   "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N",
    "missing_hsts":                "CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:L/A:N",
    "missing_csp":                 "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N",
    "open_redirect":               "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N",
    "sensitive_file_exposed":      "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
    "admin_interface_exposed":     "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
    "outdated_software":           "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
    "subdomain_takeover":          "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:N",
    "http_trace_enabled":          "CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:L/I:L/A:N",
    "directory_listing":           "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N",
    "sql_injection":               "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
    "default_credentials":         "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
    "known_cve_vulnerability":     "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N",
    "sensitive_path_exposed":      "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
    "command_injection":           "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H",
    "reflected_xss":               "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N",
}
