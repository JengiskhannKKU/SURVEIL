const IPV4_RE = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/;

export function isIpAddress(target: string): boolean {
  const raw = target.trim();
  const parts = raw.split(":");
  // Strip a single trailing :port — but don't mangle IPv6, which has
  // several colons of its own.
  const host = parts.length === 2 ? parts[0] : raw;
  const m = host.match(IPV4_RE);
  if (m) return m.slice(1).every((octet) => Number(octet) <= 255);
  // Basic IPv6 heuristic — good enough for a UI hint, not a validator.
  return host.includes(":") && /^[0-9a-fA-F:]+$/.test(host);
}
