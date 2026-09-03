"""OWASP WSTG v4.2 checklist definitions with tool mappings.

Covers the full WSTG v4.2 table of contents (4.1 through 4.12):
  • WSTG-INFO-01 … WSTG-INFO-10  (Information Gathering)
  • WSTG-CONF-01 … WSTG-CONF-11  (Configuration & Deployment Management)
  • WSTG-IDNT-01 … WSTG-IDNT-05  (Identity Management)
  • WSTG-ATHN-01 … WSTG-ATHN-10  (Authentication)
  • WSTG-ATHZ-01 … WSTG-ATHZ-04  (Authorization)
  • WSTG-SESS-01 … WSTG-SESS-09  (Session Management)
  • WSTG-INPV-01 … WSTG-INPV-19  (Input Validation)
  • WSTG-ERRH-01, WSTG-ERRH-02   (Error Handling)
  • WSTG-CRYP-01 … WSTG-CRYP-04  (Weak Cryptography)
  • WSTG-BUSL-01 … WSTG-BUSL-09  (Business Logic)
  • WSTG-CLNT-01 … WSTG-CLNT-13  (Client-side)
  • WSTG-APIT-01                 (API Testing)

Many items in the back half of the guide (Business Logic, most of
Authentication/Session Management, several Client-side tests) are
inherently manual/logic-driven — no CLI tool can decide whether an
application's workflow can legitimately be circumvented. Those items
list `tools=[]` or the closest thing that provides *supporting* evidence
(e.g. httpx for a cookie's flags) rather than a tool that "does" the test.
"""
from __future__ import annotations

import re

from .models import ChecklistItem, Engagement

# Maps a checklist item ID to a wordlist category (see
# oculus/wordlists.py's recommend_wordlist() and CATEGORY_LABELS below)
# for the items whose tools include a wordlist-based tool (ffuf/gobuster).
# Lets the Run Tool dialog suggest a wordlist actually suited to what that
# specific test is looking for — an admin-panel list for "Enumerate Admin
# Interfaces", an API list for "Identify Application Entry Points" —
# instead of one generic directory list for every test. Items not listed
# here (including custom tester-added items) just get the plain default.
WORDLIST_CATEGORY: dict[str, str] = {
    "WSTG-INFO-03": "metafiles",   # Review Webserver Metafiles
    "WSTG-INFO-04": "common",      # Enumerate Applications on Web Server
    "WSTG-INFO-06": "api",         # Identify Application Entry Points
    "WSTG-CONF-03": "extensions",  # Test File Extension Handling
    "WSTG-CONF-04": "backup",      # Review Old Backup and Unreferenced Files
    "WSTG-CONF-05": "admin",       # Enumerate Admin Interfaces
    "WSTG-CONF-09": "backup",      # Test File Permission (.git/.svn exposure — same shape as backup files)
    "WSTG-IDNT-04": "usernames",   # Test for Account Enumeration
    "WSTG-IDNT-05": "usernames",   # Weak or Unenforced Username Policy
    "WSTG-ATHN-04": "admin",       # Bypassing Authentication Schema (forced browsing to protected pages)
    "WSTG-BUSL-08": "extensions",  # Upload of Unexpected File Types
}

# Maps a checklist item ID to the nuclei template tags actually relevant
# to that test. NucleiTool.build_command() has one fixed tag set
# ("misconfig,exposure,headers,tech") baked in as its own default — fine
# for the handful of items that default genuinely suits (WSTG-CONF-02's
# "check for verbose errors/exposed configs", WSTG-INFO-08/09's
# fingerprinting), but nuclei is also mapped to ~20 Input
# Validation/Authorization/Client-side items (XSS, SQLi-adjacent, SSRF,
# SSTI, XXE, CORS, GraphQL, ...) that fixed tag set would never load
# templates for — running "nuclei" from e.g. the SSRF item would silently
# run the exact same generic misconfig scan as every other nuclei-mapped
# item instead of anything that actually tests for SSRF. This dict lets
# the backend swap in the right `-tags` value per item, same pattern as
# WORDLIST_CATEGORY above. Items not listed here keep nuclei's own
# built-in default, because that default already suits them.
NUCLEI_TAGS: dict[str, str] = {
    "WSTG-INFO-05": "exposure,token",       # Review Webpage Content for Info Leakage
    "WSTG-CONF-05": "exposure,panel",       # Enumerate Admin Interfaces
    "WSTG-CONF-10": "takeover",             # Test for Subdomain Takeover
    "WSTG-CONF-11": "exposure,misconfig",   # Test Cloud Storage
    "WSTG-ATHN-02": "default-login",        # Test for Default Credentials
    "WSTG-ATHN-04": "exposure,unauth",      # Bypassing Authentication Schema
    "WSTG-ATHZ-01": "lfi",                  # Directory Traversal / File Include
    "WSTG-ATHZ-02": "exposure,unauth",      # Bypassing Authorization Schema
    "WSTG-SESS-05": "csrf",                 # Cross Site Request Forgery
    "WSTG-INPV-01": "xss",                  # Reflected XSS
    "WSTG-INPV-02": "xss",                  # Stored XSS
    "WSTG-INPV-06": "ldapi",                # LDAP Injection
    "WSTG-INPV-07": "xxe",                  # XML Injection
    "WSTG-INPV-05": "sqli",                 # SQL Injection
    "WSTG-INPV-08": "injection",            # SSI Injection
    "WSTG-INPV-11": "lfi,rfi",              # Code Injection (LFI/RFI)
    "WSTG-INPV-12": "rce,injection",        # Command Injection
    "WSTG-INPV-15": "smuggling",            # HTTP Splitting/Smuggling
    "WSTG-INPV-17": "injection,misconfig",  # Host Header Injection
    "WSTG-INPV-18": "ssti",                 # Server-side Template Injection
    "WSTG-INPV-19": "ssrf",                 # Server-Side Request Forgery
    "WSTG-ERRH-01": "exposure,misconfig",   # Improper Error Handling
    "WSTG-ERRH-02": "exposure",             # Stack Traces
    "WSTG-CLNT-03": "xss",                  # HTML Injection
    "WSTG-CLNT-04": "redirect",             # Client-side URL Redirect
    "WSTG-CLNT-07": "cors",                 # Cross Origin Resource Sharing
    "WSTG-APIT-01": "graphql",              # Testing GraphQL
}

# Same swap pattern as NUCLEI_TAGS, for curl: CurlTool's own
# build_command() default (-sS -I, headers only) is a fine generic
# "what does this endpoint send back" check, but several tests need
# specific flags/headers to actually be about what they're named for —
# -X OPTIONS for the HTTP-methods test, a spoofed Origin/Host header for
# CORS/host-header-injection tests, etc. Items not listed here keep the
# generic default. Values are the curl args between "curl" and the URL
# (the URL itself is appended by the backend).
CURL_ARGS: dict[str, list[str]] = {
    "WSTG-CONF-06": ["-sS", "-i", "-X", "OPTIONS"],                              # Test HTTP Methods
    "WSTG-CLNT-07": ["-sS", "-i", "-H", "Origin: https://evil-test.example"],    # CORS
    "WSTG-INPV-17": ["-sS", "-i", "-H", "Host: evil-test.example"],              # Host Header Injection
}

# Path appended after the target for a curl/wget check that's about a
# specific well-known file rather than the bare site root (e.g. RIA
# cross domain policy files, robots.txt, a dangling .git directory).
CURL_PATH_SUFFIX: dict[str, str] = {
    "WSTG-CONF-08": "/crossdomain.xml",     # Test RIA Cross Domain Policy
}
WGET_PATH_SUFFIX: dict[str, str] = {
    "WSTG-INFO-03": "/robots.txt",          # Review Webserver Metafiles
    "WSTG-CONF-08": "/crossdomain.xml",     # Test RIA Cross Domain Policy
    "WSTG-CONF-09": "/.git/HEAD",           # Test File Permission
}


def _swap_wordlist_flag(command: list[str], new_path: str) -> list[str]:
    """Replace the value following a `-w` flag in *command*, if present."""
    cmd = list(command)
    for i, tok in enumerate(cmd):
        if tok == "-w" and i + 1 < len(cmd):
            cmd[i + 1] = new_path
            break
    return cmd


def _swap_nuclei_tags(command: list[str], tags: str) -> list[str]:
    """Replace the value following a `-tags` flag, if present."""
    cmd = list(command)
    for i, tok in enumerate(cmd):
        if tok == "-tags" and i + 1 < len(cmd):
            cmd[i + 1] = tags
            break
    return cmd


def _apply_curl_override(command: list[str], item_id: str) -> list[str]:
    """Swap in this test's CURL_ARGS/CURL_PATH_SUFFIX override, if any.

    *command* is always ["curl", ...flags..., url] (CurlTool.build_command()
    puts the URL last), so the override either replaces the flags (args)
    or appends a path onto the URL (suffix), or both.
    """
    args = CURL_ARGS.get(item_id)
    suffix = CURL_PATH_SUFFIX.get(item_id, "")
    if not args and not suffix:
        return command
    flags = args if args else command[1:-1]
    url = command[-1] + suffix
    return ["curl", *flags, url]


def _apply_wget_override(command: list[str], item_id: str) -> list[str]:
    """Swap in this test's WGET_PATH_SUFFIX override, if any."""
    suffix = WGET_PATH_SUFFIX.get(item_id, "")
    if not suffix:
        return command
    return [*command[:-1], command[-1] + suffix]


_NMAP_OPEN_PORT_RE = re.compile(r"^(\d+)/(tcp|udp)\s+open\S*", re.MULTILINE)

# Items whose nmap default is meant to be "every open port found earlier
# in the engagement" rather than a fixed port list — currently just
# OSCP-ENUM-02 ("Detailed -sV -sC scan of every open port found above").
# nmap_tool.py's own `fast=False` default is a *web*-port list
# (80/443/8080/...) since that's the right default for the handful of
# WSTG items that also map to nmap; without this override, following the
# OSCP checklist in order after OSCP-ENUM-01 (a real full-range port scan)
# silently re-scanned only those web ports and dropped everything else
# OSCP-ENUM-01 had just found (FTP, SSH, ...) — confirmed against a real
# target: OSCP-ENUM-01 found 21/22/80 open, OSCP-ENUM-02's unedited
# "full" command only ever touched port 80.
_NMAP_DISCOVERED_PORTS_ITEMS = frozenset({"OSCP-ENUM-02"})


def _discovered_ports(engagement: Engagement) -> list[str]:
    """Every open port nmap has already reported anywhere on this
    engagement's checklist — numeric-sorted, deduplicated. naabu isn't
    read here: it only ever confirms ports nmap would already have found
    on the same engagement, and its bare "host:port" lines carry no
    open/closed state to filter on in the first place.
    """
    ports: set[str] = set()
    for other in engagement.checklist_items:
        output = other.tool_outputs.get("nmap", "")
        if not output:
            continue
        ports.update(m.group(1) for m in _NMAP_OPEN_PORT_RE.finditer(output))
    return sorted(ports, key=int)


def _apply_nmap_override(
    command: list[str], item_id: str, engagement: Engagement | None
) -> list[str]:
    """Swap OSCP-ENUM-02's `-p <web ports>` for the real ports this
    engagement's own earlier nmap runs already found open, if any exist
    yet. Falls back to the tool's own default (the web-port list) for a
    brand-new engagement with no prior scan to draw from — that default is
    still a reasonable first pass, just not the "every open port found
    above" the item actually asks for once one exists.
    """
    if item_id not in _NMAP_DISCOVERED_PORTS_ITEMS or engagement is None:
        return command
    ports = _discovered_ports(engagement)
    if not ports:
        return command
    cmd = list(command)
    for i, tok in enumerate(cmd):
        if tok == "-p" and i + 1 < len(cmd):
            cmd[i + 1] = ",".join(ports)
            break
    return cmd


