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
# sqlmap findings
# ---------------------------------------------------------------------------

def extract_sqlmap(item_id: str, output: str) -> list[Finding]:
    """Extract findings from sqlmap output.

    Real sqlmap reports a confirmed injection point as a "Parameter: NAME
    (METHOD)" block followed by one or more Type/Title/Payload groups —
    this is sqlmap's actual reporting format, not just the mock output's,
    so this parser works against a real run too.
    """
    findings: list[Finding] = []

    param_block_re = re.compile(
        r"Parameter:\s*(\S+)\s*\((\w+)\)\n((?:(?!Parameter:).)*)",
        re.DOTALL,
    )
    type_re = re.compile(r"Type:\s*(.+)")

    dbms_match = re.search(r"back-end DBMS is (\S+)", output)
    dbms = dbms_match.group(1) if dbms_match else None

    for match in param_block_re.finditer(output):
        param, method, block = match.group(1), match.group(2), match.group(3)
        types = [t.strip() for t in type_re.findall(block)]
        if not types:
            continue
        description = (
            f"sqlmap confirmed SQL injection in the '{param}' {method} parameter "
            f"({', '.join(types)})."
        )
        if dbms:
            description += f" Back-end DBMS: {dbms}."
        findings.append(_make_finding(
            item_id=item_id,
            title=f"SQL Injection in '{param}' ({method}) Parameter",
            severity=Severity.CRITICAL,
            description=description,
            evidence=block.strip()[:800],
            owasp_category="WSTG-INPV-05",
            cwe_id="CWE-89",
            cvss_vector=COMMON_VECTORS["sql_injection"],
            tool="sqlmap",
            remediation=(
                "Use parameterized queries/prepared statements for every database "
                "call. Never build SQL by string-concatenating user input."
            ),
        ))

    return findings


# ---------------------------------------------------------------------------
# hydra findings
# ---------------------------------------------------------------------------

def extract_hydra(item_id: str, output: str) -> list[Finding]:
    """Extract findings from hydra output.

    Real hydra prints a found credential pair as
    "[PORT][service] host: HOST   login: USER   password: PASS" — this is
    hydra's own real output format.
    """
    findings: list[Finding] = []

    cred_re = re.compile(
        r"\[\d+\]\[(\w+)\]\s+host:\s*(\S+)\s+login:\s*(\S+)\s+password:\s*(\S+)"
    )
    for service, host, login, password in cred_re.findall(output):
        findings.append(_make_finding(
            item_id=item_id,
            title=f"Weak/Default Credential Accepted ({service})",
            severity=Severity.CRITICAL,
            description=(
                f"hydra found a working credential pair on {host} via {service}: "
                f"'{login}:{password}'. This account is protected only by a "
                f"guessable password."
            ),
            evidence=f"{service}://{host} — {login}:{password}",
            owasp_category="WSTG-ATHN-02",
            cwe_id="CWE-521",
            cvss_vector=COMMON_VECTORS["default_credentials"],
            tool="hydra",
            remediation=(
                "Change this credential immediately, enforce a strong password "
                "policy, and add account lockout / rate limiting (see WSTG-ATHN-03)."
            ),
        ))

    if re.search(r"No account lockout observed", output, re.IGNORECASE):
        findings.append(_make_finding(
            item_id=item_id,
            title="No Account Lockout After Repeated Failed Logins",
            severity=Severity.MEDIUM,
            description=(
                "Repeated failed login attempts did not trigger any lockout or "
                "throttling, leaving the login endpoint open to unlimited "
                "brute-force/credential-stuffing attempts."
            ),
            evidence=_grep_context(output, "lockout", context=1),
            owasp_category="WSTG-ATHN-03",
            cwe_id="CWE-307",
            tool="hydra",
            remediation="Add account lockout or progressive-delay throttling after N failed attempts.",
        ))

    return findings


# ---------------------------------------------------------------------------
# wpscan findings
# ---------------------------------------------------------------------------

