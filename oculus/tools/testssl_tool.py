"""testssl tool wrapper — TLS/SSL configuration analysis."""
from __future__ import annotations

from .base import BaseTool


class TestsslTool(BaseTool):
    name   = "testssl"
    binary = "testssl.sh"
    description = "Analyze TLS/SSL configuration, protocols, ciphers, and known vulnerabilities."
    example = "testssl.sh --quiet --color 0 https://example.com"
    help_flag = "--help"
    install_hints = {
        "brew": "brew install testssl",
        "apt": "sudo apt install -y testssl.sh",
    }
    timeout_seconds = 300

    def build_command(self, fast: bool = False) -> list[str]:
        cmd = ["testssl.sh", "--quiet", "--color", "0"]
        if fast:
            cmd.append("--fast")
        cmd.append(f"https://{self.target}")
        return cmd

    def mock_output(self) -> str:
        return f"""\
###########################################################
    testssl.sh       3.2 from https://testssl.sh/

      Testing server defaults (Server Hello)

 TLS extensions (standard)    "renegotiation info/#65281" "EC point formats/#11"
                              "session ticket/#35" "max fragment length/#1"
                              "application layer protocol negotiation/#16"
 Session Ticket RFC 5077 hint 7200 seconds, session tickets keys seems to be rotated < daily
 SSL Session ID support       yes
 Session Resumption           Tickets: yes, ID: yes

      Testing protocols

 SSLv2      not offered (OK)
 SSLv3      not offered (OK)
 TLS 1      not offered
 TLS 1.1    not offered
 TLS 1.2    offered (OK)
 TLS 1.3    offered (OK): final
 NPN/SPDY   h2, http/1.1 (advertised)
 ALPN/HTTP2 h2, http/1.1 (offered)

      Testing cipher categories

 NULL ciphers (no encryption)                      not offered (OK)
 Anonymous NULL Ciphers (no authentication)        not offered (OK)
 Export ciphers (w/o ADH+NULL)                     not offered (OK)
 LOW: 64 Bit + DES, RC[2,4], MD5 (w/o export)     not offered (OK)
 Triple DES Ciphers / IDEA                         not offered
 Obsoleted CBC ciphers (AES, ARIA etc.)            offered
 Strong encryption (AEAD ciphers) with no FS       offered (OK)
 Forward Secrecy strong encryption (AEAD ciphers)  offered (OK)

      Testing server's certificate

 Common Name (CN)             {self.target}
 Subj. Alt. Name (SAN)        {self.target} *.{self.target}
 Trust (hostname)              Ok via SAN
 Chain of trust                Ok
 EV cert (experimental)        no
 Certificate Validity (UTC)    expires in 182 days (2025-01-01 00:00 --> 2026-01-01 00:00)
 ETS/"eSNI", keytic.          no
 Certificate Transparency      yes (certificate extension)
 OCSP URL                      http://r3.o.lencr.org
 OCSP stapling                 offered
 OCSP must staple extension    --
 DNS CAA RR (experimental)     available - "letsencrypt.org"
 Certificate Issued by         Let's Encrypt Authority R3

      Testing HTTP header response

 HTTP Status Code             200
 HTTP clock skew              0 sec from localtime
 Strict Transport Security    not offered  ⚠
 Public Key Pinning           --
 Server banner                nginx/1.18.0 (Ubuntu)
 Application banner           X-Powered-By: PHP/7.4.33
 Cookie(s)                    1 issued: PHPSESSID — NOT secure, NOT HttpOnly  ⚠
 Security headers             X-Frame-Options: SAMEORIGIN
                              X-Content-Type-Options: nosniff
                              -- No Content-Security-Policy
                              -- No Referrer-Policy
                              -- No Permissions-Policy

      Testing vulnerabilities

 Heartbleed (CVE-2014-0160)            not vulnerable (OK)
 CCS (CVE-2014-0224)                   not vulnerable (OK)
 Ticketbleed (CVE-2016-9244)           not vulnerable (OK)
 ROBOT                                 not vulnerable (OK)
 Secure Renegotiation (RFC 5746)       supported (OK)
 Secure Client-Initiated Renegotiation not vulnerable (OK)
 CRIME, TLS (CVE-2012-4929)            not vulnerable (OK)
 BREACH (CVE-2013-3587)                potentially NOT ok, "gzip" HTTP compression detected. See: https://breachattack.com/
 POODLE, SSL (CVE-2014-3566)           not vulnerable (OK), no SSLv3
 TLS_FALLBACK_SCSV (RFC 7507)          No fallback possible (OK), no protocol below TLS 1.2 offered
 SWEET32 (CVE-2016-2183, CVE-2016-6329) not vulnerable (OK)
 FREAK (CVE-2015-0204)                 not vulnerable (OK)
 DROWN (CVE-2016-0800, CVE-2016-0703) not vulnerable (OK)
 LOGJAM (CVE-2015-4000)               not vulnerable (OK)
 BEAST (CVE-2011-3389)                 not vulnerable (OK), no SSL3 or TLS1
 LUCKY13 (CVE-2013-0169)              potentially VULNERABLE, uses cipher block chaining (CBC) ciphers with TLS. Check patches
 Winshock (CVE-2014-6321)             not vulnerable (OK)
 RC4 (CVE-2013-2566, CVE-2015-2808)   not vulnerable (OK)

 Done 2026-07-07 15:03:12 [ 94s] -->> 93.184.216.34:443 ({self.target}) <<--
[SIMULATED — testssl.sh not found on this machine]"""
