"""Auto-finding extraction from raw tool output.

Parses structured or semi-structured output from enumeration tools and
returns ``Finding`` objects flagged as **unverified** (tool-detected).
These are appended automatically when a tool finishes, giving the tester
a starting point they can later verify/dismiss.
"""
from __future__ import annotations

import re
from typing import Optional

from .models import Finding, Severity
from .scoring import COMMON_VECTORS, score_from_vector, severity_from_score


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def _make_finding(
    item_id: str,
    title: str,
    severity: Severity,
    description: str,
    evidence: str = "",
    raw_output: str = "",
    owasp_category: str = "",
    cwe_id: str = "",
    cvss_vector: str = "",
    tool: str = "unknown",
    remediation: str = "",
) -> Finding:
    """Create an unverified finding with optional CVSS auto-scoring."""
    cvss_score = 0.0
    if cvss_vector:
        cvss_score = score_from_vector(cvss_vector) or 0.0
        severity = Severity(severity_from_score(cvss_score))

    return Finding(
        checklist_item_id=item_id,
        title=title,
        severity=severity,
        description=description,
        evidence=evidence,
        raw_output=raw_output,
        owasp_category=owasp_category,
        cwe_id=cwe_id,
        cvss_vector=cvss_vector,
        cvss_score=cvss_score,
        verified=False,
        tool=tool,
        remediation=remediation,
    )


# ---------------------------------------------------------------------------
# Nmap findings
# ---------------------------------------------------------------------------

def extract_nmap(item_id: str, output: str) -> list[Finding]:
    """Extract findings from nmap output."""
    findings: list[Finding] = []

    # Detect TRACE method
    if re.search(r"risky methods:.*TRACE", output, re.IGNORECASE):
        findings.append(_make_finding(
            item_id=item_id,
            title="HTTP TRACE Method Enabled",
            severity=Severity.LOW,
            description=(
                "The TRACE HTTP method is enabled on the web server. "
                "This can be leveraged for Cross-Site Tracing (XST) attacks "
                "to steal credentials from HTTP headers."
            ),
            evidence=_grep_context(output, "TRACE", context=2),
            owasp_category="WSTG-CONF-06",
            cwe_id="CWE-16",
            cvss_vector=COMMON_VECTORS["http_trace_enabled"],
            tool="nmap",
            remediation="Disable the TRACE method in the web server configuration.",
        ))

    # Detect exposed admin panels (Tomcat Manager, etc.)
    tomcat_match = re.search(r"Apache Tomcat[/ ](\S+)", output)
    if tomcat_match:
        version = tomcat_match.group(1)
        findings.append(_make_finding(
            item_id=item_id,
            title=f"Apache Tomcat Manager Exposed (v{version})",
            severity=Severity.HIGH,
            description=(
                f"Apache Tomcat {version} Manager interface is accessible. "
                "Default or weak credentials may grant full server control."
            ),
            evidence=_grep_context(output, "Tomcat", context=3),
            owasp_category="WSTG-CONF-05",
            cwe_id="CWE-284",
            cvss_vector=COMMON_VECTORS["admin_interface_exposed"],
            tool="nmap",
            remediation=(
                "Restrict access to the Tomcat Manager to trusted IPs only. "
                "Change default credentials immediately."
            ),
        ))

    # Detect server version
    server_match = re.search(r"(nginx|apache|lighttpd)[/ ](\S+)", output, re.IGNORECASE)
    if server_match:
        server = server_match.group(1)
        version = server_match.group(2)
        findings.append(_make_finding(
            item_id=item_id,
            title=f"Server Version Disclosure: {server}/{version}",
            severity=Severity.LOW,
            description=(
                f"The web server discloses its version: {server}/{version}. "
                "This information helps attackers identify known CVEs for this version."
            ),
            evidence=_grep_context(output, server, context=1),
            owasp_category="WSTG-INFO-02",
            cwe_id="CWE-200",
            cvss_vector=COMMON_VECTORS["server_version_disclosure"],
            tool="nmap",
            remediation="Configure the server to suppress version information in headers and error pages.",
        ))

    # Missing CSP detection
    if re.search(r"No Content-Security-Policy", output, re.IGNORECASE):
        findings.append(_make_finding(
            item_id=item_id,
            title="Missing Content-Security-Policy Header",
            severity=Severity.MEDIUM,
            description=(
                "The Content-Security-Policy (CSP) header is not set. "
                "Without CSP, the application is more vulnerable to XSS attacks."
            ),
            evidence=_grep_context(output, "Content-Security-Policy", context=1),
            owasp_category="WSTG-CONF-08",
            cwe_id="CWE-693",
            cvss_vector=COMMON_VECTORS["missing_csp"],
            tool="nmap",
            remediation="Implement a Content-Security-Policy header with a restrictive policy.",
        ))

    return findings