# nmap's table line for a service with a detected version, e.g.
# "21/tcp   open  ftp     vsftpd 3.0.3" — SERVICE is always one token,
# VERSION is everything after it on the same line (nmap's own NSE script
# output is on separate, indented "|" lines, never appended here).
_NMAP_SERVICE_LINE_RE = re.compile(r"^(\d+)/(?:tcp|udp)\s+open\S*\s+(\S+)\s+(.+)$", re.MULTILINE)

# Service names too generic/likely-patched to make a good default
# exploit-db/Metasploit search term on their own — SSH is near-always
# already at a current, unexploitable point release, and "http" is a
# transport, not a product name (the real product — Apache, a CMS, ... —
# usually isn't in nmap's own SERVICE column). Skipped first so a more
# specific hit (ftp, smb, a database, ...) wins when several services were
# found; still used as a last resort if nothing else is available.
_LOW_PRIORITY_SERVICES = frozenset({"ssh", "http", "https", "domain", "tcpwrapped"})

# Items whose searchsploit/metasploit default is meant to search by the
# most interesting service+version this engagement's own nmap runs
# already found, instead of the bare target IP/hostname — confirmed
# against a real target that the un-overridden default
# (`searchsploit --disable-colour 10.129.34.27`) returns "No Results"
# every time (searchsploit/metasploit both search by product name, not
# target), while the exact same tool given the real product string
# ("vsftpd 3.0.3", read off this engagement's own nmap output) finds a
# real match. OSCP-PRIVL-02/03 and OSCP-PRIVW-02/03 (the other checklist
# items mapped to these two tools) are deliberately NOT included here —
# those are OS/kernel exploit lookups, not network-service lookups, and
# a vsftpd version string would be actively wrong as their default.
_EXPLOIT_LOOKUP_ITEMS = frozenset({"OSCP-VULN-02", "OSCP-VULN-04"})


def discovered_service_candidates(engagement: Engagement) -> list[str]:
    """Every distinct `<service> <version>` string nmap has already found
    anywhere on this engagement, "most interesting first" — a named
    service other than _LOW_PRIORITY_SERVICES sorted by port, then the
    low-priority ones (ssh/http/...) the same way. Used both to pick
    OSCP-VULN-02/04's actual default (see _apply_exploit_lookup_override,
    which just takes the first entry) and to show the tester every *other*
    candidate as a hint in the Run Tool dialog — the auto-pick is a
    reasonable starting point, not the only service worth a lookup; a
    target with several open services (this one included — ftp, ssh, http
    all had a version) genuinely can have more than one exploitable
    product. Empty list if nmap hasn't found anything with a version yet.
    """
    candidates: list[tuple[int, str, str]] = []  # (port, service, version)
    for other in engagement.checklist_items:
        output = other.tool_outputs.get("nmap", "")
        if not output:
            continue
        for m in _NMAP_SERVICE_LINE_RE.finditer(output):
            port_str, service, version = m.groups()
            candidates.append((int(port_str), service, version.strip()))
    if not candidates:
        return []
    preferred = sorted(
        (c for c in candidates if c[1].lower() not in _LOW_PRIORITY_SERVICES),
        key=lambda c: c[0],
    )
    low_priority = sorted(
        (c for c in candidates if c[1].lower() in _LOW_PRIORITY_SERVICES),
        key=lambda c: c[0],
    )
    seen: set[str] = set()
    ordered: list[str] = []
    for _, service, version in preferred + low_priority:
        label = f"{service} {version}"
        if label not in seen:
            seen.add(label)
            ordered.append(label)
    return ordered


def _apply_exploit_lookup_override(
    command: list[str], tool_name: str, item_id: str, engagement: Engagement | None
) -> list[str]:
    """Swap OSCP-VULN-02/04's bare-target search term for the most
    interesting service+version this engagement's nmap runs already found
    (see discovered_service_candidates — this just takes its first entry).
    Falls back to the original placeholder when nothing's been scanned
    yet, or nmap found nothing with a version.
    """
    if item_id not in _EXPLOIT_LOOKUP_ITEMS or engagement is None:
        return command
    candidates = discovered_service_candidates(engagement)
    if not candidates:
        return command
    service_version = candidates[0]
    cmd = list(command)
    if tool_name == "searchsploit":
        # build_command()'s shape: [..., "--disable-colour", <target>] —
        # the bare target is always the last token.
        if cmd and cmd[-1] == engagement.target:
            cmd = cmd[:-1] + service_version.split()
    elif tool_name == "metasploit":
        # The target is embedded inside one shell-script argument
        # (`-x "search <target>; exit"`), not a standalone token.
        needle = f"search {engagement.target}; exit"
        for i, tok in enumerate(cmd):
            if tok == needle:
                cmd[i] = f"search {service_version}; exit"
                break
    return cmd


def apply_tool_overrides(
    tool_name: str,
    item_id: str,
    command: list[str],
    *,
    uses_wordlist: bool,
    engagement: Engagement | None = None,
) -> list[str]:
    """Swap this checklist item's recommended wordlist category / nuclei
    tags / curl-wget path+flags / nmap discovered-ports / searchsploit &
    metasploit discovered-service into *command*, if any of those apply.

    Shared by the Run Tool dialog's command-preview endpoint AND the real
    execution path (oculus.orchestrator.Orchestrator.run_tool) — the
    recommendation has to be applied in both places, not just the preview,
    or a tester who runs a tool without first editing the (already correct-
    looking) previewed command gets the tool's plain generic default
    instead of what was actually recommended for this specific test. That
    was a real bug: WORDLIST_CATEGORY/NUCLEI_TAGS previously only affected
    the text shown in the dialog, not what actually executed, unless the
    tester happened to edit the command field first.

    *engagement*, when given, lets the nmap-discovered-ports override (see
    _apply_nmap_override) and the searchsploit/metasploit-discovered-
    service override (see _apply_exploit_lookup_override) look at this
    engagement's own already-recorded scan output; omitted entirely (None)
    short-circuits both branches to a no-op, for any caller that doesn't
    have an engagement loaded.
    """
    cmd = list(command)
    if uses_wordlist:
        category = WORDLIST_CATEGORY.get(item_id)
        if category:
            from .wordlists import recommend_wordlist  # local import: avoid a hard module-load coupling to wordlists.py for callers that never hit this branch
            cmd = _swap_wordlist_flag(cmd, recommend_wordlist(category))
    if tool_name == "nuclei":
        tags = NUCLEI_TAGS.get(item_id)
        if tags:
            cmd = _swap_nuclei_tags(cmd, tags)
    elif tool_name == "curl":
        cmd = _apply_curl_override(cmd, item_id)
    elif tool_name == "wget":
        cmd = _apply_wget_override(cmd, item_id)
    elif tool_name == "nmap":
        cmd = _apply_nmap_override(cmd, item_id, engagement)
    elif tool_name in ("searchsploit", "metasploit"):
        cmd = _apply_exploit_lookup_override(cmd, tool_name, item_id, engagement)
    return cmd


# Human-readable label per category, shown in the Run Tool dialog's
# "recommended for this test" hint.
CATEGORY_LABELS: dict[str, str] = {
    "metafiles": "well-known metafiles (robots.txt, sitemap.xml, ...)",
    "common": "common directories",
    "api": "API endpoints",
    "extensions": "file extension handling",
    "backup": "backup & old files",
    "admin": "admin interfaces",
    "usernames": "username enumeration",
}


