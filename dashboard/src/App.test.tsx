import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import App from "./App";

vi.mock("./api/client", () => ({
  getHealth: vi.fn().mockResolvedValue({ status: "ok", hardening_enabled: false }),
  getHealthSummary: vi.fn().mockResolvedValue({
    health_score: 85,
    total_logs: 10,
    error_count: 2,
    error_rate: 0.2,
    open_alerts: 1,
    open_critical_alerts: 0,
    last_analyzed_at: null,
  }),
  getTrends: vi.fn().mockResolvedValue({ points: [] }),
  getAlerts: vi.fn().mockResolvedValue([]),
  getWebhookDeliveries: vi.fn().mockResolvedValue([]),
}));

describe("App", () => {
  it("renders dashboard title and primary actions", async () => {
    render(<App />);
    expect(await screen.findByRole("heading", { name: /Observability Watchdog/i })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Run Analysis/i })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Upload Log File/i })).toBeTruthy();
  });
});
