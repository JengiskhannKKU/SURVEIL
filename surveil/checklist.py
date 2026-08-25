"""OWASP WSTG checklist definitions with tool mappings.

Covers:
  • WSTG-INFO-01 … WSTG-INFO-10  (Information Gathering)
  • WSTG-CONF-01 … WSTG-CONF-10  (Configuration & Deployment Management)
  • WSTG-IDNT-04                 (Identity Management)
  • WSTG-ATHN-02, WSTG-ATHN-03   (Authentication)
  • WSTG-INPV-01, 05, 12         (Input Validation)
"""
from __future__ import annotations

from .models import ChecklistItem

# Maps a checklist item ID to a wordlist category (see
# surveil/wordlists.py's recommend_wordlist() and CATEGORY_LABELS below)
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
    "WSTG-IDNT-04": "usernames",   # Test for Account Enumeration
}

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
    """Return a fresh, ordered list of OWASP WSTG checklist items."""
    return [
        # ================================================================
        # INFORMATION GATHERING
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
            tools=["nmap", "httpx", "whatweb"],
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
            tools=["httpx", "ffuf"],
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
                "comments, or staging/debug endpoints."
            ),
            category="Information Gathering",
            category_code="INFO",
            tools=["katana", "httpx"],
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
                "Screenshot every distinct page state."
            ),
            category="Information Gathering",
            category_code="INFO",
            tools=["katana", "gowitness"],
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
                "Cross-reference with nuclei fingerprint templates."
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
        # CONFIGURATION & DEPLOYMENT MANAGEMENT
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
            tools=["nmap"],
            owasp_ref="WSTG-CONF-01",
            cwe_ids=["CWE-16"],
        ),
        ChecklistItem(
            id="WSTG-CONF-02",
            name="Test Application Platform Configuration",
            description=(
                "Check for verbose error messages, directory listings, debug mode enabled, "
                "and exposed configuration endpoints (/actuator, /.env, /config.php). "
                "Verbose errors leak stack traces and internal paths."
            ),
            category="Configuration Management",
            category_code="CONF",
            tools=["nikto", "nuclei", "httpx"],
            owasp_ref="WSTG-CONF-02",
            cwe_ids=["CWE-16", "CWE-209"],
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
            name="Enumerate Admin Interfaces",
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
            tools=["nmap", "httpx", "nuclei"],
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
            tools=["testssl", "httpx", "nuclei"],
            owasp_ref="WSTG-CONF-07",
            cwe_ids=["CWE-319", "CWE-326"],
        ),
        ChecklistItem(
            id="WSTG-CONF-08",
            name="Test Security Response Headers",
            description=(
                "Audit all security-relevant response headers: Content-Security-Policy, "
                "X-Frame-Options, X-Content-Type-Options, Referrer-Policy, "
                "Permissions-Policy. Missing or misconfigured headers enable clickjacking, "
                "MIME sniffing, and XSS."
            ),
            category="Configuration Management",
            category_code="CONF",
            tools=["httpx", "nuclei"],
            owasp_ref="WSTG-CONF-08",
            cwe_ids=["CWE-693", "CWE-116"],
        ),
        ChecklistItem(
            id="WSTG-CONF-09",
            name="Test for Subdomain Takeover",
            description=(
                "Enumerate all subdomains and check for dangling DNS records pointing to "
                "deprovisioned cloud resources (AWS S3, Azure, GitHub Pages, Heroku). "
                "A takeover allows hosting malicious content under the target domain."
            ),
            category="Configuration Management",
            category_code="CONF",
            tools=["subfinder", "dnsx", "nuclei"],
            owasp_ref="WSTG-CONF-09",
            cwe_ids=["CWE-350"],
        ),
        ChecklistItem(
            id="WSTG-CONF-10",
            name="Test WAF Detection",
            description=(
                "Detect the presence and vendor of any Web Application Firewall. "
                "Document WAF type (Cloudflare, Akamai, AWS WAF) as this affects the "
                "reliability of subsequent active scanning."
            ),
            category="Configuration Management",
            category_code="CONF",
            tools=["wafw00f", "nuclei"],
            owasp_ref="WSTG-CONF-10",
            cwe_ids=["CWE-693"],
        ),
        # ================================================================
        # IDENTITY MANAGEMENT
        # ================================================================
        ChecklistItem(
            id="WSTG-IDNT-04",
            name="Test for Account Enumeration",
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
        # ================================================================
        # AUTHENTICATION
        # ================================================================
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
        # ================================================================
        # INPUT VALIDATION
        # ================================================================
        ChecklistItem(
            id="WSTG-INPV-01",
            name="Test for Reflected Cross-Site Scripting",
            description=(
                "Inject script payloads into every input (query params, form "
                "fields, headers) and check whether the target reflects them back "
                "unencoded into the response HTML — the classic XSS entry point."
            ),
            category="Input Validation",
            category_code="INPV",
            tools=["nuclei"],
            owasp_ref="WSTG-INPV-01",
            cwe_ids=["CWE-79"],
        ),
        ChecklistItem(
            id="WSTG-INPV-05",
            name="Test SQL Injection",
            description=(
                "Test every input that reaches a database query for SQL injection: "
                "boolean-based, error-based, UNION-based, and time-based blind. "
                "One of the highest-impact, most consequential web vulnerabilities."
            ),
            category="Input Validation",
            category_code="INPV",
            tools=["sqlmap", "nuclei"],
            owasp_ref="WSTG-INPV-05",
            cwe_ids=["CWE-89"],
        ),
        ChecklistItem(
            id="WSTG-INPV-12",
            name="Test Command Injection",
            description=(
                "Test inputs that might reach a shell/OS command (file names, "
                "hostnames passed to ping/nslookup-style utilities, export/convert "
                "features) for OS command injection using shell metacharacters."
            ),
            category="Input Validation",
            category_code="INPV",
            tools=["nuclei"],
            owasp_ref="WSTG-INPV-12",
            cwe_ids=["CWE-78"],
        ),
    ]


def _validate_tool_references() -> None:
    """Catch a checklist item pointing at a tool name that doesn't actually
    exist (e.g. "wappalyzer-cli" sat here unregistered/unrunnable for a
    while) as soon as this module loads, instead of only noticing when a
    tester's Run Tool dropdown for that item is quietly missing an entry.
    """
    from .tools import TOOL_REGISTRY  # local import: tools/ has no reason to import checklist.py, but avoid any load-order assumption

    known = set(TOOL_REGISTRY.keys())
    for item in build_checklist():
        unknown = [t for t in item.tools if t not in known]
        if unknown:
            raise AssertionError(
                f"{item.id} ({item.name}) lists unregistered tool(s) {unknown} — "
                f"check TOOL_REGISTRY in surveil/tools/__init__.py"
            )


_validate_tool_references()