def extract_wpscan(item_id: str, output: str) -> list[Finding]:
    """Extract findings from wpscan output."""
    findings: list[Finding] = []

    core_match = re.search(r"WordPress version (\S+) identified.*?(\d+) vulnerabilit", output, re.DOTALL)
    if core_match:
        version, count = core_match.group(1), core_match.group(2)
        findings.append(_make_finding(
            item_id=item_id,
            title=f"Outdated WordPress Core: v{version} ({count} known vulnerabilities)",
            severity=Severity.HIGH,
            description=(
                f"WordPress core version {version} has {count} known "
                f"vulnerabilities against it per WPScan's vulnerability database."
            ),
            evidence=_grep_context(output, "WordPress version", context=2),
            owasp_category="WSTG-INFO-08",
            cwe_id="CWE-1104",
            tool="wpscan",
            remediation="Update WordPress core to the latest stable release.",
        ))

    # "[!] Title: ..." blocks appear for both core and plugin/theme
    # vulnerabilities, each optionally followed by "Fixed in:"/"Reference:".
    vuln_re = re.compile(
        r"\[!\]\s*Title:\s*(.+?)\n"
        r"(?:\s*\|?\s*Fixed in:\s*(\S+)\n)?"
        r"(?:\s*\|?\s*Reference:\s*(\S+))?"
    )
    for title, fixed_in, reference in vuln_re.findall(output):
        title = title.strip()
        desc = title
        if fixed_in:
            desc += f" — fixed in {fixed_in}."

        # The vuln database entry's own title is the only signal available
        # for how bad it actually is (WPScan's text report doesn't carry a
        # CVSS score per finding) — same keyword-sniffing approach as
        # extract_nikto() above, rather than one fixed severity/CVSS vector
        # for every entry regardless of whether it's an RCE or a low-impact
        # disclosure.
        lower_title = title.lower()
        if any(kw in lower_title for kw in ("sql injection", "rce", "remote code", "arbitrary file")):
            severity, cwe = Severity.CRITICAL, "CWE-89"
        elif any(kw in lower_title for kw in ("xss", "csrf", "privilege escalation")):
            severity, cwe = Severity.MEDIUM, "CWE-79"
        elif any(kw in lower_title for kw in ("disclosure", "information")):
            severity, cwe = Severity.LOW, "CWE-200"
        else:
            severity, cwe = Severity.HIGH, "CWE-1104"

        findings.append(_make_finding(
            item_id=item_id,
            title=title[:90],
            severity=severity,
            description=desc,
            evidence=reference or title,
            owasp_category="WSTG-INFO-08",
            cwe_id=cwe,
            tool="wpscan",
            remediation=f"Update to {fixed_in} or later." if fixed_in else "Update the affected component.",
        ))

    users = re.findall(r"\[\+\]\s*(\S+)\s*\(ID:\s*\d+\)", output)
    if users:
        findings.append(_make_finding(
            item_id=item_id,
            title=f"WordPress User Accounts Enumerated ({len(users)})",
            severity=Severity.LOW,
            description=(
                f"{len(users)} WordPress user account(s) were enumerated via "
                f"author-ID brute forcing: {', '.join(users)}. These are now a "
                f"known target list for credential attacks."
            ),
            evidence=", ".join(users),
            owasp_category="WSTG-IDNT-04",
            cwe_id="CWE-203",
            tool="wpscan",
            remediation="Rename/hide default author archive URLs, or block user enumeration at the plugin/WAF level.",
        ))

    return findings


# ---------------------------------------------------------------------------
# dnsx findings
# ---------------------------------------------------------------------------

def extract_dnsx(item_id: str, output: str) -> list[Finding]:
    """Extract findings from dnsx output."""
    findings: list[Finding] = []

    for match in re.finditer(
        r"\[CNAME\]\s*(\S+)\n\s*→\s*(\S+)\.?\s*⚠\s*potential dangling CNAME",
        output,
    ):
        subdomain, target = match.group(1), match.group(2)
        findings.append(_make_finding(
            item_id=item_id,
            title=f"Potential Dangling CNAME: {subdomain}",
            severity=Severity.HIGH,
            description=(
                f"{subdomain} has a CNAME record pointing at {target}, a "
                f"third-party service — if that resource has been deprovisioned, "
                f"an attacker can claim it and serve content under {subdomain}."
            ),
            evidence=f"{subdomain} → {target}",
            owasp_category="WSTG-CONF-10",
            cwe_id="CWE-350",
            # No cvss_vector here deliberately: dnsx only flags this as
            # *potential* (it can't confirm the target resource is actually
            # deprovisioned) — the full subdomain_takeover vector implies a
            # confirmed claim and would overstate a still-unverified finding
            # as a 10.0/critical. HIGH (manual, not CVSS-computed) reflects
            # "worth checking now" without claiming more certainty than the
            # tool actually has.
            tool="dnsx",
            remediation=f"Verify whether the resource at {target} is still provisioned; remove the CNAME if not.",
        ))

    return findings


