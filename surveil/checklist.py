"""OWASP WSTG checklist definitions with tool mappings.

Covers:
  • WSTG-INFO-01 … WSTG-INFO-10  (Information Gathering)
  • WSTG-CONF-01 … WSTG-CONF-10  (Configuration & Deployment Management)
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
                "Use search engines (Google, Bing, Shodan) to surface publicly indexed "
                "information about the target: cached pages, exposed documents, "
                "credentials in pastes, and misconfigured cloud storage."
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
            tools=["whatweb", "wappalyzer-cli", "wpscan"],
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
            owasp_ref="WSTG-CONF-07",
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
            owasp_ref="WSTG-CONF-10",
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
            owasp_ref="WSTG-CONF-01",
            cwe_ids=["CWE-693"],
        ),
    ]