def build_checklist() -> list[ChecklistItem]:
    """Return a fresh, ordered list of OWASP WSTG v4.2 checklist items."""
    return [
        # ================================================================
        # 4.1 INFORMATION GATHERING
        # ================================================================
        ChecklistItem(
            id="WSTG-INFO-01",
            name="Search Engine Discovery & Recon",
            description=(
                "Passively enumerate subdomains and associated infrastructure via "
                "subfinder/amass's own aggregated sources (certificate transparency, "
                "DNS datasets, some passive search indexes) to surface exposed assets "
                "the target doesn't advertise directly. This covers the passive-discovery "
                "half of the test automatically; manually supplement with targeted Google/"
                "Bing dorking and Shodan/Censys lookups for cached pages, pastes, and "
                "misconfigured cloud storage — no wrapped tool here does that part."
            ),
            category="Information Gathering",
            category_code="INFO",
            tools=["subfinder", "amass"],
            owasp_ref="WSTG-INFO-01",
            cwe_ids=["CWE-200"],
            references=["https://owasp.org/www-project-web-security-testing-guide/v42/4-Web_Application_Security_Testing/01-Information_Gathering/01-Conduct_Search_Engine_Discovery_Reconnaissance_for_Information_Leakage"],
        ),
        ChecklistItem(
            id="WSTG-INFO-02",
            name="Fingerprint Web Server",
            description=(
                "Identify the web server software, version, and operating system via "
                "banner grabbing, response header analysis, and port scanning. "
                "Known CVEs for outdated versions should be documented."
            ),
            category="Information Gathering",
            category_code="INFO",
            tools=["nmap", "httpx", "whatweb", "curl"],
            owasp_ref="WSTG-INFO-02",
            cwe_ids=["CWE-200"],
            references=["https://owasp.org/www-project-web-security-testing-guide/v42/4-Web_Application_Security_Testing/01-Information_Gathering/02-Fingerprint_Web_Server"],
        ),
        ChecklistItem(
            id="WSTG-INFO-03",
            name="Review Webserver Metafiles",
            description=(
                "Review robots.txt, sitemap.xml, security.txt, humans.txt and similar "
                "metafiles for internal paths, disallowed endpoints, or data not intended "
                "to be indexed."
            ),
            category="Information Gathering",
            category_code="INFO",
            tools=["httpx", "ffuf", "wget"],
            owasp_ref="WSTG-INFO-03",
            cwe_ids=["CWE-200"],
        ),
        ChecklistItem(
            id="WSTG-INFO-04",
            name="Enumerate Applications on Web Server",
            description=(
                "Identify all web applications hosted on the same server: virtual hosts, "
                "non-standard ports, and directory-based path applications. Each sub-app "
                "expands the attack surface."
            ),
            category="Information Gathering",
            category_code="INFO",
            tools=["nmap", "httpx", "ffuf"],
            owasp_ref="WSTG-INFO-04",
            cwe_ids=["CWE-205"],
        ),
        ChecklistItem(
            id="WSTG-INFO-05",
            name="Review Webpage Content for Information Leakage",
            description=(
                "Analyse HTML source, inline JavaScript, and asset comments for sensitive "
                "data: hardcoded credentials, internal IP addresses, API keys, developer "
                "comments, or staging/debug endpoints. katana/httpx crawl and fetch the "
                "content for manual review; nuclei's exposure/token templates additionally "
                "flag common leaked-secret patterns (API keys, tokens) automatically."
            ),
            category="Information Gathering",
            category_code="INFO",
            tools=["katana", "httpx", "nuclei"],
            owasp_ref="WSTG-INFO-05",
            cwe_ids=["CWE-200", "CWE-312"],
        ),
        ChecklistItem(
            id="WSTG-INFO-06",
            name="Identify Application Entry Points",
            description=(
                "Map all input vectors: HTML forms, URL parameters, REST/GraphQL endpoints, "
                "HTTP headers (cookie, referer, custom), and WebSocket channels. "
                "This inventory drives subsequent injection testing."
            ),
            category="Information Gathering",
            category_code="INFO",
            tools=["katana", "arjun", "ffuf"],
            owasp_ref="WSTG-INFO-06",
            cwe_ids=["CWE-200"],
        ),
        ChecklistItem(
            id="WSTG-INFO-07",
            name="Map Execution Paths Through Application",
            description=(
                "Crawl and manually browse the application to document all functional "
                "workflows, authentication-state transitions, and business logic paths. "
                "Screenshot every distinct page state. The official WSTG methodology "
                "names OWASP ZAP's spider explicitly for this — zap's baseline scan "
                "(spider + passive rules, no active attacks) covers that directly, "
                "alongside katana's lighter/faster crawl and gowitness's screenshots."
            ),
            category="Information Gathering",
            category_code="INFO",
            tools=["katana", "gowitness", "zap"],
            owasp_ref="WSTG-INFO-07",
            cwe_ids=["CWE-200"],
        ),
        ChecklistItem(
            id="WSTG-INFO-08",
            name="Fingerprint Web Application Framework",
            description=(
                "Identify the framework or CMS (WordPress, Laravel, Django, Rails, etc.) "
                "and version. Match the fingerprint against known CVEs. For CMSes, run "
                "specialised scanners (wpscan, droopescan)."
            ),
            category="Information Gathering",
            category_code="INFO",
            tools=["whatweb", "nuclei", "wpscan"],
            owasp_ref="WSTG-INFO-08",
            cwe_ids=["CWE-200"],
        ),
        ChecklistItem(
            id="WSTG-INFO-09",
            name="Fingerprint Web Application",
            description=(
                "Confirm the specific application, version, and installed plugins/themes "
                "using cookies, URL patterns, file hashes, and HTTP headers. "
                "Cross-reference with nuclei fingerprint templates. Note: the official "
                "WSTG v4.2 guide merged this item's methodology into WSTG-INFO-08 "
                "(Fingerprint Web Application Framework) — kept here as its own item "
                "since app/plugin-specific version fingerprinting is a meaningfully "
                "different check from framework-level fingerprinting, but expect real "
                "overlap in what the two find."
            ),
            category="Information Gathering",
            category_code="INFO",
            tools=["whatweb", "nuclei"],
            owasp_ref="WSTG-INFO-09",
            cwe_ids=["CWE-200"],
        ),
        ChecklistItem(
            id="WSTG-INFO-10",
            name="Map Application Architecture",
            description=(
                "Document the full architecture: CDN, load balancers, WAF, reverse proxies, "
                "backend service language, and third-party SaaS. Timing attacks and "
                "header inconsistencies can reveal multi-tier topologies."
            ),
            category="Information Gathering",
            category_code="INFO",
            tools=["wafw00f", "nmap", "httpx"],
            owasp_ref="WSTG-INFO-10",
            cwe_ids=["CWE-200"],
        ),
        # ================================================================
        # 4.2 CONFIGURATION & DEPLOYMENT MANAGEMENT
        # ================================================================
        ChecklistItem(
            id="WSTG-CONF-01",
            name="Test Network Infrastructure Configuration",
            description=(
                "Scan for open ports and exposed services that should not be reachable "
                "from the internet: database ports (3306, 5432), cache (6379), admin "
                "panels, and development servers."
            ),
            category="Configuration Management",
            category_code="CONF",
            tools=["naabu", "nmap"],
            owasp_ref="WSTG-CONF-01",
            cwe_ids=["CWE-16"],
        ),
        ChecklistItem(
            id="WSTG-CONF-02",
            name="Test Application Platform Configuration",
            description=(
                "Check for verbose error messages, directory listings, debug mode enabled, "
                "exposed configuration endpoints (/actuator, /.env, /config.php), and "
                "missing/misconfigured security response headers (CSP, X-Frame-Options, "
                "X-Content-Type-Options, Referrer-Policy, Permissions-Policy)."
            ),
            category="Configuration Management",
            category_code="CONF",
            tools=["nikto", "nuclei", "httpx", "curl"],
            owasp_ref="WSTG-CONF-02",
            cwe_ids=["CWE-16", "CWE-209", "CWE-693"],
        ),
        ChecklistItem(
            id="WSTG-CONF-03",
            name="Test File Extension Handling",
            description=(
                "Verify that dangerous extensions (.bak, .old, .config, .env, .sql, ~) are "
                "blocked or return 404. Misconfigured servers serve source code or "
                "configuration files with these extensions."
            ),
            category="Configuration Management",
            category_code="CONF",
            tools=["ffuf", "gobuster"],
            owasp_ref="WSTG-CONF-03",
            cwe_ids=["CWE-552"],
        ),
        ChecklistItem(
            id="WSTG-CONF-04",
            name="Review Old Backup and Unreferenced Files",
            description=(
                "Brute-force for backup archives and unreferenced files using wordlists. "
                "Common patterns: index.php.bak, .git/HEAD, backup.zip, db_dump.sql. "
                "These frequently expose full source code or credentials."
            ),
            category="Configuration Management",
            category_code="CONF",
            tools=["ffuf", "gobuster", "nuclei"],
            owasp_ref="WSTG-CONF-04",
            cwe_ids=["CWE-530", "CWE-552"],
        ),
        ChecklistItem(
            id="WSTG-CONF-05",
            name="Enumerate Infrastructure and Application Admin Interfaces",
            description=(
                "Discover administrative and management interfaces reachable without "
                "authentication or via default credentials: /admin, /wp-admin, /phpmyadmin, "
                "/manager, /_dashboard, /api/internal."
            ),
            category="Configuration Management",
            category_code="CONF",
            tools=["ffuf", "gobuster", "nuclei"],
            owasp_ref="WSTG-CONF-05",
            cwe_ids=["CWE-284"],
        ),
        ChecklistItem(
            id="WSTG-CONF-06",
            name="Test HTTP Methods",
            description=(
                "Enumerate HTTP methods accepted by the server (OPTIONS). Verify that "
                "PUT, DELETE, TRACE, and CONNECT are disabled. TRACE enables XST attacks; "
                "PUT may allow arbitrary file upload."
            ),
            category="Configuration Management",
            category_code="CONF",
            tools=["nmap", "httpx", "nuclei", "curl"],
            owasp_ref="WSTG-CONF-06",
            cwe_ids=["CWE-16", "CWE-749"],
        ),
        ChecklistItem(
            id="WSTG-CONF-07",
            name="Test HTTP Strict Transport Security",
            description=(
                "Confirm HSTS header is present with max-age ≥ 31536000 and "
                "includeSubDomains. Verify TLS ≥ 1.2 is enforced and weak cipher "
                "suites (RC4, 3DES, NULL) are disabled."
            ),
            category="Configuration Management",
            category_code="CONF",
            tools=["testssl", "httpx", "nuclei", "curl"],
            owasp_ref="WSTG-CONF-07",
            cwe_ids=["CWE-319", "CWE-326"],
        ),
        ChecklistItem(
            id="WSTG-CONF-08",
            name="Test RIA Cross Domain Policy",
            description=(
                "Fetch and review crossdomain.xml (Flash) and clientaccesspolicy.xml "
                "(Silverlight) for overly permissive cross-domain access (allow-access-"
                "from domain=\"*\"), which lets any third-party site make authenticated "
                "cross-origin requests against the application."
            ),
            category="Configuration Management",
            category_code="CONF",
            tools=["httpx", "curl", "wget"],
            owasp_ref="WSTG-CONF-08",
            cwe_ids=["CWE-942"],
        ),
        ChecklistItem(
            id="WSTG-CONF-09",
            name="Test File Permission",
            description=(
                "Check for world-readable/writable files exposed over HTTP: version "
                "control metadata (.git, .svn, .hg), editor swap/backup files, and "
                "server config files with overly permissive access."
            ),
            category="Configuration Management",
            category_code="CONF",
            tools=["ffuf", "nikto", "wget"],
            owasp_ref="WSTG-CONF-09",
            cwe_ids=["CWE-732"],
        ),
        ChecklistItem(
            id="WSTG-CONF-10",
            name="Test for Subdomain Takeover",
            description=(
                "Enumerate all subdomains and check for dangling DNS records pointing to "
                "deprovisioned cloud resources (AWS S3, Azure, GitHub Pages, Heroku). "
                "A takeover allows hosting malicious content under the target domain."
            ),
            category="Configuration Management",
            category_code="CONF",
            tools=["subfinder", "dnsx", "nuclei"],
            owasp_ref="WSTG-CONF-10",
            cwe_ids=["CWE-350"],
        ),
        ChecklistItem(
            id="WSTG-CONF-11",
            name="Test Cloud Storage",
            description=(
                "Identify cloud storage buckets (S3, Azure Blob, GCS) referenced by the "
                "application or guessable from its name, and check for public read/write "
                "access, directory listing, and sensitive files inside."
            ),
            category="Configuration Management",
            category_code="CONF",
            tools=["nuclei", "ffuf"],
            owasp_ref="WSTG-CONF-11",
            cwe_ids=["CWE-284", "CWE-668"],
        ),
        # ================================================================
        # 4.3 IDENTITY MANAGEMENT
        # ================================================================
        ChecklistItem(
            id="WSTG-IDNT-01",
            name="Test Role Definitions",
            description=(
                "Document every distinct role the application defines and the "
                "privilege boundary each implies — the baseline a later authorization "
                "test (WSTG-ATHZ) checks enforcement against. Inherently manual: no "
                "tool can infer intended role semantics from the outside."
            ),
            category="Identity Management",
            category_code="IDNT",
            tools=[],
            owasp_ref="WSTG-IDNT-01",
            cwe_ids=["CWE-269"],
        ),
        ChecklistItem(
            id="WSTG-IDNT-02",
            name="Test User Registration Process",
            description=(
                "Review the self-registration flow for identity verification gaps: can "
                "an account be created with someone else's email/identity, are duplicate "
                "accounts prevented, is the role assigned at signup ever attacker-"
                "controllable (e.g. a hidden 'role' field)?"
            ),
            category="Identity Management",
            category_code="IDNT",
            tools=["katana"],
            owasp_ref="WSTG-IDNT-02",
            cwe_ids=["CWE-287"],
        ),
        ChecklistItem(
            id="WSTG-IDNT-03",
            name="Test Account Provisioning Process",
            description=(
                "Confirm only authorized parties can provision new accounts (especially "
                "elevated ones), and that de-provisioning on offboarding actually revokes "
                "access rather than just disabling a UI login."
            ),
            category="Identity Management",
            category_code="IDNT",
            tools=[],
            owasp_ref="WSTG-IDNT-03",
            cwe_ids=["CWE-284"],
        ),
        ChecklistItem(
            id="WSTG-IDNT-04",
            name="Test for Account Enumeration and Guessable User Account",
            description=(
                "Probe login/registration/password-reset endpoints for a response "
                "difference between a valid and invalid username (different error "
                "message, status code, response time, or redirect) — lets an attacker "
                "build a list of real accounts to target with credential attacks."
            ),
            category="Identity Management",
            category_code="IDNT",
            tools=["ffuf"],
            owasp_ref="WSTG-IDNT-04",
            cwe_ids=["CWE-203", "CWE-204"],
        ),
        ChecklistItem(
            id="WSTG-IDNT-05",
            name="Testing for Weak or Unenforced Username Policy",
            description=(
                "Check whether usernames are predictable (sequential IDs, "
                "firstname.lastname with no variation) and whether the registration "
                "form leaks which usernames are already taken."
            ),
            category="Identity Management",
            category_code="IDNT",
            tools=["ffuf"],
            owasp_ref="WSTG-IDNT-05",
            cwe_ids=["CWE-521"],
        ),
        # ================================================================
        # 4.4 AUTHENTICATION
        # ================================================================
        ChecklistItem(
            id="WSTG-ATHN-01",
            name="Testing for Credentials Transported over an Encrypted Channel",
            description=(
                "Confirm every login form and its submission endpoint are served over "
                "HTTPS only, with no HTTP fallback that would let credentials be "
                "captured in plaintext over the wire."
            ),
            category="Authentication",
            category_code="ATHN",
            tools=["testssl", "httpx", "curl"],
            owasp_ref="WSTG-ATHN-01",
            cwe_ids=["CWE-319"],
        ),
        ChecklistItem(
            id="WSTG-ATHN-02",
            name="Test for Default Credentials",
            description=(
                "Try common default/weak username-password pairs (admin:admin, "
                "admin:password, root:toor, ...) against every exposed login — SSH, "
                "admin panels, device management interfaces. A shockingly common "
                "finding on internal/staging systems that were never hardened."
            ),
            category="Authentication",
            category_code="ATHN",
            tools=["hydra", "nuclei"],
            owasp_ref="WSTG-ATHN-02",
            cwe_ids=["CWE-521", "CWE-1392"],
        ),
        ChecklistItem(
            id="WSTG-ATHN-03",
            name="Test for Weak Lock Out Mechanism",
            description=(
                "Attempt repeated failed logins and confirm the account/IP is "
                "throttled or locked after a reasonable number of tries. No lockout "
                "means credential-stuffing and brute-force attacks run unimpeded."
            ),
            category="Authentication",
            category_code="ATHN",
            tools=["hydra"],
            owasp_ref="WSTG-ATHN-03",
            cwe_ids=["CWE-307"],
        ),
        ChecklistItem(
            id="WSTG-ATHN-04",
            name="Testing for Bypassing Authentication Schema",
            description=(
                "Try to reach authenticated-only pages/APIs directly (forced browsing, "
                "parameter tampering, header injection like X-Original-URL) without "
                "ever completing the login flow."
            ),
            category="Authentication",
            category_code="ATHN",
            tools=["ffuf", "nuclei"],
            owasp_ref="WSTG-ATHN-04",
            cwe_ids=["CWE-288"],
        ),
        ChecklistItem(
            id="WSTG-ATHN-05",
            name="Testing for Vulnerable Remember Password",
            description=(
                "Check how 'remember me' persists a session — a long-lived plaintext/"
                "reversible cookie or the password itself cached client-side is a "
                "durable credential-theft target."
            ),
            category="Authentication",
            category_code="ATHN",
            tools=["httpx"],
            owasp_ref="WSTG-ATHN-05",
            cwe_ids=["CWE-522"],
        ),
        ChecklistItem(
            id="WSTG-ATHN-06",
            name="Testing for Browser Cache Weaknesses",
            description=(
                "Confirm authenticated pages set Cache-Control: no-store (not just "
                "no-cache) so sensitive content isn't recoverable from local browser "
                "cache/back-button after logout on a shared machine."
            ),
            category="Authentication",
            category_code="ATHN",
            tools=["httpx", "curl"],
            owasp_ref="WSTG-ATHN-06",
            cwe_ids=["CWE-525"],
        ),
        ChecklistItem(
            id="WSTG-ATHN-07",
            name="Testing for Weak Password Policy",
            description=(
                "Review the registration/password-change form's enforced minimum "
                "length, complexity, and rejection of common/breached passwords "
                "(rockyou-style lists) — weak policy is a root cause behind most "
                "successful credential attacks."
            ),
            category="Authentication",
            category_code="ATHN",
            tools=[],
            owasp_ref="WSTG-ATHN-07",
            cwe_ids=["CWE-521"],
        ),
        ChecklistItem(
            id="WSTG-ATHN-08",
            name="Testing for Weak Security Question Answer",
            description=(
                "If security questions gate account recovery, confirm the questions "
                "aren't trivially OSINT-able (mother's maiden name, first pet) and "
                "answers aren't guessable/brute-forceable without lockout."
            ),
            category="Authentication",
            category_code="ATHN",
            tools=[],
            owasp_ref="WSTG-ATHN-08",
            cwe_ids=["CWE-640"],
        ),
        ChecklistItem(
            id="WSTG-ATHN-09",
            name="Testing for Weak Password Change or Reset Functionalities",
            description=(
                "Test the password-reset flow for a predictable/guessable reset token, "
                "a token that doesn't expire or isn't invalidated after use, and whether "
                "the old password is required to set a new one while authenticated."
            ),
            category="Authentication",
            category_code="ATHN",
            tools=["katana"],
            owasp_ref="WSTG-ATHN-09",
            cwe_ids=["CWE-640"],
        ),
        ChecklistItem(
            id="WSTG-ATHN-10",
            name="Testing for Weaker Authentication in Alternative Channel",
            description=(
                "Check whether a mobile app, legacy API, or 'classic site' alternate "
                "channel enforces weaker authentication (no MFA, no lockout, an older "
                "auth scheme) than the primary web flow — attackers pick the weakest door."
            ),
            category="Authentication",
            category_code="ATHN",
            tools=["httpx"],
            owasp_ref="WSTG-ATHN-10",
            cwe_ids=["CWE-303"],
        ),
        # ================================================================
        # 4.5 AUTHORIZATION
        # ================================================================
        ChecklistItem(
            id="WSTG-ATHZ-01",
            name="Testing Directory Traversal File Include",
            description=(
                "Fuzz any input that builds a filesystem path (file/page/template "
                "parameters) with ../ traversal sequences and null-byte/encoding "
                "tricks to read files outside the intended directory, or trigger "
                "local/remote file inclusion."
            ),
            category="Authorization",
            category_code="ATHZ",
            tools=["nuclei", "ffuf"],
            owasp_ref="WSTG-ATHZ-01",
            cwe_ids=["CWE-22", "CWE-98"],
        ),
        ChecklistItem(
            id="WSTG-ATHZ-02",
            name="Testing for Bypassing Authorization Schema",
            description=(
                "Access another role's functionality/data by tampering with role/"
                "permission parameters, replaying a lower-privilege token against a "
                "higher-privilege endpoint, or hitting an endpoint the UI never links to."
            ),
            category="Authorization",
            category_code="ATHZ",
            tools=["nuclei"],
            owasp_ref="WSTG-ATHZ-02",
            cwe_ids=["CWE-285"],
        ),
        ChecklistItem(
            id="WSTG-ATHZ-03",
            name="Testing for Privilege Escalation",
            description=(
                "Attempt vertical (low-priv user gains admin function) and horizontal "
                "(user A performs an action scoped to user B) privilege escalation "
                "across every role boundary identified in WSTG-IDNT-01."
            ),
            category="Authorization",
            category_code="ATHZ",
            tools=[],
            owasp_ref="WSTG-ATHZ-03",
            cwe_ids=["CWE-269"],
        ),
        ChecklistItem(
            id="WSTG-ATHZ-04",
            name="Testing for Insecure Direct Object References",
            description=(
                "Increment/guess an object identifier in a URL or API call (order ID, "
                "invoice number, user ID) to access another user's record without an "
                "authorization check on the server side."
            ),
            category="Authorization",
            category_code="ATHZ",
            tools=["ffuf"],
            owasp_ref="WSTG-ATHZ-04",
            cwe_ids=["CWE-639"],
        ),
        # ================================================================
        # 4.6 SESSION MANAGEMENT
        # ================================================================
        ChecklistItem(
            id="WSTG-SESS-01",
            name="Testing for Session Management Schema",
            description=(
                "Analyse how session tokens are generated (randomness/entropy, "
                "predictability across multiple logins) and where they're transmitted "
                "(cookie vs. URL vs. body) — a weak scheme undermines every other "
                "session-management defense below."
            ),
            category="Session Management",
            category_code="SESS",
            tools=["httpx", "curl"],
            owasp_ref="WSTG-SESS-01",
            cwe_ids=["CWE-330"],
        ),
        ChecklistItem(
            id="WSTG-SESS-02",
            name="Testing for Cookies Attributes",
            description=(
                "Verify every session cookie sets Secure, HttpOnly, and an appropriate "
                "SameSite value — missing flags expose the cookie to network sniffing, "
                "XSS-driven theft, or CSRF respectively."
            ),
            category="Session Management",
            category_code="SESS",
            tools=["httpx", "curl"],
            owasp_ref="WSTG-SESS-02",
            cwe_ids=["CWE-614", "CWE-1004"],
        ),
        ChecklistItem(
            id="WSTG-SESS-03",
            name="Testing for Session Fixation",
            description=(
                "Set a known session ID before authenticating and check whether the "
                "server issues a *new* ID on login — if it keeps the pre-auth one, an "
                "attacker who planted it can hijack the now-authenticated session."
            ),
            category="Session Management",
            category_code="SESS",
            tools=[],
            owasp_ref="WSTG-SESS-03",
            cwe_ids=["CWE-384"],
        ),
        ChecklistItem(
            id="WSTG-SESS-04",
            name="Testing for Exposed Session Variables",
            description=(
                "Check for session tokens/identifiers leaking into URLs (and therefore "
                "browser history, proxy/server logs, and the Referer header sent to "
                "third-party resources on the page)."
            ),
            category="Session Management",
            category_code="SESS",
            tools=["katana", "httpx"],
            owasp_ref="WSTG-SESS-04",
            cwe_ids=["CWE-598"],
        ),
        ChecklistItem(
            id="WSTG-SESS-05",
            name="Testing for Cross Site Request Forgery",
            description=(
                "Check whether state-changing requests (form posts, JSON APIs) require "
                "an unpredictable per-session/per-request anti-CSRF token, and whether "
                "that token is actually validated server-side rather than just present."
            ),
            category="Session Management",
            category_code="SESS",
            tools=["nuclei"],
            owasp_ref="WSTG-SESS-05",
            cwe_ids=["CWE-352"],
        ),
        ChecklistItem(
            id="WSTG-SESS-06",
            name="Testing for Logout Functionality",
            description=(
                "Confirm logout actually invalidates the session server-side (not just "
                "clears the client-side cookie) — replay the pre-logout token afterward "
                "and confirm it's rejected."
            ),
            category="Session Management",
            category_code="SESS",
            tools=[],
            owasp_ref="WSTG-SESS-06",
            cwe_ids=["CWE-613"],
        ),
        ChecklistItem(
            id="WSTG-SESS-07",
            name="Testing Session Timeout",
            description=(
                "Confirm an idle session expires within a reasonable window (both "
                "client-side and, more importantly, server-side) rather than staying "
                "valid indefinitely."
            ),
            category="Session Management",
            category_code="SESS",
            tools=[],
            owasp_ref="WSTG-SESS-07",
            cwe_ids=["CWE-613"],
        ),
        ChecklistItem(
            id="WSTG-SESS-08",
            name="Testing for Session Puzzling",
            description=(
                "Check whether a session attribute set in one workflow (e.g. a "
                "multi-step registration) gets reused/trusted in a different, "
                "unrelated workflow in a way that skips a check it wasn't meant to."
            ),
            category="Session Management",
            category_code="SESS",
            tools=[],
            owasp_ref="WSTG-SESS-08",
            cwe_ids=["CWE-841"],
        ),
        ChecklistItem(
            id="WSTG-SESS-09",
            name="Testing for Session Hijacking",
            description=(
                "Assess whether a captured session token (via XSS, network sniffing on "
                "a non-HTTPS path, or a shared/public machine) is sufficient alone to "
                "impersonate the user — no additional binding (IP/device fingerprint) "
                "to make a stolen token less useful."
            ),
            category="Session Management",
            category_code="SESS",
            tools=["testssl"],
            owasp_ref="WSTG-SESS-09",
            cwe_ids=["CWE-384"],
        ),
        # ================================================================
        # 4.7 INPUT VALIDATION
        # ================================================================
        ChecklistItem(
            id="WSTG-INPV-01",
            name="Testing for Reflected Cross Site Scripting",
            description=(
                "Inject script payloads into every input (query params, form "
                "fields, headers) and check whether the target reflects them back "
                "unencoded into the response HTML — the classic XSS entry point."
            ),
            category="Input Validation",
            category_code="INPV",
            tools=["dalfox", "nuclei"],
            owasp_ref="WSTG-INPV-01",
            cwe_ids=["CWE-79"],
        ),
        ChecklistItem(
            id="WSTG-INPV-02",
            name="Testing for Stored Cross Site Scripting",
            description=(
                "Submit script payloads into any field that's persisted and later "
                "rendered back to the same or a different user (comments, profile "
                "fields, support tickets) — higher-impact than reflected XSS since it "
                "fires on every subsequent view."
            ),
            category="Input Validation",
            category_code="INPV",
            tools=["nuclei"],
            owasp_ref="WSTG-INPV-02",
            cwe_ids=["CWE-79"],
        ),
        ChecklistItem(
            id="WSTG-INPV-03",
            name="Testing for HTTP Verb Tampering",
            description=(
                "Re-send a protected request with a different HTTP verb (GET instead "
                "of POST, or an unexpected one) — some access-control middleware only "
                "guards the verb it expects, letting others slip through."
            ),
            category="Input Validation",
            category_code="INPV",
            tools=["nmap", "nuclei"],
            owasp_ref="WSTG-INPV-03",
            cwe_ids=["CWE-436"],
        ),
        ChecklistItem(
            id="WSTG-INPV-04",
            name="Testing for HTTP Parameter Pollution",
            description=(
                "Submit the same parameter name multiple times in one request "
                "(?id=1&id=2) — different frameworks/servers pick the first, last, or "
                "concatenate, creating parsing inconsistencies that bypass filters."
            ),
            category="Input Validation",
            category_code="INPV",
            tools=["nuclei", "ffuf"],
            owasp_ref="WSTG-INPV-04",
            cwe_ids=["CWE-235"],
        ),
        ChecklistItem(
            id="WSTG-INPV-05",
            name="Testing for SQL Injection",
            description=(
                "Test every input that reaches a database query for SQL injection: "
                "boolean-based, error-based, UNION-based, and time-based blind, across "
                "whatever back-end DBMS is in play (MySQL, PostgreSQL, MSSQL, Oracle, "
                "MS Access, or a NoSQL/ORM equivalent — sqlmap fingerprints and adapts "
                "automatically). One of the highest-impact, most consequential web "
                "vulnerabilities."
            ),
            category="Input Validation",
            category_code="INPV",
            tools=["sqlmap", "nuclei"],
            owasp_ref="WSTG-INPV-05",
            cwe_ids=["CWE-89"],
        ),
        ChecklistItem(
            id="WSTG-INPV-06",
            name="Testing for LDAP Injection",
            description=(
                "Inject LDAP filter metacharacters (*, (, ), \\, NUL) into inputs that "
                "reach a directory-service query (login forms backed by AD/LDAP are "
                "the classic case) to bypass authentication or exfiltrate directory data."
            ),
            category="Input Validation",
            category_code="INPV",
            tools=["nuclei"],
            owasp_ref="WSTG-INPV-06",
            cwe_ids=["CWE-90"],
        ),
        ChecklistItem(
            id="WSTG-INPV-07",
            name="Testing for XML Injection",
            description=(
                "Test XML-consuming endpoints for injected elements/entities, "
                "including XXE (external entity) payloads that can read local files "
                "or trigger SSRF via a malicious DOCTYPE declaration."
            ),
            category="Input Validation",
            category_code="INPV",
            tools=["nuclei"],
            owasp_ref="WSTG-INPV-07",
            cwe_ids=["CWE-91", "CWE-611"],
        ),
        ChecklistItem(
            id="WSTG-INPV-08",
            name="Testing for SSI Injection",
            description=(
                "On servers with Server-Side Includes enabled, test whether user "
                "input reaches an SSI directive (<!--#exec cmd=\"...\"-->) unescaped, "
                "which leads directly to remote command execution."
            ),
            category="Input Validation",
            category_code="INPV",
            tools=["nuclei"],
            owasp_ref="WSTG-INPV-08",
            cwe_ids=["CWE-97"],
        ),
        ChecklistItem(
            id="WSTG-INPV-09",
            name="Testing for XPath Injection",
            description=(
                "Inject XPath metacharacters into inputs that build an XPath query "
                "against XML data storage/auth — similar impact to SQL injection but "
                "against XML instead of a relational database."
            ),
            category="Input Validation",
            category_code="INPV",
            tools=[],
            owasp_ref="WSTG-INPV-09",
            cwe_ids=["CWE-643"],
        ),
        ChecklistItem(
            id="WSTG-INPV-10",
            name="Testing for IMAP SMTP Injection",
            description=(
                "Inject IMAP/SMTP command sequences (CRLF-separated) into inputs that "
                "reach a mail server (contact forms, password-reset emails) to smuggle "
                "extra commands or headers into the mail transaction."
            ),
            category="Input Validation",
            category_code="INPV",
            tools=[],
            owasp_ref="WSTG-INPV-10",
            cwe_ids=["CWE-93", "CWE-147"],
        ),
        ChecklistItem(
            id="WSTG-INPV-11",
            name="Testing for Code Injection",
            description=(
                "Test for local file inclusion (an input controls which local file a "
                "script includes/executes) and remote file inclusion (the include "
                "target is a URL the attacker controls) — both can lead to full "
                "code execution."
            ),
            category="Input Validation",
            category_code="INPV",
            tools=["nuclei", "ffuf"],
            owasp_ref="WSTG-INPV-11",
            cwe_ids=["CWE-94", "CWE-98"],
        ),
        ChecklistItem(
            id="WSTG-INPV-12",
            name="Testing for Command Injection",
            description=(
                "Test inputs that might reach a shell/OS command (file names, "
                "hostnames passed to ping/nslookup-style utilities, export/convert "
                "features) for OS command injection using shell metacharacters."
            ),
            category="Input Validation",
            category_code="INPV",
            tools=["commix", "nuclei"],
            owasp_ref="WSTG-INPV-12",
            cwe_ids=["CWE-78"],
        ),
        ChecklistItem(
            id="WSTG-INPV-13",
            name="Testing for Format String Injection",
            description=(
                "In native/C-backed components, test whether user input reaches a "
                "format-string function (printf-family) directly — %x/%s/%n sequences "
                "can leak memory or crash the process."
            ),
            category="Input Validation",
            category_code="INPV",
            tools=[],
            owasp_ref="WSTG-INPV-13",
            cwe_ids=["CWE-134"],
        ),
        ChecklistItem(
            id="WSTG-INPV-14",
            name="Testing for Incubated Vulnerability",
            description=(
                "Look for multi-stage attacks where an initial low-impact upload/"
                "injection (e.g. an image with embedded payload) lies dormant until a "
                "later, separate action triggers it."
            ),
            category="Input Validation",
            category_code="INPV",
            tools=[],
            owasp_ref="WSTG-INPV-14",
            cwe_ids=["CWE-73"],
        ),
        ChecklistItem(
            id="WSTG-INPV-15",
            name="Testing for HTTP Splitting Smuggling",
            description=(
                "Test for CRLF injection into response headers (response splitting) "
                "and for front-end/back-end request-parsing disagreements (request "
                "smuggling) that let one request be interpreted as two."
            ),
            category="Input Validation",
            category_code="INPV",
            tools=["nuclei"],
            owasp_ref="WSTG-INPV-15",
            cwe_ids=["CWE-113", "CWE-444"],
        ),
        ChecklistItem(
            id="WSTG-INPV-16",
            name="Testing for HTTP Incoming Requests",
            description=(
                "Monitor/review raw incoming request handling for anomalies — "
                "malformed headers, unexpected verbs, or oversized requests the "
                "front-end silently normalizes in a way that hides an attack from "
                "logging/WAF inspection."
            ),
            category="Input Validation",
            category_code="INPV",
            tools=[],
            owasp_ref="WSTG-INPV-16",
            cwe_ids=["CWE-444"],
        ),
        ChecklistItem(
            id="WSTG-INPV-17",
            name="Testing for Host Header Injection",
            description=(
                "Send requests with a tampered Host header and check whether the "
                "application trusts it for password-reset links, cache keys, or "
                "routing decisions — enables password-reset poisoning and cache "
                "poisoning."
            ),
            category="Input Validation",
            category_code="INPV",
            tools=["nuclei", "httpx", "curl"],
            owasp_ref="WSTG-INPV-17",
            cwe_ids=["CWE-644"],
        ),
        ChecklistItem(
            id="WSTG-INPV-18",
            name="Testing for Server-side Template Injection",
            description=(
                "Inject template-engine syntax ({{7*7}}, ${7*7}, etc.) into inputs "
                "that might be rendered through a server-side template engine — "
                "confirmed evaluation usually escalates directly to remote code "
                "execution."
            ),
            category="Input Validation",
            category_code="INPV",
            tools=["nuclei"],
            owasp_ref="WSTG-INPV-18",
            cwe_ids=["CWE-1336"],
        ),
        ChecklistItem(
            id="WSTG-INPV-19",
            name="Testing for Server-Side Request Forgery",
            description=(
                "Find any server-side feature that fetches a URL on the attacker's "
                "behalf (webhooks, PDF/image renderers, 'import from URL') and redirect "
                "it at internal-only services, cloud metadata endpoints (169.254.169.254), "
                "or localhost."
            ),
            category="Input Validation",
            category_code="INPV",
            tools=["nuclei"],
            owasp_ref="WSTG-INPV-19",
            cwe_ids=["CWE-918"],
        ),
        # ================================================================
        # 4.8 TESTING FOR ERROR HANDLING
        # ================================================================
        ChecklistItem(
            id="WSTG-ERRH-01",
            name="Testing for Improper Error Handling",
            description=(
                "Trigger unexpected input/state (malformed data, missing parameters, "
                "wrong content-type) and confirm the application fails to a generic "
                "error page rather than a framework-default error page."
            ),
            category="Error Handling",
            category_code="ERRH",
            tools=["nikto", "nuclei", "curl"],
            owasp_ref="WSTG-ERRH-01",
            cwe_ids=["CWE-209"],
        ),
        ChecklistItem(
            id="WSTG-ERRH-02",
            name="Testing for Stack Traces",
            description=(
                "Look specifically for a full stack trace leaking in an error "
                "response — reveals internal file paths, framework/library versions, "
                "and sometimes query structure, all useful for follow-on attacks."
            ),
            category="Error Handling",
            category_code="ERRH",
            tools=["nuclei", "curl"],
            owasp_ref="WSTG-ERRH-02",
            cwe_ids=["CWE-209", "CWE-200"],
        ),
        # ================================================================
        # 4.9 TESTING FOR WEAK CRYPTOGRAPHY
        # ================================================================
        ChecklistItem(
            id="WSTG-CRYP-01",
            name="Testing for Weak Transport Layer Security",
            description=(
                "Audit the TLS configuration: protocol versions offered (TLS 1.0/1.1 "
                "should be disabled), cipher suite strength, certificate validity/chain, "
                "and known TLS-layer vulnerabilities (Heartbleed, POODLE, etc.)."
            ),
            category="Weak Cryptography",
            category_code="CRYP",
            tools=["testssl"],
            owasp_ref="WSTG-CRYP-01",
            cwe_ids=["CWE-326", "CWE-327"],
        ),
        ChecklistItem(
            id="WSTG-CRYP-02",
            name="Testing for Padding Oracle",
            description=(
                "If the application decrypts CBC-mode ciphertext it receives from the "
                "client (encrypted view state, tokens), check whether padding-validation "
                "errors are distinguishable from other errors — a padding oracle lets an "
                "attacker decrypt/forge ciphertext without the key."
            ),
            category="Weak Cryptography",
            category_code="CRYP",
            tools=[],
            owasp_ref="WSTG-CRYP-02",
            cwe_ids=["CWE-696"],
        ),
        ChecklistItem(
            id="WSTG-CRYP-03",
            name="Testing for Sensitive Information Sent via Unencrypted Channels",
            description=(
                "Beyond the login form (WSTG-ATHN-01), check every channel that might "
                "carry sensitive data — API calls, WebSocket traffic, third-party "
                "widget requests — for a plaintext HTTP path."
            ),
            category="Weak Cryptography",
            category_code="CRYP",
            tools=["httpx", "testssl"],
            owasp_ref="WSTG-CRYP-03",
            cwe_ids=["CWE-319"],
        ),
        ChecklistItem(
            id="WSTG-CRYP-04",
            name="Testing for Weak Encryption",
            description=(
                "Review any application-level (not just transport-level) use of "
                "cryptography — password hashing algorithm, encrypted-at-rest fields, "
                "custom token signing — for weak/deprecated primitives (MD5, SHA1, "
                "unsalted hashes, hardcoded keys)."
            ),
            category="Weak Cryptography",
            category_code="CRYP",
            tools=[],
            owasp_ref="WSTG-CRYP-04",
            cwe_ids=["CWE-327", "CWE-916"],
        ),
        # ================================================================
        # 4.10 BUSINESS LOGIC TESTING
        # ================================================================
        ChecklistItem(
            id="WSTG-BUSL-01",
            name="Test Business Logic Data Validation",
            description=(
                "Submit logically invalid but syntactically valid data (negative "
                "quantities, a discount code with a future start date used early, an "
                "out-of-range but well-formed value) and check whether business rules, "
                "not just input format, are actually validated server-side."
            ),
            category="Business Logic",
            category_code="BUSL",
            tools=[],
            owasp_ref="WSTG-BUSL-01",
            cwe_ids=["CWE-20"],
        ),
        ChecklistItem(
            id="WSTG-BUSL-02",
            name="Test Ability to Forge Requests",
            description=(
                "Replay/modify a request that carries client-side-computed state "
                "(price, total, a hidden 'approved' flag) and confirm the server "
                "recomputes/re-validates it rather than trusting whatever the client sent."
            ),
            category="Business Logic",
            category_code="BUSL",
            tools=[],
            owasp_ref="WSTG-BUSL-02",
            cwe_ids=["CWE-441"],
        ),
        ChecklistItem(
            id="WSTG-BUSL-03",
            name="Test Integrity Checks",
            description=(
                "Tamper with data passed through multiple steps of a workflow (a "
                "multi-page checkout, a signed/hashed hidden field) and confirm any "
                "integrity check on it is actually enforced rather than decorative."
            ),
            category="Business Logic",
            category_code="BUSL",
            tools=[],
            owasp_ref="WSTG-BUSL-03",
            cwe_ids=["CWE-345"],
        ),
        ChecklistItem(
            id="WSTG-BUSL-04",
            name="Test for Process Timing",
            description=(
                "Look for timing differences in a sensitive operation (login, token "
                "validation, discount-code check) that leak information about correct "
                "vs. incorrect input independent of the stated error response."
            ),
            category="Business Logic",
            category_code="BUSL",
            tools=[],
            owasp_ref="WSTG-BUSL-04",
            cwe_ids=["CWE-208"],
        ),
        ChecklistItem(
            id="WSTG-BUSL-05",
            name="Test Number of Times a Function Can Be Used Limits",
            description=(
                "Check whether a function meant to be used a limited number of times "
                "(redeem a coupon once, one free trial per account, a single vote) "
                "actually enforces that limit server-side against repeated/parallel "
                "requests."
            ),
            category="Business Logic",
            category_code="BUSL",
            tools=[],
            owasp_ref="WSTG-BUSL-05",
            cwe_ids=["CWE-799"],
        ),
        ChecklistItem(
            id="WSTG-BUSL-06",
            name="Testing for the Circumvention of Work Flows",
            description=(
                "Try skipping steps in a multi-step process (jump straight to a "
                "'confirmation' page/API without completing prior steps, replay a "
                "later step's request out of order) to see if server-side state "
                "actually enforces the intended sequence."
            ),
            category="Business Logic",
            category_code="BUSL",
            tools=[],
            owasp_ref="WSTG-BUSL-06",
            cwe_ids=["CWE-841"],
        ),
        ChecklistItem(
            id="WSTG-BUSL-07",
            name="Test Defenses Against Application Misuse",
            description=(
                "Probe whether the application detects/throttles obviously abusive "
                "usage patterns (rapid-fire requests, scripted account creation, "
                "scraping) rather than treating every request as legitimate at any rate."
            ),
            category="Business Logic",
            category_code="BUSL",
            tools=[],
            owasp_ref="WSTG-BUSL-07",
            cwe_ids=["CWE-799"],
        ),
        ChecklistItem(
            id="WSTG-BUSL-08",
            name="Test Upload of Unexpected File Types",
            description=(
                "Upload files with an unexpected but structurally valid type/extension "
                "to a file-upload feature (polyglot files, wrong-but-accepted MIME "
                "type, double extensions) and confirm server-side type validation, not "
                "just a client-side/extension check."
            ),
            category="Business Logic",
            category_code="BUSL",
            tools=["ffuf"],
            owasp_ref="WSTG-BUSL-08",
            cwe_ids=["CWE-434"],
        ),
        ChecklistItem(
            id="WSTG-BUSL-09",
            name="Test Upload of Malicious Files",
            description=(
                "Upload a webshell, EICAR test file, or an oversized/zip-bomb file to "
                "confirm the application scans/rejects malicious content and doesn't "
                "serve uploaded files from an executable path."
            ),
            category="Business Logic",
            category_code="BUSL",
            tools=[],
            owasp_ref="WSTG-BUSL-09",
            cwe_ids=["CWE-434"],
        ),
        # ================================================================
        # 4.11 CLIENT-SIDE TESTING
        # ================================================================
        ChecklistItem(
            id="WSTG-CLNT-01",
            name="Testing for DOM-Based Cross Site Scripting",
            description=(
                "Trace client-side JavaScript sources (location.hash, "
                "postMessage, document.referrer) to sinks (innerHTML, eval, "
                "document.write) that render attacker-controlled data without "
                "sanitization — invisible to server-side scanning, needs "
                "browser-based/manual review of the actual JS."
            ),
            category="Client-side Testing",
            category_code="CLNT",
            tools=["katana"],
            owasp_ref="WSTG-CLNT-01",
            cwe_ids=["CWE-79"],
        ),
        ChecklistItem(
            id="WSTG-CLNT-02",
            name="Testing for JavaScript Execution",
            description=(
                "Review bundled/inline JavaScript for dangerous patterns (eval on "
                "external data, dynamically constructed script tags) that an attacker "
                "could reach via a supply-chain or injection vector."
            ),
            category="Client-side Testing",
            category_code="CLNT",
            tools=["katana"],
            owasp_ref="WSTG-CLNT-02",
            cwe_ids=["CWE-95"],
        ),
        ChecklistItem(
            id="WSTG-CLNT-03",
            name="Testing for HTML Injection",
            description=(
                "Inject HTML markup (without script tags) into inputs reflected/stored "
                "in the page — even without JS execution, injected markup can deface "
                "content or build a convincing phishing overlay."
            ),
            category="Client-side Testing",
            category_code="CLNT",
            tools=["nuclei"],
            owasp_ref="WSTG-CLNT-03",
            cwe_ids=["CWE-79", "CWE-80"],
        ),
        ChecklistItem(
            id="WSTG-CLNT-04",
            name="Testing for Client-side URL Redirect",
            description=(
                "Find any redirect parameter (?next=, ?returnUrl=, ?redirect=) and "
                "test whether it accepts an attacker-controlled external URL — enables "
                "convincing phishing via a trusted domain's own redirect."
            ),
            category="Client-side Testing",
            category_code="CLNT",
            tools=["nuclei", "ffuf"],
            owasp_ref="WSTG-CLNT-04",
            cwe_ids=["CWE-601"],
        ),
        ChecklistItem(
            id="WSTG-CLNT-05",
            name="Testing for CSS Injection",
            description=(
                "Check whether user input reaches a stylesheet/style attribute "
                "unescaped — modern CSS (attribute selectors, @import) can exfiltrate "
                "page data or overlay convincing UI without any JavaScript."
            ),
            category="Client-side Testing",
            category_code="CLNT",
            tools=[],
            owasp_ref="WSTG-CLNT-05",
            cwe_ids=["CWE-79"],
        ),
        ChecklistItem(
            id="WSTG-CLNT-06",
            name="Testing for Client-side Resource Manipulation",
            description=(
                "Check whether client-side JS builds a resource reference (an AJAX "
                "URL, a dynamically inserted <script src>) from attacker-influenceable "
                "data without validation."
            ),
            category="Client-side Testing",
            category_code="CLNT",
            tools=["katana"],
            owasp_ref="WSTG-CLNT-06",
            cwe_ids=["CWE-79"],
        ),
        ChecklistItem(
            id="WSTG-CLNT-07",
            name="Testing Cross Origin Resource Sharing",
            description=(
                "Send requests with varied Origin headers and check the "
                "Access-Control-Allow-Origin response — reflecting an arbitrary "
                "Origin (especially combined with Allow-Credentials: true) lets any "
                "site read authenticated responses cross-origin."
            ),
            category="Client-side Testing",
            category_code="CLNT",
            tools=["httpx", "nuclei", "curl"],
            owasp_ref="WSTG-CLNT-07",
            cwe_ids=["CWE-346"],
        ),
        ChecklistItem(
            id="WSTG-CLNT-08",
            name="Testing for Cross Site Flashing",
            description=(
                "For any legacy Flash (.swf) content still served, review its "
                "cross-domain permissions and input handling — largely obsolete as "
                "Flash is EOL, but a leftover .swf on an old server is still a real "
                "finding if present."
            ),
            category="Client-side Testing",
            category_code="CLNT",
            tools=["ffuf"],
            owasp_ref="WSTG-CLNT-08",
            cwe_ids=["CWE-79"],
        ),
        ChecklistItem(
            id="WSTG-CLNT-09",
            name="Testing for Clickjacking",
            description=(
                "Confirm the application sets X-Frame-Options or a frame-ancestors "
                "CSP directive — without it, the page can be iframed on an attacker "
                "site and its UI overlaid to trick users into unintended clicks."
            ),
            category="Client-side Testing",
            category_code="CLNT",
            tools=["httpx", "nuclei", "curl"],
            owasp_ref="WSTG-CLNT-09",
            cwe_ids=["CWE-1021"],
        ),
        ChecklistItem(
            id="WSTG-CLNT-10",
            name="Testing WebSockets",
            description=(
                "Check WebSocket handshake origin validation, whether the connection "
                "requires the same authentication as the rest of the app, and whether "
                "messages are validated server-side like any other input."
            ),
            category="Client-side Testing",
            category_code="CLNT",
            tools=[],
            owasp_ref="WSTG-CLNT-10",
            cwe_ids=["CWE-346"],
        ),
        ChecklistItem(
            id="WSTG-CLNT-11",
            name="Testing Web Messaging",
            description=(
                "Review postMessage() listeners for missing origin checks on the "
                "message sender and for passing message data into a dangerous sink "
                "(innerHTML, eval) unsanitized."
            ),
            category="Client-side Testing",
            category_code="CLNT",
            tools=["katana"],
            owasp_ref="WSTG-CLNT-11",
            cwe_ids=["CWE-346"],
        ),
        ChecklistItem(
            id="WSTG-CLNT-12",
            name="Testing Browser Storage",
            description=(
                "Inspect localStorage/sessionStorage/IndexedDB for sensitive data "
                "(tokens, PII) stored client-side, where it's readable by any script "
                "on the page (including an XSS payload) and persists beyond the session."
            ),
            category="Client-side Testing",
            category_code="CLNT",
            tools=[],
            owasp_ref="WSTG-CLNT-12",
            cwe_ids=["CWE-922"],
        ),
        ChecklistItem(
            id="WSTG-CLNT-13",
            name="Testing for Cross Site Script Inclusion",
            description=(
                "Check whether a sensitive endpoint returns executable JavaScript "
                "(JSONP, a .js-served API) containing user-specific data without "
                "verifying the request's origin — a third-party page can <script "
                "src> it and read the response."
            ),
            category="Client-side Testing",
            category_code="CLNT",
            tools=["httpx"],
            owasp_ref="WSTG-CLNT-13",
            cwe_ids=["CWE-352"],
        ),
        # ================================================================
        # 4.12 API TESTING
        # ================================================================
        ChecklistItem(
            id="WSTG-APIT-01",
            name="Testing GraphQL",
            description=(
                "Check whether GraphQL introspection is exposed in production "
                "(reveals the full schema to an attacker), test for missing "
                "field-level authorization, and probe for resource-exhaustion via "
                "deeply nested or batched queries."
            ),
            category="API Testing",
            category_code="APIT",
            tools=["nuclei", "httpx"],
            owasp_ref="WSTG-APIT-01",
            cwe_ids=["CWE-200", "CWE-285", "CWE-400"],
        ),
    ]


