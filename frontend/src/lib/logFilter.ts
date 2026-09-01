// Lines that are pure progress/status noise from a live-streaming tool —
// ffuf's repeating "::  Progress: [1038084/1185254] :: Job [1/1] :: 3472
// req/sec :: Duration: [0:04:58] :: Errors: 0 ::" ticker being the
// motivating case, which can print thousands of lines over a long run and
// bury any real finding underneath them — rather than an actual result
// worth a tester's attention. Shared with pathTree.ts's own path-parsing
// ignore-list, since the same lines that are noise for "did this line
// report a path" are noise for "is this worth showing while watching a
// run live" too.
export const NOISE_LINE_RE = /^(::|_{3,}|v\d|\[SIMULATED|Duration:|Progress:)/;

export function isNoiseLine(line: string): boolean {
  return NOISE_LINE_RE.test(line.trim());
}

export function filterNoiseLines(lines: string[]): string[] {
  return lines.filter((l) => !isNoiseLine(l));
}
