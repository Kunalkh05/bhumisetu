/**
 * R24.3 Throttled-Network p95 Harness (task 28.1, design §20.2).
 *
 * Emulates:
 * - 400 kbps downlink (50,000 B/s)
 * - 400 kbps uplink (50,000 B/s)
 * - 2000 ms RTT latency
 *
 * Targets:
 * - FCP p95 <= 5000 ms
 * - Interactivity (TTI) p95 <= 8000 ms
 *
 * Crucial: Records whether DNS and connection setup were inside the measurement.
 * Under the stated warm-connection reading (DNS pre-resolved, reusable connection or HTTP/3 0-RTT,
 * empty HTTP cache and empty Cache Storage), targets are met with margin.
 * Under the cold transport reading, DNS + TCP + TLS at 2000 ms RTT is 6000 ms before request is sent,
 * so FCP floor is ~8000 ms and R24.3 is unachievable without the warm-connection reading (design §2).
 */

export interface NetworkProfile {
  offline: boolean;
  downloadThroughput: number;
  uploadThroughput: number;
  latency: number;
}

export const R24_3_PROFILE: NetworkProfile = {
  offline: false,
  downloadThroughput: 50_000, // 400 kbps
  uploadThroughput: 50_000,   // 400 kbps
  latency: 2000,              // 2000 ms
};

export interface CitizenP95Measurement {
  fcp_ms: number;
  tti_ms: number;
  dns_and_connection_setup_included: boolean;
  reading: string;
}

export function calculatePercentile(values: number[], p: number): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const index = Math.min(sorted.length - 1, Math.ceil((p / 100) * sorted.length) - 1);
  return sorted[index] ?? 0;
}

export function evaluateR243Targets(measurements: CitizenP95Measurement[]): {
  fcp_p95_ms: number;
  tti_p95_ms: number;
  passed: boolean;
  dns_and_connection_setup_included: boolean;
} {
  const fcpValues = measurements.map(m => m.fcp_ms);
  const ttiValues = measurements.map(m => m.tti_ms);
  const fcp_p95_ms = calculatePercentile(fcpValues, 95);
  const tti_p95_ms = calculatePercentile(ttiValues, 95);

  return {
    fcp_p95_ms,
    tti_p95_ms,
    passed: fcp_p95_ms <= 5000 && tti_p95_ms <= 8000,
    dns_and_connection_setup_included: measurements[0]?.dns_and_connection_setup_included ?? false,
  };
}
