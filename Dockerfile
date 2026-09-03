# syntax=docker/dockerfile:1

# ---- Stage 1: build Go-based enumeration tools ----
FROM golang:1.26-bookworm AS gotools

# libpcap-dev: naabu's SYN-scan mode links against libpcap at build time
# (CGO) — without it the build either fails or silently falls back to a
# slower plain-connect scan.
RUN apt-get update && apt-get install -y --no-install-recommends libpcap-dev \
    && rm -rf /var/lib/apt/lists/*

ENV GOPATH=/root/go
RUN go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest \
    && go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest \
    && go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest \
    && go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest \
    && go install -v github.com/projectdiscovery/katana/cmd/katana@latest \
    && go install -v github.com/sensepost/gowitness@latest \
    && go install -v github.com/owasp-amass/amass/v4/...@master \
    && go install -v github.com/ffuf/ffuf/v2@latest \
    && go install -v github.com/OJ/gobuster/v3@latest \
    && go install -v github.com/projectdiscovery/naabu/v2/cmd/naabu@latest \
    && go install -v github.com/hahwul/dalfox/v2@latest

# ---- Stage 2: runtime image ----
FROM python:3.11-slim-bookworm

LABEL org.opencontainers.image.title="oculus" \
      org.opencontainers.image.description="Deterministic, OWASP WSTG checklist-driven web application penetration testing tool"

# System enumeration tools available directly from Debian repos, plus
# runtime/build deps for the Ruby (wpscan), Perl (nikto), and shell
# (testssl.sh) tools:
#   - libjson-perl / libxml-writer-perl: nikto's report/plugin modules
#   - bsdextrautils / procps: `hexdump` and `ps`, both used by testssl.sh
#   - libcurl4: required at runtime by the `ffi`/`typhoeus` gems wpscan depends on
#   - sqlmap / hydra: both packaged directly for Debian, no build step needed
#   - docker.io: the `docker` CLI the `zap` tool wrapper shells out to
#     (oculus/tools/zap_tool.py runs `docker run zaproxy/zap-stable ...`)
#     — this is the *client* only, talking to the host's own Docker daemon
#     over the socket docker-compose.yml mounts in at
#     /var/run/docker.sock; no dockerd runs inside this container itself.
#   - chromium: gowitness v3's default `chromedp` driver execs a real
#     Chrome-compatible binary directly (confirmed via a real run: `exec:
#     "google-chrome": executable file not found in $PATH`) rather than
#     reliably auto-downloading one itself despite what its own --chrome-
#     path help text implies — Debian's `chromium` package provides that
#     binary; oculus/tools/gowitness_tool.py locates it and passes
#     --chrome-path explicitly so gowitness doesn't have to guess.
#   - smbclient / samba-common-bin: not themselves wrapped tools, but
#     enum4linux-ng shells out to nmblookup/net/rpcclient/smbclient at
#     runtime and refuses to run at all without them (confirmed via a
#     real run: "[!] The following dependend tools are missing:
#     nmblookup, net, rpcclient, smbclient") — smbclient the Debian
#     package only provides rpcclient/smbclient; net/nmblookup are a
#     *separate* package, samba-common-bin (confirmed via `dpkg -L
#     smbclient` genuinely not listing them, not assumed).
#   - tshark: oculus/tools/tshark_tool.py's offline pcap-credential-
#     extraction tool. The wireshark-common package's postinst normally
#     asks an interactive debconf question (whether non-root users can
#     capture live traffic) that hangs a non-interactive `docker build`
#     forever — preseeded to "false" below (this tool only ever reads an
#     already-captured file with `-r`, never a live interface, so that
#     capability isn't needed anyway) and DEBIAN_FRONTEND=noninteractive
#     set for just this install so the preseed actually takes effect
#     instead of still prompting.
RUN echo "wireshark-common wireshark-common/install-setuid boolean false" | debconf-set-selections
RUN DEBIAN_FRONTEND=noninteractive apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        nmap \
        whatweb \
        wafw00f \
        sqlmap \
        hydra \
        curl \
        wget \
        perl \
        libjson-perl \
        libxml-writer-perl \
        bsdextrautils \
        procps \
        ruby-full \
        libcurl4 \
        build-essential \
        git \
        python3-pip \
        pipx \
        ca-certificates \
        docker.io \
        chromium \
        smbclient \
        samba-common-bin \
        default-mysql-client \
        redis-tools \
        tshark \
    && rm -rf /var/lib/apt/lists/*

# nikto — not packaged for Debian bookworm; install from source.
RUN git clone --depth 1 https://github.com/sullo/nikto.git /opt/nikto \
    && ln -s /opt/nikto/program/nikto.pl /usr/local/bin/nikto \
    && chmod +x /opt/nikto/program/nikto.pl

# exploitdb (provides `searchsploit`, the OSCP checklist's exploit-lookup-
# by-service/version step) — confirmed NOT packaged for Debian bookworm
# (`apt install exploitdb` really does fail with "Unable to locate
# package" on this exact base image, tried before falling back to this);
# install from the official repo instead, same pattern as nikto/testssl
# above. `searchsploit` is a self-contained script that locates its own
# sibling exploits/ database directory via its own path, so a plain
# symlink into PATH is enough — no separate config step needed.
RUN git clone --depth 1 https://gitlab.com/exploit-database/exploitdb.git /opt/exploitdb \
    && ln -s /opt/exploitdb/searchsploit /usr/local/bin/searchsploit

# Go-based tools built in the previous stage.
COPY --from=gotools /root/go/bin/subfinder /usr/local/bin/subfinder
COPY --from=gotools /root/go/bin/httpx /usr/local/bin/httpx
COPY --from=gotools /root/go/bin/nuclei /usr/local/bin/nuclei
COPY --from=gotools /root/go/bin/dnsx /usr/local/bin/dnsx
COPY --from=gotools /root/go/bin/katana /usr/local/bin/katana
COPY --from=gotools /root/go/bin/gowitness /usr/local/bin/gowitness
COPY --from=gotools /root/go/bin/amass /usr/local/bin/amass
COPY --from=gotools /root/go/bin/ffuf /usr/local/bin/ffuf
COPY --from=gotools /root/go/bin/gobuster /usr/local/bin/gobuster
COPY --from=gotools /root/go/bin/naabu /usr/local/bin/naabu
COPY --from=gotools /root/go/bin/dalfox /usr/local/bin/dalfox

# wpscan (Ruby gem) and arjun (Python tool, installed in an isolated venv via pipx).
RUN gem install wpscan --no-document \
    && pipx install arjun \
    && ln -s /root/.local/bin/arjun /usr/local/bin/arjun

# enum4linux-ng — confirmed NOT on PyPI (`pipx install enum4linux-ng`
# really does fail with "No matching distribution found", tried before
# falling back to this, same lesson as entry 48's exploitdb apt attempt);
# install from its real source instead, same pattern as nikto/testssl
# above, plus its own requirements.txt (impacket/ldap3/pyyaml) via plain
# pip into the system interpreter (this image already does that for
# oculus itself further down, so it's a proven-working install path here).
RUN git clone --depth 1 https://github.com/cddmp/enum4linux-ng.git /opt/enum4linux-ng \
    && pip install --no-cache-dir -r /opt/enum4linux-ng/requirements.txt \
    && chmod +x /opt/enum4linux-ng/enum4linux-ng.py \
    && ln -s /opt/enum4linux-ng/enum4linux-ng.py /usr/local/bin/enum4linux-ng

# testssl.sh — plain shell script, no build step required.
RUN git clone --depth 1 https://github.com/testssl/testssl.sh.git /opt/testssl.sh \
    && ln -s /opt/testssl.sh/testssl.sh /usr/local/bin/testssl.sh

# commix — not packaged for Debian; install from source, same pattern as nikto.
RUN git clone --depth 1 https://github.com/commixproject/commix.git /opt/commix \
    && printf '#!/bin/sh\nexec python3 /opt/commix/commix.py "$@"\n' > /usr/local/bin/commix \
    && chmod +x /usr/local/bin/commix

# linpeas.sh / winPEASx64.exe — the standard OSCP privilege-escalation
# enumeration scripts (see oculus/tools/linpeas_tool.py, which serves
# this directory over HTTP for a tester to pull onto their own foothold
# shell — not something run inside this container against the network
# target at all). Static script/binary releases, no package to install;
# grabbed straight from the upstream project's "latest" GitHub release,
# same pattern as searchsploit/nikto above.
RUN mkdir -p /opt/peas \
    && curl -fsSL -o /opt/peas/linpeas.sh https://github.com/carlospolop/PEASS-ng/releases/latest/download/linpeas.sh \
    && curl -fsSL -o /opt/peas/winPEASx64.exe https://github.com/carlospolop/PEASS-ng/releases/latest/download/winPEASx64.exe \
    && chmod +x /opt/peas/linpeas.sh

WORKDIR /app
COPY pyproject.toml README.md ./
COPY oculus ./oculus
# backend/ isn't a pip-installed package (see pyproject.toml's
# packages.find, which only includes "oculus*") — it's imported as
# "backend.main:app" straight off disk by the `backend` docker-compose
# service, so PYTHONPATH=/app below is what makes that resolve.
COPY backend ./backend

# `.[web]` pulls in fastapi/uvicorn/websockets too, so the same image
# serves both the CLI/TUI (default entrypoint below) and the `backend`
# compose service (which overrides entrypoint/command to run uvicorn)
# without needing a second, mostly-duplicate image.
RUN pip install --no-cache-dir ".[web]"

# Fetch nuclei templates at build time so scans work fully offline afterwards.
RUN nuclei -update-templates || true

ENV PYTHONPATH=/app

# Engagement state is persisted under $HOME/.oculus — mount a
# volume here to keep engagements/reports across container restarts.
ENV HOME=/data
RUN mkdir -p /data && chmod 777 /data
VOLUME ["/data"]
WORKDIR /data

ENTRYPOINT ["oculus"]
CMD ["--help"]