def build_oscp_checklist() -> list[ChecklistItem]:
    """Return a fresh, ordered list of OSCP/PEN-200-style checklist items.

    A genuinely different shape than build_checklist() above, not a
    relabeled copy of it — OSCP methodology is phase-based (recon ->
    enumeration -> vulnerability analysis -> exploitation -> privilege
    escalation -> post-exploitation -> proof/reporting), not organized
    around OWASP's web-application test categories, and "enumeration"
    alone is conventionally ~80% of the actual work (a point repeated
    across essentially every OSCP methodology writeup).

    Automated (real tools already wrapped here) where this app's own
    architecture genuinely allows it — it runs recon/enumeration tools
    against a target over the network, same as the WSTG checklist above.
    Left as `tools=[]` guidance-only where it structurally can't be: this
    app never gets an interactive shell on a compromised host, so
    exploitation, privilege escalation enumeration (LinPEAS/WinPEAS run
    *on* the target, not against it), and post-exploitation are real
    checklist items with real guidance in their description, not tools
    that would just fail or lie about doing something they can't.

    Privilege escalation is split into separate Linux/Windows categories
    (OffSec's own phase list doesn't formally split it, but every
    community methodology writeup treats them as two checklists in
    practice, since the techniques/tools are entirely different) so a
    tester working a Linux box isn't stuck scrolling past Windows-only
    guidance and vice versa. A separate Active Directory category covers
    AD-specific enumeration/attack techniques (LDAP, Kerberos) that don't
    fit either the generic network-service Enumeration category or a
    single host's Privilege Escalation checklist.
    """
    return [
        # ================================================================
        # RECONNAISSANCE
        # ================================================================
        ChecklistItem(
            id="OSCP-RECON-01",
            name="Target Scoping & Passive OSINT",
            description=(
                "Confirm the target(s) actually in scope for this engagement before "
                "touching anything (rules of engagement, IP ranges, excluded hosts). "
                "Passively gather whatever's publicly known about the organization/host "
                "first — no wrapped tool automates this step; it's deliberately manual."
            ),
            category="Reconnaissance",
            category_code="RECON",
            tools=[],
        ),
        ChecklistItem(
            id="OSCP-RECON-02",
            name="Identify Live Hosts",
            description=(
                "Confirm the target actually responds before spending time enumerating "
                "it in depth — a fast ping sweep / top-ports pass first, ahead of the "
                "full port scan below."
            ),
            category="Reconnaissance",
            category_code="RECON",
            tools=["nmap", "naabu"],
        ),
        ChecklistItem(
            id="OSCP-RECON-03",
            name="DNS / Subdomain Enumeration",
            description=(
                "If the target is a domain (not a bare IP), passively enumerate "
                "subdomains and DNS records — additional in-scope hosts are commonly "
                "found this way and each expands the attack surface."
            ),
            category="Reconnaissance",
            category_code="RECON",
            tools=["subfinder", "amass", "dnsx"],
        ),
        # ================================================================
        # ENUMERATION — conventionally the bulk of real OSCP exam/lab time
        # ================================================================
        ChecklistItem(
            id="OSCP-ENUM-01",
            name="Full TCP Port Scan (All 65535 Ports)",
            description=(
                "A top-1000/default nmap scan misses services on non-standard ports — "
                "a real, commonly-cited exam mistake. Run a full-range scan first, then "
                "feed exactly the open ports found into the detailed scan below."
            ),
            category="Enumeration",
            category_code="ENUM",
            tools=["nmap"],
        ),
        ChecklistItem(
            id="OSCP-ENUM-02",
            name="Service/Version Detection & Default Scripts",
            description=(
                "Detailed -sV -sC scan of every open port found above: exact service "
                "versions (needed for the exploit-lookup step later) and nmap's default "
                "NSE script set, which already covers several common misconfig checks "
                "(anonymous FTP, some SMB checks) without a separate tool."
            ),
            category="Enumeration",
            category_code="ENUM",
            tools=["nmap"],
        ),
        ChecklistItem(
            id="OSCP-ENUM-03",
            name="UDP Port Scan",
            description=(
                "A TCP-only scan misses UDP services (SNMP, DNS, TFTP, ...) entirely — "
                "commonly skipped under time pressure, also commonly where an easy win "
                "is sitting."
            ),
            category="Enumeration",
            category_code="ENUM",
            tools=["nmap"],
        ),
        ChecklistItem(
            id="OSCP-ENUM-04",
            name="SMB / NetBIOS Enumeration",
            description=(
                "Users, groups, shares (including anonymous/null-session access), "
                "password policy, and OS/domain info via SMB (usually port 445) — a "
                "very common OSCP/PWK-lab foothold path. Also worth a manual pass with "
                "`smbclient -L //<target>/ -N` (list shares) and `smbclient "
                "//<target>/<share> -N` (browse one) if enum4linux-ng's own share "
                "listing doesn't cover everything."
            ),
            category="Enumeration",
            category_code="ENUM",
            tools=["enum4linux"],
        ),
        ChecklistItem(
            id="OSCP-ENUM-05",
            name="Web Server Directory/File Enumeration",
            description=(
                "Brute-force directories/files and crawl the site on every web port "
                "found — the same web-enumeration tools as the WSTG checklist, just "
                "run here because a web app is one of the most common OSCP-lab entry "
                "points, not because this is a web-app-security test."
            ),
            category="Enumeration",
            category_code="ENUM",
            tools=["ffuf", "gobuster", "katana"],
        ),
        ChecklistItem(
            id="OSCP-ENUM-06",
            name="Web Technology Fingerprinting",
            description=(
                "Identify the exact web server/framework/CMS and version on each web "
                "port — feeds directly into the exploit-lookup step below."
            ),
            category="Enumeration",
            category_code="ENUM",
            tools=["whatweb", "httpx", "nikto"],
        ),
        ChecklistItem(
            id="OSCP-ENUM-07",
            name="Default / Weak Credential Testing",
            description=(
                "Try default and commonly-weak credentials against every exposed login "
                "(SSH, a web login form, FTP, ...) found so far."
            ),
            category="Enumeration",
            category_code="ENUM",
            tools=["hydra"],
        ),
        ChecklistItem(
            id="OSCP-ENUM-08",
            name="Other Service Enumeration (SNMP, etc.)",
            description=(
                "Any other open service nmap's scripts flagged but no wrapped tool "
                "covers directly — e.g. `snmpwalk -c public -v1 <target>` if SNMP is "
                "open. Manual by design; the specific commands depend entirely on "
                "what actually turned up in the port scan."
            ),
            category="Enumeration",
            category_code="ENUM",
            tools=[],
        ),
        ChecklistItem(
            id="OSCP-ENUM-09",
            name="Virtual Host / Subdomain Fuzzing on Web Ports",
            description=(
                "A single IP can quietly host several distinct sites, selected by the "
                "HTTP Host header rather than a URL path — the directory brute-force "
                "above won't find any of them. Fuzz the Host header itself (ffuf's "
                "-H \"Host: FUZZ.<target>\" against a hostname wordlist) on every web "
                "port; a real, commonly-tested OSCP-lab technique distinct from "
                "OSCP-ENUM-05's path-based brute force."
            ),
            category="Enumeration",
            category_code="ENUM",
            tools=["ffuf"],
        ),
        ChecklistItem(
            id="OSCP-ENUM-10",
            name="Database Service Enumeration",
            description=(
                "If MySQL/Redis/MSSQL/PostgreSQL/Oracle turned up in the port scan, "
                "check for unauthenticated or default-credential access directly "
                "against the database service itself (not just via a web app's SQL "
                "injection — see OSCP-EXPLOIT-02 for that). `mysql` and `redis` are "
                "wrapped here (both default to a blank-credential/no-auth check); for "
                "PostgreSQL/MSSQL/Oracle the right client and flags depend entirely on "
                "which database turned up — `psql -h <target> -U postgres`, "
                "Impacket's `mssqlclient.py` — no wrapper for those yet."
            ),
            category="Enumeration",
            category_code="ENUM",
            tools=["mysql", "redis"],
        ),
        ChecklistItem(
            id="OSCP-ENUM-11",
            name="FTP Anonymous Login Check",
            description=(
                "If port 21 turned up in the port scan, check for anonymous FTP "
                "login directly — nmap's default -sC pass (OSCP-ENUM-02) covers this "
                "too via its ftp-anon script, but a real login-and-list confirms it "
                "unambiguously and surfaces what's actually sitting in the directory, "
                "which is often the finding itself (world-readable backups, "
                "credentials left in a file, a writable directory to drop a payload "
                "into)."
            ),
            category="Enumeration",
            category_code="ENUM",
            tools=["ftp"],
        ),
        # ================================================================
        # VULNERABILITY ANALYSIS
        # ================================================================
        ChecklistItem(
            id="OSCP-VULN-01",
            name="Automated Vulnerability Scan",
            description="Run template-based vulnerability scanning against every identified service/web port.",
            category="Vulnerability Analysis",
            category_code="VULN",
            tools=["nuclei"],
        ),
        ChecklistItem(
            id="OSCP-VULN-02",
            name="Exploit Lookup by Service/Version",
            description=(
                "For every specific product+version identified during enumeration, "
                "search the local exploit-db mirror for a known, working exploit — "
                "the direct payoff of doing enumeration thoroughly."
            ),
            category="Vulnerability Analysis",
            category_code="VULN",
            tools=["searchsploit"],
        ),
        ChecklistItem(
            id="OSCP-VULN-03",
            name="Web Application Vulnerability Scan",
            description="If a web app is in scope, a dedicated web vulnerability scan on top of the generic template scan above.",
            category="Vulnerability Analysis",
            category_code="VULN",
            tools=["nikto", "zap"],
        ),
        ChecklistItem(
            id="OSCP-VULN-04",
            name="Exploit Lookup via Metasploit",
            description=(
                "Search the Metasploit Framework's own module database for the "
                "product/version identified above — a different (and often more "
                "current) database than exploit-db, and one that goes straight from "
                "'found a module' to configuring and running it in the same session "
                "if OSCP-EXPLOIT-01 confirms it's the right one."
            ),
            category="Vulnerability Analysis",
            category_code="VULN",
            tools=["metasploit"],
        ),
        # ================================================================
        # EXPLOITATION
        # ================================================================
        ChecklistItem(
            id="OSCP-EXPLOIT-01",
            name="Attempt Identified Exploit",
            description=(
                "Weaponize and run the exploit found above (a public PoC adapted to "
                "this target, or a manual technique). Inherently manual and specific "
                "to what was actually found — no generic tool automates \"exploit the "
                "thing.\" Set up a listener (e.g. `nc -lvnp <port>`) before firing it."
            ),
            category="Exploitation",
            category_code="EXPLOIT",
            tools=[],
        ),
        ChecklistItem(
            id="OSCP-EXPLOIT-02",
            name="SQL Injection Testing",
            description="If a web app with data-driven pages is in scope, test for and exploit SQL injection.",
            category="Exploitation",
            category_code="EXPLOIT",
            tools=["sqlmap"],
        ),
        ChecklistItem(
            id="OSCP-EXPLOIT-03",
            name="Command Injection Testing",
            description="Test any web app input that might reach a shell command for OS command injection.",
            category="Exploitation",
            category_code="EXPLOIT",
            tools=["commix"],
        ),
        ChecklistItem(
            id="OSCP-EXPLOIT-04",
            name="Buffer Overflow Exploitation",
            description=(
                "The classic OSCP topic: a vulnerable Windows service crashes on a "
                "long/malformed input, controllable well enough to hijack execution. "
                "Needs a debugger (Immunity Debugger + mona.py, or x64dbg) attached to "
                "the *target* process — genuinely outside what this app (a recon/"
                "enumeration orchestrator against a target over the network) can ever "
                "automate. Real workflow: fuzz -> find the crash offset -> confirm "
                "EIP/RIP control -> find bad chars -> pick a JMP ESP/return gadget -> "
                "generate shellcode -> weaponize."
            ),
            category="Exploitation",
            category_code="EXPLOIT",
            tools=[],
        ),
        # ================================================================
        # PRIVILEGE ESCALATION — split Linux/Windows: same phase in OffSec's
        # own materials, but different techniques/tools in every practical
        # writeup, so kept as two checklists rather than one mixed one.
        # ================================================================
        ChecklistItem(
            id="OSCP-PRIVL-01",
            name="Linux Privilege Escalation Enumeration",
            description=(
                "Run on the compromised host itself (this app only reaches the target "
                "over the network, it doesn't get a shell on it) — LinPEAS or "
                "linux-smart-enumeration, plus by hand: `sudo -l`, SUID/SGID binaries "
                "(`find / -perm -4000 2>/dev/null`), writable cron jobs, kernel version, "
                "readable credential files."
            ),
            category="Privilege Escalation (Linux)",
            category_code="PRIVL",
            tools=[],
        ),
        ChecklistItem(
            id="OSCP-PRIVL-02",
            name="Linux Kernel/Service Exploit Research",
            description="Look up known local-privesc exploits for the exact kernel version and any locally-running services/cron scripts found above.",
            category="Privilege Escalation (Linux)",
            category_code="PRIVL",
            tools=["searchsploit"],
        ),
        ChecklistItem(
            id="OSCP-PRIVL-03",
            name="Linux Privesc — Metasploit Local Exploit Search",
            description="Same lookup as OSCP-PRIVL-02, against Metasploit's module database instead of exploit-db — check both, they don't always overlap.",
            category="Privilege Escalation (Linux)",
            category_code="PRIVL",
            tools=["metasploit"],
        ),
        ChecklistItem(
            id="OSCP-PRIVW-01",
            name="Windows Privilege Escalation Enumeration",
            description=(
                "Run on the compromised host itself — WinPEAS, plus by hand: "
                "`whoami /priv`, unquoted service paths, AlwaysInstallElevated, "
                "stored credentials (`reg query`, scheduled tasks, saved sessions), "
                "`systeminfo` for a missing-patch check."
            ),
            category="Privilege Escalation (Windows)",
            category_code="PRIVW",
            tools=[],
        ),
        ChecklistItem(
            id="OSCP-PRIVW-02",
            name="Windows Kernel/Service Exploit Research",
            description="Look up known local-privesc exploits for the exact Windows build and any third-party services found running above.",
            category="Privilege Escalation (Windows)",
            category_code="PRIVW",
            tools=["searchsploit"],
        ),
        ChecklistItem(
            id="OSCP-PRIVW-03",
            name="Windows Privesc — Metasploit Local Exploit Search",
            description="Same lookup as OSCP-PRIVW-02, against Metasploit's module database instead of exploit-db — check both, they don't always overlap.",
            category="Privilege Escalation (Windows)",
            category_code="PRIVW",
            tools=["metasploit"],
        ),
        # ================================================================
        # ACTIVE DIRECTORY — newer PEN-200 syllabus revisions weigh AD
        # attack chains heavily; kept as its own category rather than
        # folded into Enumeration/Privilege Escalation since AD techniques
        # (LDAP/Kerberos-specific) are genuinely distinct from either.
        # ================================================================
        ChecklistItem(
            id="OSCP-AD-01",
            name="Active Directory Enumeration",
            description=(
                "If the target is a domain controller (or joined to one), enumerate "
                "domain users/groups/computers/trusts and shares — enum4linux-ng "
                "covers the SMB/RPC side; for the LDAP side by hand: `ldapsearch -x -H "
                "ldap://<target> -b \"dc=...,dc=...\"`, `rpcclient -U '' -N <target>`, "
                "or BloodHound for the full attack-path graph (no wrapped tool for "
                "BloodHound's own collectors here — it needs valid domain creds and "
                "produces a graph this app doesn't render, not a simple stdout scan)."
            ),
            category="Active Directory",
            category_code="AD",
            tools=["enum4linux"],
        ),
        ChecklistItem(
            id="OSCP-AD-02",
            name="Kerberoasting / AS-REP Roasting",
            description=(
                "With any valid domain credentials (even a low-privilege user), request "
                "TGS tickets for accounts with an SPN set (Kerberoasting) or find "
                "accounts with pre-authentication disabled (AS-REP Roasting) — both "
                "yield an offline-crackable hash. Needs domain credentials and "
                "Kerberos-aware tooling (Impacket's GetUserSPNs.py/GetNPUsers.py) this "
                "app doesn't orchestrate; manual by design."
            ),
            category="Active Directory",
            category_code="AD",
            tools=[],
        ),
        # ================================================================
        # POST-EXPLOITATION
        # ================================================================
        ChecklistItem(
            id="OSCP-POST-01",
            name="Credential Harvesting & Loot Collection",
            description="Collect credentials, config files, and other loot from the compromised host — often the key to reaching further hosts.",
            category="Post-Exploitation",
            category_code="POST",
            tools=[],
        ),
        ChecklistItem(
            id="OSCP-POST-02",
            name="Lateral Movement / Pivoting",
            description="If other hosts are reachable only from the compromised box, pivot through it (e.g. chisel/ligolo/SSH tunneling) to reach them.",
            category="Post-Exploitation",
            category_code="POST",
            tools=[],
        ),
        # ================================================================
        # PROOF & REPORTING
        # ================================================================
        ChecklistItem(
            id="OSCP-PROOF-01",
            name="Capture Proof",
            description="Capture proof.txt/local.txt contents and a screenshot showing the compromised host's hostname/IP alongside the proof file — the actual evidence an OSCP-style report is graded on.",
            category="Proof & Reporting",
            category_code="PROOF",
            tools=[],
        ),
        ChecklistItem(
            id="OSCP-PROOF-02",
            name="Document Findings",
            description="Write up every step that led to compromise, in order, with commands and evidence — use this app's own Findings panel and report export for each checklist item as you go, not from memory at the end.",
            category="Proof & Reporting",
            category_code="PROOF",
            tools=[],
        ),
    ]