# ---------------------------------------------------------------------------
# httpx findings
# ---------------------------------------------------------------------------

def extract_httpx(item_id: str, output: str) -> list[Finding]:
    """Extract findings from httpx output."""
    findings: list[Finding] = []

    # Missing security headers
    missing_headers = re.findall(
        r"Missing.*?:\s*-\s*([\w-]+)", output, re.IGNORECASE
    )
    # Also check line-by-line for "⚠  Missing headers:" block
    if not missing_headers:
        in_missing = False
        for line in output.splitlines():
            if "Missing headers" in line:
                in_missing = True
                continue
            if in_missing:
                hdr = line.strip().lstrip("- ").strip()
                if hdr and not hdr.startswith("⚠") and not hdr.startswith("Tech"):
                    missing_headers.append(hdr)
                elif not hdr.startswith("-") and hdr and not hdr.startswith(" "):
                    in_missing = False

    header_meta = {
        "Content-Security-Policy": (
            COMMON_VECTORS["missing_csp"], "CWE-693", "WSTG-CONF-08",
            "Implement a Content-Security-Policy header.",
        ),
        "Strict-Transport-Security": (
            COMMON_VECTORS["missing_hsts"], "CWE-319", "WSTG-CONF-07",
            "Add Strict-Transport-Security header with max-age >= 31536000.",
        ),
        "Referrer-Policy": (
            "", "CWE-116", "WSTG-CONF-08",
            "Set Referrer-Policy to 'strict-origin-when-cross-origin' or stricter.",
        ),
        "Permissions-Policy": (
            "", "CWE-693", "WSTG-CONF-08",
            "Configure a Permissions-Policy header to restrict browser features.",
        ),
    }

    for hdr_name in missing_headers:
        meta = header_meta.get(hdr_name)
        if meta:
            cvss_v, cwe, owasp, remed = meta
        else:
            cvss_v, cwe, owasp, remed = "", "CWE-693", "WSTG-CONF-08", f"Add the {hdr_name} header."

        findings.append(_make_finding(
            item_id=item_id,
            title=f"Missing {hdr_name} Header",
            severity=Severity.MEDIUM if "CSP" in hdr_name or "HSTS" in hdr_name or "Strict" in hdr_name else Severity.LOW,
            description=f"The {hdr_name} security header is missing from the HTTP response.",
            evidence=_grep_context(output, hdr_name, context=1),
            owasp_category=owasp,
            cwe_id=cwe,
            cvss_vector=cvss_v,
            tool="httpx",
            remediation=remed,
        ))

    # Cookie without Secure/HttpOnly
    cookie_match = re.search(r"Set-Cookie:.*missing\s+(Secure|HttpOnly)", output, re.IGNORECASE)
    if cookie_match:
        findings.append(_make_finding(
            item_id=item_id,
            title="Cookie Missing Secure/HttpOnly Flags",
            severity=Severity.MEDIUM,
            description=(
                "A session cookie is set without the Secure and/or HttpOnly flags. "
                "This may allow cookie theft via XSS or network interception."
            ),
            evidence=_grep_context(output, "Set-Cookie", context=1),
            owasp_category="WSTG-CONF-08",
            cwe_id="CWE-614",
            tool="httpx",
            remediation="Set both Secure and HttpOnly flags on all session cookies.",
        ))

    return findings


# ---------------------------------------------------------------------------
# whatweb findings
# ---------------------------------------------------------------------------

def extract_whatweb(item_id: str, output: str) -> list[Finding]:
    """Extract findings from whatweb output."""
    findings: list[Finding] = []

    # EOL / outdated software
    eol_matches = re.findall(
        r"\[?\+?\]?\s*(\w[\w.]*)\s*\n?\s*Version\s*:\s*(\S+)\s*\n?\s*⚠\s*(.*)",
        output,
    )
    for tech, version, note in eol_matches:
        # Try to extract CVE from the note
        cve_match = re.search(r"(CVE-\d{4}-\d+)", note)
        cve_str = cve_match.group(1) if cve_match else ""

        findings.append(_make_finding(
            item_id=item_id,
            title=f"Outdated Software: {tech} {version}",
            severity=Severity.MEDIUM,
            description=f"{tech} version {version} is outdated. {note.strip()}",
            evidence=f"{tech} {version}: {note.strip()}",
            owasp_category="WSTG-INFO-08",
            cwe_id="CWE-1104",
            cvss_vector=COMMON_VECTORS.get("outdated_software", ""),
            tool="whatweb",
            remediation=f"Upgrade {tech} to the latest stable version.",
        ))

    # Email disclosure
    email_match = re.search(r"Email\[([^\]]+)\]", output)
    if email_match:
        email = email_match.group(1)
        findings.append(_make_finding(
            item_id=item_id,
            title=f"Email Address Disclosed: {email}",
            severity=Severity.INFO,
            description=f"An email address ({email}) was found in the page source or headers.",
            evidence=f"Email: {email}",
            owasp_category="WSTG-INFO-05",
            cwe_id="CWE-200",
            tool="whatweb",
            remediation="Consider using a contact form instead of exposing email addresses.",
        ))

    return findings


