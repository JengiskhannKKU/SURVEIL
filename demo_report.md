# Pentest Report — VulnWeb Demo Engagement

| Field                  | Value                 |
| ---------------------- | --------------------- |
| **Target**             | `testphp.vulnweb.com` |
| **Engagement ID**      | `1b058611`            |
| **Report Date**        | 2026-07-07 15:40      |
| **Engagement Created** | 2026-07-07 15:40      |
| **Progress**           | 0/20 checklist items  |

---

## Executive Summary

This report presents findings from a deterministic, OWASP WSTG checklist-driven web application security assessment of **testphp.vulnweb.com**. All enumeration was performed using standard open-source tools invoked directly; no AI-driven decision-making was used in the enumeration phase.

### Finding Severity Summary

| Severity    | Count |
| ----------- | ----- |
| 🔴 Critical | 2     |
| 🟠 High     | 0     |
| 🟡 Medium   | 2     |
| 🔵 Low      | 0     |
| ⚪ Info     | 0     |
| **Total**   | **4** |

---

## Checklist Coverage

| ID             | Name                                           | Status    | Findings |
| -------------- | ---------------------------------------------- | --------- | -------- |
| `WSTG-INFO-01` | Search Engine Discovery & Recon                | ○ pending | 0        |
| `WSTG-INFO-02` | Fingerprint Web Server                         | ○ pending | 1        |
| `WSTG-INFO-03` | Review Webserver Metafiles                     | ○ pending | 0        |
| `WSTG-INFO-04` | Enumerate Applications on Web Server           | ○ pending | 0        |
| `WSTG-INFO-05` | Review Webpage Content for Information Leakage | ○ pending | 0        |
| `WSTG-INFO-06` | Identify Application Entry Points              | ○ pending | 0        |
| `WSTG-INFO-07` | Map Execution Paths Through Application        | ○ pending | 0        |
| `WSTG-INFO-08` | Fingerprint Web Application Framework          | ○ pending | 0        |
| `WSTG-INFO-09` | Fingerprint Web Application                    | ○ pending | 0        |
| `WSTG-INFO-10` | Map Application Architecture                   | ○ pending | 0        |
| `WSTG-CONF-01` | Test Network Infrastructure Configuration      | ○ pending | 0        |
| `WSTG-CONF-02` | Test Application Platform Configuration        | ○ pending | 0        |
| `WSTG-CONF-03` | Test File Extension Handling                   | ○ pending | 0        |
| `WSTG-CONF-04` | Review Old Backup and Unreferenced Files       | ○ pending | 0        |
| `WSTG-CONF-05` | Enumerate Admin Interfaces                     | ○ pending | 1        |
| `WSTG-CONF-06` | Test HTTP Methods                              | ○ pending | 0        |
| `WSTG-CONF-07` | Test HTTP Strict Transport Security            | ○ pending | 1        |
| `WSTG-CONF-08` | Test Security Response Headers                 | ○ pending | 1        |
| `WSTG-CONF-09` | Test for Subdomain Takeover                    | ○ pending | 0        |
| `WSTG-CONF-10` | Test WAF Detection                             | ○ pending | 0        |

---

## Detailed Findings

### 🔴 [CRITICAL] nginx 1.18.0 — Outdated with known CVEs

| Field              | Value                                                    |
| ------------------ | -------------------------------------------------------- |
| **Finding ID**     | `9e7c74ae`                                               |
| **Checklist Item** | `WSTG-INFO-02`                                           |
| **Severity**       | CRITICAL                                                 |
| **CVSS Score**     | `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H` → **9.8** |
| **OWASP Category** | —                                                        |
| **CWE**            | CWE-200                                                  |
| **Tool**           | `manual`                                                 |
| **Status**         | ⚠️ Unverified (tool)                                     |
| **Discovered**     | 2026-07-07 15:40                                         |

**Description**

nginx 1.18.0 discloses version in Server header and has CVE-2021-23017 (CVSS 7.7 resolver buffer overflow).

**Remediation**

Upgrade nginx to 1.24.0+ and suppress version via 'server_tokens off;'

---

### 🔴 [CRITICAL] Apache Tomcat Manager Exposed on :8080

| Field              | Value                                                    |
| ------------------ | -------------------------------------------------------- |
| **Finding ID**     | `ebe2b833`                                               |
| **Checklist Item** | `WSTG-CONF-05`                                           |
| **Severity**       | CRITICAL                                                 |
| **CVSS Score**     | `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H` → **9.8** |
| **OWASP Category** | —                                                        |
| **CWE**            | CWE-284                                                  |
| **Tool**           | `manual`                                                 |
| **Status**         | ⚠️ Unverified (tool)                                     |
| **Discovered**     | 2026-07-07 15:40                                         |

**Description**

Tomcat Manager at :8080/manager/html is accessible without IP restriction. Default credentials may be in use.

**Remediation**

Restrict Tomcat Manager access by IP in conf/tomcat-users.xml and bind to localhost only.

---

### 🟡 [MEDIUM] Missing Strict-Transport-Security header

| Field              | Value                                                    |
| ------------------ | -------------------------------------------------------- |
| **Finding ID**     | `52f5d197`                                               |
| **Checklist Item** | `WSTG-CONF-07`                                           |
| **Severity**       | MEDIUM                                                   |
| **CVSS Score**     | `CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:L/A:N` → **4.2** |
| **OWASP Category** | —                                                        |
| **CWE**            | CWE-319                                                  |
| **Tool**           | `manual`                                                 |
| **Status**         | ⚠️ Unverified (tool)                                     |
| **Discovered**     | 2026-07-07 15:40                                         |

**Description**

HSTS is not configured. Browsers may connect over HTTP before being redirected.

**Remediation**

Add: Strict-Transport-Security: max-age=31536000; includeSubDomains; preload

---

### 🟡 [MEDIUM] Missing Content-Security-Policy header

| Field              | Value                                                    |
| ------------------ | -------------------------------------------------------- |
| **Finding ID**     | `7eb38199`                                               |
| **Checklist Item** | `WSTG-CONF-08`                                           |
| **Severity**       | MEDIUM                                                   |
| **CVSS Score**     | `CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N` → **6.1** |
| **OWASP Category** | —                                                        |
| **CWE**            | CWE-693                                                  |
| **Tool**           | `manual`                                                 |
| **Status**         | ⚠️ Unverified (tool)                                     |
| **Discovered**     | 2026-07-07 15:40                                         |

**Description**

The application does not set a Content-Security-Policy header, leaving it vulnerable to XSS and data injection attacks.

**Remediation**

Implement a strict CSP: Content-Security-Policy: default-src 'self'; script-src 'self'

---

## Appendix — Raw Tool Output