# ---------------------------------------------------------------------------
# naabu findings
# ---------------------------------------------------------------------------

# Ports whose mere exposure is itself worth flagging — databases, caches,
# and management interfaces that should almost never be internet-facing.
# (port, title, severity, cwe)
_INTERESTING_PORTS: tuple[tuple[int, str, Severity, str], ...] = (
    (23,    "Telnet Service Exposed (Unencrypted)", Severity.HIGH, "CWE-319"),
    (3306,  "MySQL Database Port Exposed", Severity.HIGH, "CWE-16"),
    (5432,  "PostgreSQL Database Port Exposed", Severity.HIGH, "CWE-16"),
    (6379,  "Redis Port Exposed (Often Unauthenticated)", Severity.HIGH, "CWE-306"),
    (27017, "MongoDB Port Exposed", Severity.HIGH, "CWE-16"),
    (9200,  "Elasticsearch Port Exposed", Severity.HIGH, "CWE-16"),
    (2375,  "Docker API Exposed (Unauthenticated)", Severity.CRITICAL, "CWE-306"),
    (5900,  "VNC Port Exposed", Severity.HIGH, "CWE-16"),
    (3389,  "RDP Port Exposed", Severity.MEDIUM, "CWE-16"),
    (21,    "FTP Service Exposed", Severity.MEDIUM, "CWE-16"),
)


def extract_naabu(item_id: str, output: str) -> list[Finding]:
    """Extract findings from naabu output (real -silent mode prints one bare
    'host:port' line per open port — nothing else)."""
    findings: list[Finding] = []
    ports = {int(p) for p in re.findall(r":(\d+)\s*$", output, re.MULTILINE)}

    for port, title, severity, cwe in _INTERESTING_PORTS:
        if port not in ports:
            continue
        findings.append(_make_finding(
            item_id=item_id,
            title=title,
            severity=severity,
            description=f"Port {port} is open and reachable — {title.lower()}.",
            evidence=_grep_context(output, f":{port}", context=0),
            owasp_category="WSTG-CONF-01",
            cwe_id=cwe,
            tool="naabu",
            remediation=f"Firewall port {port} from the internet, or bind the service to localhost/an internal network only.",
        ))

    return findings


# ---------------------------------------------------------------------------
# dalfox findings
# ---------------------------------------------------------------------------

def extract_dalfox(item_id: str, output: str) -> list[Finding]:
    """Extract findings from dalfox output.

    A confirmed hit is reported as a `[POC][METHOD]` block followed by
    `URL:`/`Param:`/`Type:` lines — dalfox's own real reporting format for
    a verified (not just reflected-looking) XSS.
    """
    findings: list[Finding] = []

    poc_re = re.compile(
        r"\[POC\]\[(\w+)\][^\n]*\n\s*URL:\s*(\S+)\n\s*Param:\s*(\S+)\n\s*Type:\s*(\S+)"
    )
    for method, url, param, xss_type in poc_re.findall(output):
        findings.append(_make_finding(
            item_id=item_id,
            title=f"{xss_type} XSS in '{param}' Parameter",
            # Overridden by cvss_vector below (a typical reflected-XSS
            # vector scores 6.1/MEDIUM) — this argument is just the
            # pre-CVSS fallback, kept accurate rather than misleading.
            severity=Severity.MEDIUM,
            description=(
                f"dalfox confirmed a {xss_type.lower()} XSS vector via the '{param}' "
                f"{method} parameter, verified against a real browser context "
                f"(not just a raw string reflection)."
            ),
            evidence=url,
            owasp_category="WSTG-INPV-01",
            cwe_id="CWE-79",
            cvss_vector=COMMON_VECTORS["reflected_xss"],
            tool="dalfox",
            remediation=(
                "Context-appropriately encode/escape this parameter wherever it's "
                "reflected into the response, and add a Content-Security-Policy as "
                "defense in depth."
            ),
        ))

    return findings


# ---------------------------------------------------------------------------
# commix findings
# ---------------------------------------------------------------------------