def _validate_tool_references() -> None:
    """Catch a checklist item pointing at a tool name that doesn't actually
    exist (e.g. "wappalyzer-cli" sat here unregistered/unrunnable for a
    while) as soon as this module loads, instead of only noticing when a
    tester's Run Tool dropdown for that item is quietly missing an entry.

    Also catches the per-tool-override version of the same mistake (used
    by NUCLEI_TAGS, CURL_ARGS, CURL_PATH_SUFFIX, WGET_PATH_SUFFIX): a
    typo'd item ID, or an override for an item whose `tools` doesn't even
    include the tool being overridden (so it could never actually apply).
    """
    from .tools import TOOL_REGISTRY  # local import: tools/ has no reason to import checklist.py, but avoid any load-order assumption

    known = set(TOOL_REGISTRY.keys())
    # Both checklists share the same tool registry and item-shape checks —
    # validate them together so an unregistered tool reference in the OSCP
    # checklist is caught at import time exactly like a WSTG one.
    items_by_id = {item.id: item for item in build_checklist() + build_oscp_checklist()}
    for item in items_by_id.values():
        unknown = [t for t in item.tools if t not in known]
        if unknown:
            raise AssertionError(
                f"{item.id} ({item.name}) lists unregistered tool(s) {unknown} — "
                f"check TOOL_REGISTRY in oculus/tools/__init__.py"
            )

    def _check_override(overrides: dict, required_tool: str, dict_name: str) -> None:
        for item_id in overrides:
            item = items_by_id.get(item_id)
            if item is None:
                raise AssertionError(f"{dict_name} references unknown checklist item {item_id!r}")
            if required_tool not in item.tools:
                raise AssertionError(
                    f"{dict_name} overrides {required_tool} for {item_id}, but its tools "
                    f"list {item.tools} doesn't include {required_tool!r} — the override "
                    f"can never apply"
                )

    _check_override(NUCLEI_TAGS, "nuclei", "NUCLEI_TAGS")
    _check_override(CURL_ARGS, "curl", "CURL_ARGS")
    _check_override(CURL_PATH_SUFFIX, "curl", "CURL_PATH_SUFFIX")
    _check_override(WGET_PATH_SUFFIX, "wget", "WGET_PATH_SUFFIX")


_validate_tool_references()
