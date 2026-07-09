# syntax=docker/dockerfile:1

# ---- Stage 1: build Go-based enumeration tools (subfinder, httpx, nuclei) ----
FROM golang:1.25-bookworm AS gotools

ENV GOPATH=/root/go
RUN go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest \
    && go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest \
    && go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest

# ---- Stage 2: runtime image ----
FROM python:3.11-slim-bookworm

LABEL org.opencontainers.image.title="PCT — Pentest Checklist Tool" \
      org.opencontainers.image.description="Deterministic, OWASP WSTG checklist-driven web application penetration testing tool"

# System enumeration tools available directly from Debian repos.
RUN apt-get update && apt-get install -y --no-install-recommends \
        nmap \
        whatweb \
        wafw00f \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Go-based tools built in the previous stage.
COPY --from=gotools /root/go/bin/subfinder /usr/local/bin/subfinder
COPY --from=gotools /root/go/bin/httpx /usr/local/bin/httpx
COPY --from=gotools /root/go/bin/nuclei /usr/local/bin/nuclei

WORKDIR /app
COPY pyproject.toml README.md ./
COPY pentest_checklist ./pentest_checklist

RUN pip install --no-cache-dir .

# Fetch nuclei templates at build time so scans work fully offline afterwards.
RUN nuclei -update-templates || true

# Engagement state is persisted under $HOME/.pentest_checklist — mount a
# volume here to keep engagements/reports across container restarts.
ENV HOME=/data
RUN mkdir -p /data && chmod 777 /data
VOLUME ["/data"]
WORKDIR /data

ENTRYPOINT ["pct"]
CMD ["--help"]
