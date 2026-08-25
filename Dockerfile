# syntax=docker/dockerfile:1

# ---- Stage 1: build Go-based enumeration tools ----
FROM golang:1.26-bookworm AS gotools

ENV GOPATH=/root/go
RUN go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest \
    && go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest \
    && go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest \
    && go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest \
    && go install -v github.com/projectdiscovery/katana/cmd/katana@latest \
    && go install -v github.com/sensepost/gowitness@latest \
    && go install -v github.com/owasp-amass/amass/v4/...@master \
    && go install -v github.com/ffuf/ffuf/v2@latest \
    && go install -v github.com/OJ/gobuster/v3@latest

# ---- Stage 2: runtime image ----
FROM python:3.11-slim-bookworm

LABEL org.opencontainers.image.title="surveil" \
      org.opencontainers.image.description="Deterministic, OWASP WSTG checklist-driven web application penetration testing tool"

# System enumeration tools available directly from Debian repos, plus
# runtime/build deps for the Ruby (wpscan), Perl (nikto), and shell
# (testssl.sh) tools:
#   - libjson-perl / libxml-writer-perl: nikto's report/plugin modules
#   - bsdextrautils / procps: `hexdump` and `ps`, both used by testssl.sh
#   - libcurl4: required at runtime by the `ffi`/`typhoeus` gems wpscan depends on
#   - sqlmap / hydra: both packaged directly for Debian, no build step needed
RUN apt-get update && apt-get install -y --no-install-recommends \
        nmap \
        whatweb \
        wafw00f \
        sqlmap \
        hydra \
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
    && rm -rf /var/lib/apt/lists/*

# nikto — not packaged for Debian bookworm; install from source.
RUN git clone --depth 1 https://github.com/sullo/nikto.git /opt/nikto \
    && ln -s /opt/nikto/program/nikto.pl /usr/local/bin/nikto \
    && chmod +x /opt/nikto/program/nikto.pl

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

# wpscan (Ruby gem) and arjun (Python tool, installed in an isolated venv via pipx).
RUN gem install wpscan --no-document \
    && pipx install arjun \
    && ln -s /root/.local/bin/arjun /usr/local/bin/arjun

# testssl.sh — plain shell script, no build step required.
RUN git clone --depth 1 https://github.com/testssl/testssl.sh.git /opt/testssl.sh \
    && ln -s /opt/testssl.sh/testssl.sh /usr/local/bin/testssl.sh

WORKDIR /app
COPY pyproject.toml README.md ./
COPY surveil ./surveil
# backend/ isn't a pip-installed package (see pyproject.toml's
# packages.find, which only includes "surveil*") — it's imported as
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

# Engagement state is persisted under $HOME/.surveil — mount a
# volume here to keep engagements/reports across container restarts.
ENV HOME=/data
RUN mkdir -p /data && chmod 777 /data
VOLUME ["/data"]
WORKDIR /data

ENTRYPOINT ["surveil"]
CMD ["--help"]