def extract_commix(item_id: str, output: str) -> list[Finding]:
    """Extract findings from commix output.

    commix announces a confirmed injection with a line naming the vulnerable
    parameter and technique, e.g. "The (GET) 'host' parameter is vulnerable
    via the classic injection technique."
    """
    findings: list[Finding] = []

    vuln_re = re.compile(
        r"The \((\w+)\)\s*'(\w+)'\s*parameter is vulnerable via the (.+?) technique",
        re.IGNORECASE,
    )
    for method, param, technique in vuln_re.findall(output):
        findings.append(_make_finding(
            item_id=item_id,
            title=f"OS Command Injection in '{param}' ({method}) Parameter",
            severity=Severity.CRITICAL,
            description=(
                f"commix confirmed OS command injection in the '{param}' {method} "
                f"parameter via the {technique} technique — arbitrary shell commands "
                f"can be executed on the server."
            ),
            evidence=_grep_context(output, param, context=1),
            owasp_category="WSTG-INPV-12",
            cwe_id="CWE-78",
            cvss_vector=COMMON_VECTORS["command_injection"],
            tool="commix",
            remediation=(
                "Never pass user input to a shell/OS command. Use a language-native "
                "API instead of shelling out; if unavoidable, use strict allow-listing "
                "and a non-shell exec call (no string concatenation into a shell)."
            ),
        ))

    return findings


# ---------------------------------------------------------------------------
# ffuf / gobuster findings — both discover directories/files by brute
# force; share the same "does this path look sensitive" heuristic.
# ---------------------------------------------------------------------------

_INTERESTING_PATHS: tuple[tuple[str, str, Severity, str, bool], ...] = (
    # (substring to match in the discovered path, title, severity, cwe,
    #  use the shared high-impact CVSS vector — only for the genuinely
    #  high-severity ones; the rest keep their own fixed severity below,
    #  since _make_finding() lets a passed cvss_vector's auto-computed
    #  score override the severity= argument, and one shared vector for
    #  every entry would have flattened "admin discovered" (low) and
    #  ".env exposed" (high) to the same severity)
    (".env", "Environment Configuration File Exposed", Severity.HIGH, "CWE-538", True),
    (".git", "Git Repository Metadata Exposed", Severity.HIGH, "CWE-538", True),
    ("phpmyadmin", "phpMyAdmin Interface Exposed", Severity.MEDIUM, "CWE-284", False),
    ("wp-admin", "WordPress Admin Interface Exposed", Severity.MEDIUM, "CWE-284", False),
    ("server-status", "Apache mod_status Exposed", Severity.MEDIUM, "CWE-200", False),
    ("backup", "Backup File/Directory Exposed", Severity.MEDIUM, "CWE-530", False),
    ("config", "Configuration Path Exposed", Severity.MEDIUM, "CWE-538", False),
    ("admin", "Admin Interface Discovered", Severity.LOW, "CWE-284", False),
)


# Status codes that mean "exists but needs credentials/permission" rather
# than "publicly reachable" — surfaced per-path so a tester can tell the two
# apart at a glance instead of treating every discovered path as equally
# open (see the paired status badges in frontend/src/components/DirectoryTree.tsx).
_AUTH_REQUIRED_CODES = {"401", "403"}


def _access_note(status: Optional[str]) -> str:
    if status is None:
        return ""
    if status in _AUTH_REQUIRED_CODES:
        return f" (HTTP {status} — requires permission/authentication to access)"
    if status == "200":
        return " (HTTP 200 — publicly accessible)"
    return f" (HTTP {status})"


def _flag_interesting_paths(
    paths: list[str], item_id: str, tool: str, statuses: Optional[dict[str, str]] = None
) -> list[Finding]:
    statuses = statuses or {}
    findings: list[Finding] = []
    seen_titles: set[str] = set()
    for path in paths:
        lower = path.lower()
        for keyword, title, severity, cwe, use_vector in _INTERESTING_PATHS:
            if keyword in lower and title not in seen_titles:
                seen_titles.add(title)
                note = _access_note(statuses.get(path))
                findings.append(_make_finding(
                    item_id=item_id,
                    title=title,
                    severity=severity,
                    description=f"A path matching '{keyword}' was discovered: {path}{note}.",
                    evidence=path,
                    owasp_category="WSTG-CONF-05" if "admin" in keyword else "WSTG-CONF-04",
                    cwe_id=cwe,
                    cvss_vector=COMMON_VECTORS["sensitive_path_exposed"] if use_vector else "",
                    tool=tool,
                    remediation=f"Restrict or remove access to {path} if not intentionally public.",
                ))
                break
    return findings