# ---------------------------------------------------------------------------
# nuclei findings
# ---------------------------------------------------------------------------

def extract_nuclei(item_id: str, output: str) -> list[Finding]:
    """Extract findings from nuclei output."""
    findings: list[Finding] = []

    # Parse nuclei output lines like:
    # [2026-07-07 15:01:23] [missing-csp] [http] [medium] https://target
    pattern = re.compile(
        r"\[[\d\-: ]+\]\s*\[([^\]]+)\]\s*\[([^\]]+)\]\s*\[(\w+)\]\s*(https?://\S+)(?:\s*\n?\s*info:\s*(.*))?",
        re.MULTILINE,
    )

    nuclei_meta = {
        "missing-csp": ("Missing Content-Security-Policy", "CWE-693", "WSTG-CONF-08",
                         COMMON_VECTORS["missing_csp"],
                         "Implement a Content-Security-Policy header."),
        "missing-hsts": ("Missing HSTS Header", "CWE-319", "WSTG-CONF-07",
                          COMMON_VECTORS["missing_hsts"],
                          "Add Strict-Transport-Security header."),
        "tomcat-manager-exposed": ("Tomcat Manager Exposed", "CWE-284", "WSTG-CONF-05",
                                    COMMON_VECTORS["admin_interface_exposed"],
                                    "Restrict access to the Tomcat Manager."),
        "http-trace-method": ("HTTP TRACE Method Enabled", "CWE-16", "WSTG-CONF-06",
                               COMMON_VECTORS["http_trace_enabled"],
                               "Disable the TRACE method."),
        "phpinfo-disclosure": ("phpinfo() Page Accessible", "CWE-200", "WSTG-CONF-02",
                                COMMON_VECTORS["sensitive_file_exposed"],
                                "Remove or restrict access to phpinfo() pages."),
        "directory-listing": ("Directory Listing Enabled", "CWE-548", "WSTG-CONF-02",
                               COMMON_VECTORS["directory_listing"],
                               "Disable directory listing in the web server config."),
    }

    for match in pattern.finditer(output):
        template_id = match.group(1)
        _protocol = match.group(2)
        sev_str = match.group(3).lower()
        url = match.group(4)
        info = match.group(5) or ""

        sev_map = {"critical": Severity.CRITICAL, "high": Severity.HIGH,
                    "medium": Severity.MEDIUM, "low": Severity.LOW, "info": Severity.INFO}
        severity = sev_map.get(sev_str, Severity.INFO)

        meta = nuclei_meta.get(template_id)
        if meta:
            title, cwe, owasp, cvss_v, remed = meta
        else:
            title = template_id.replace("-", " ").title()
            cwe, owasp, cvss_v, remed = "", "", "", ""

        findings.append(_make_finding(
            item_id=item_id,
            title=title,
            severity=severity,
            description=info.strip() if info.strip() else f"Nuclei template '{template_id}' matched at {url}.",
            evidence=f"URL: {url}\nTemplate: {template_id}",
            owasp_category=owasp,
            cwe_id=cwe,
            cvss_vector=cvss_v,
            tool="nuclei",
            remediation=remed,
        ))

    return findings


# ---------------------------------------------------------------------------
# wafw00f findings
# ---------------------------------------------------------------------------

def extract_wafw00f(item_id: str, output: str) -> list[Finding]:
    """Extract findings from wafw00f output."""
    findings: list[Finding] = []

    if re.search(r"No WAF detected", output, re.IGNORECASE):
        findings.append(_make_finding(
            item_id=item_id,
            title="No Web Application Firewall Detected",
            severity=Severity.INFO,
            description=(
                "No WAF was detected protecting the application. "
                "While not a vulnerability itself, the lack of a WAF means "
                "there is no additional layer of protection against web attacks."
            ),
            evidence=_grep_context(output, "No WAF", context=2),
            owasp_category="WSTG-INFO-10",
            cwe_id="CWE-693",
            tool="wafw00f",
            remediation="Consider deploying a WAF (Cloudflare, AWS WAF, ModSecurity) for defense-in-depth.",
        ))
    else:
        waf_match = re.search(r"is behind\s+(\S+)", output, re.IGNORECASE)
        if waf_match:
            waf_name = waf_match.group(1)
            findings.append(_make_finding(
                item_id=item_id,
                title=f"WAF Detected: {waf_name}",
                severity=Severity.INFO,
                description=f"A Web Application Firewall ({waf_name}) was detected. Active scanning results may be filtered.",
                evidence=_grep_context(output, waf_name, context=2),
                owasp_category="WSTG-INFO-10",
                cwe_id="",
                tool="wafw00f",
            ))

    return findings


# ---------------------------------------------------------------------------
# subfinder findings
# ---------------------------------------------------------------------------

def extract_subfinder(item_id: str, output: str) -> list[Finding]:
    """Extract findings from subfinder output."""
    findings: list[Finding] = []

    # Count subdomains
    subdomain_lines = [
        line.strip() for line in output.splitlines()
        if line.strip() and not line.startswith("[") and not line.startswith("⚠") and "." in line
        and not line.startswith("SIMULATED")
    ]

    interesting = ["dev", "staging", "admin", "backup", "old", "test", "internal", "debug", "qa"]
    risky_subs = [s for s in subdomain_lines if any(kw in s.lower() for kw in interesting)]

    if risky_subs:
        findings.append(_make_finding(
            item_id=item_id,
            title=f"Potentially Sensitive Subdomains Found ({len(risky_subs)})",
            severity=Severity.MEDIUM,
            description=(
                "Subdomains suggesting development, staging, or admin environments were discovered. "
                "These may have weaker security controls than production."
            ),
            evidence="\n".join(risky_subs[:10]),
            owasp_category="WSTG-INFO-01",
            cwe_id="CWE-200",
            tool="subfinder",
            remediation=(
                "Review all discovered subdomains. Ensure dev/staging environments "
                "are not publicly accessible or are properly secured."
            ),
        ))

    if len(subdomain_lines) > 0:
        findings.append(_make_finding(
            item_id=item_id,
            title=f"Subdomain Enumeration: {len(subdomain_lines)} Subdomains Found",
            severity=Severity.INFO,
            description=f"{len(subdomain_lines)} subdomains were discovered via passive enumeration.",
            evidence="\n".join(subdomain_lines[:15]),
            owasp_category="WSTG-INFO-01",
            cwe_id="CWE-200",
            tool="subfinder",
        ))

    return findings


# ---------------------------------------------------------------------------
# nikto findings
# ---------------------------------------------------------------------------

def extract_nikto(item_id: str, output: str) -> list[Finding]:
    """Extract findings from nikto output."""
    findings: list[Finding] = []

    # Parse + lines from nikto output
    for line in output.splitlines():
        line = line.strip()
        if not line.startswith("+"):
            continue

        # OSVDB entries
        osvdb_match = re.match(r"\+\s*OSVDB-\d+:\s*(.*)", line)
        if osvdb_match:
            desc = osvdb_match.group(1).strip()
            # Determine severity from context
            severity = Severity.MEDIUM
            if any(kw in desc.lower() for kw in ["remote code", "rce", "arbitrary", "sql injection"]):
                severity = Severity.HIGH
            elif any(kw in desc.lower() for kw in ["information", "disclosure", "version"]):
                severity = Severity.LOW

            findings.append(_make_finding(
                item_id=item_id,
                title=desc[:80],
                severity=severity,
                description=desc,
                evidence=line,
                owasp_category="WSTG-CONF-02",
                cwe_id="CWE-200",
                tool="nikto",
            ))

    return findings


# ---------------------------------------------------------------------------
# Dispatcher: tool name → extractor
# ---------------------------------------------------------------------------

EXTRACTORS: dict[str, callable] = {
    "nmap":      extract_nmap,
    "httpx":     extract_httpx,
    "whatweb":   extract_whatweb,
    "nuclei":    extract_nuclei,
    "wafw00f":   extract_wafw00f,
    "subfinder": extract_subfinder,
    "nikto":     extract_nikto,
}


def extract_findings(
    tool_name: str,
    item_id: str,
    output: str,
) -> list[Finding]:
    """Run the appropriate extractor for *tool_name* and return findings.

    Returns an empty list if no extractor is registered for the tool.
    """
    extractor = EXTRACTORS.get(tool_name)
    if extractor is None:
        return []
    try:
        return extractor(item_id, output)
    except Exception:
        # Never crash the workflow because of a parser bug
        return []


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _grep_context(text: str, keyword: str, context: int = 2) -> str:
    """Return lines around the first occurrence of *keyword*."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if keyword.lower() in line.lower():
            start = max(0, i - context)
            end = min(len(lines), i + context + 1)
            return "\n".join(lines[start:end])
    return ""