def extract_ffuf(item_id: str, output: str) -> list[Finding]:
    """Extract findings from ffuf output: its own mock/-v verbose "[Status:
    ...]" + "| URL |" pair, real ffuf's -s silent bare-path-per-line output
    (older saved runs, from before -v replaced -s), and gobuster-style
    "path (Status: N)" as a fallback."""
    statuses: dict[str, str] = {}
    pending_status: Optional[str] = None
    paths: list[str] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        status_m = re.match(r"^\[Status:\s*(\d+)", line)
        if status_m:
            pending_status = status_m.group(1)
            continue
        url_m = re.match(r"^\|\s*URL\s*\|\s*(\S+)", line)
        if url_m:
            path = url_m.group(1).split("->")[0].strip()
            paths.append(path)
            if pending_status:
                statuses[path] = pending_status
            pending_status = None

    if not paths:
        # Real ffuf -s output: one bare relative path per line, nothing else
        # (no status info at all — a run saved before -v replaced -s).
        paths = [
            line.strip() for line in output.splitlines()
            if line.strip() and re.match(r"^[\w.\-/]+$", line.strip())
        ]

    return _flag_interesting_paths(paths, item_id, "ffuf", statuses)


def extract_gobuster(item_id: str, output: str) -> list[Finding]:
    """Extract findings from gobuster output."""
    matches = re.findall(r"^(/\S*)\s+\(Status:\s*(\d+)", output, re.MULTILINE)
    paths = [p for p, _ in matches]
    statuses = {p: s for p, s in matches}
    return _flag_interesting_paths(paths, item_id, "gobuster", statuses)


# ---------------------------------------------------------------------------
# zap (zap-baseline.py) findings
# ---------------------------------------------------------------------------

def extract_zap(item_id: str, output: str) -> list[Finding]:
    """Extract findings from zap-baseline.py output.

    A confirmed alert is a `WARN-NEW: <title> [<rule-id>] x <count>` or
    `FAIL-NEW: <title> [<rule-id>] x <count>` line, followed by tab-indented
    lines listing the affected URLs — zap-baseline.py's own real reporting
    format, confirmed against a live run (not guessed from docs).
    """
    findings: list[Finding] = []
    alert_re = re.compile(r"^(WARN-NEW|FAIL-NEW):\s*(.+?)\s*\[(\d+)\]\s*x\s*(\d+)")

    lines = output.splitlines()
    for i, raw_line in enumerate(lines):
        m = alert_re.match(raw_line.strip())
        if not m:
            continue
        level, title, rule_id, count = m.groups()

        affected: list[str] = []
        for follow in lines[i + 1:]:
            if not follow.startswith(("\t", "    ")):
                break
            affected.append(follow.strip())

        # zap-baseline.py's own two-tier pass/fail threshold (FAIL is what
        # would break a CI pipeline without -I) — not ZAP's separate
        # internal Low/Medium/High risk rating, which isn't in this
        # short-format output at all.
        severity = Severity.HIGH if level == "FAIL-NEW" else Severity.MEDIUM
        findings.append(_make_finding(
            item_id=item_id,
            title=title,
            severity=severity,
            description=(
                f"ZAP's passive scan flagged '{title}' (rule {rule_id}) on "
                f"{count} URL(s)."
            ),
            evidence="\n".join(affected[:5]) or title,
            owasp_category="WSTG-INFO-07",
            cwe_id="CWE-200",
            tool="zap",
            remediation=f"Review ZAP rule {rule_id} ('{title}') and address it for the affected URL(s).",
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
    "sqlmap":    extract_sqlmap,
    "hydra":     extract_hydra,
    "wpscan":    extract_wpscan,
    "dnsx":      extract_dnsx,
    "ffuf":      extract_ffuf,
    "gobuster":  extract_gobuster,
    "naabu":     extract_naabu,
    "dalfox":    extract_dalfox,
    "commix":    extract_commix,
    "zap":       extract_zap,
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
