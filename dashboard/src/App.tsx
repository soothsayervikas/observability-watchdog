import { useCallback, useEffect, useRef, useState } from "react";
import {
  Alert,
  AnalyzeResult,
  getAlerts,
  getHealth,
  getHealthSummary,
  getTrends,
  getWebhookDeliveries,
  HealthSummary,
  runAnalysis,
  scanLogSources,
  seedSampleData,
  TrendPoint,
  updateAlertStatus,
  uploadLogFile,
  WebhookDelivery,
} from "./api/client";
import { AlertTable } from "./components/AlertTable";
import { HealthOverview } from "./components/HealthOverview";
import { TrendChart } from "./components/TrendChart";
import { WebhookPanel } from "./components/WebhookPanel";

export default function App() {
  const [summary, setSummary] = useState<HealthSummary | null>(null);
  const [trends, setTrends] = useState<TrendPoint[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [deliveries, setDeliveries] = useState<WebhookDelivery[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [demoEnabled, setDemoEnabled] = useState(true);
  const [trendHours, setTrendHours] = useState(24);
  const [updatingAlertId, setUpdatingAlertId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const summaryRef = useRef<HealthSummary | null>(null);
  summaryRef.current = summary;

  const refresh = useCallback(
    async (options?: { silent?: boolean }): Promise<HealthSummary | null> => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      const signal = controller.signal;

      if (!options?.silent) {
        setLoading(true);
      }
      if (!options?.silent) {
        setError(null);
      }
      try {
        const [health, healthSummary, trendData, alertData, deliveryData] = await Promise.all([
          getHealth(signal),
          getHealthSummary(signal),
          getTrends(undefined, trendHours, signal),
          getAlerts({ limit: 100 }, signal),
          getWebhookDeliveries(signal),
        ]);
        if (signal.aborted) {
          return null;
        }
        setDemoEnabled(!(health.hardening_enabled ?? false));
        setSummary(healthSummary);
        setTrends(trendData.points);
        setAlerts(alertData);
        setDeliveries(deliveryData);
        setError(null);
        return healthSummary;
      } catch (err) {
        if (signal.aborted) {
          return null;
        }
        const message = err instanceof Error ? err.message : "Failed to load dashboard";
        if (options?.silent && summaryRef.current) {
          return null;
        }
        setError(message);
        return null;
      } finally {
        if (!options?.silent && !signal.aborted) {
          setLoading(false);
        }
      }
    },
    [trendHours],
  );

  useEffect(() => {
    void refresh();
    const interval = setInterval(() => void refresh({ silent: true }), 15000);
    return () => {
      clearInterval(interval);
      abortRef.current?.abort();
    };
  }, [refresh]);

  const handleAnalyze = async () => {
    setAnalyzing(true);
    setError(null);
    setNotice(null);
    try {
      const result: AnalyzeResult = await runAnalysis();
      const refreshed = await refresh();

      if (result.alerts_created > 0) {
        setNotice(
          `Analysis complete (${result.detection_method}): ${result.alerts_created} new alert(s) from ${result.buckets_analyzed} bucket(s).` +
            (result.ai_assessment ? ` AI: ${result.ai_assessment}` : ""),
        );
      } else if ((refreshed?.total_logs ?? 0) === 0) {
        setNotice(
          demoEnabled
            ? "No logs found. Click 'Load Sample Data' first, then run analysis again."
            : "No logs found. Upload a log file or scan incoming sources, then run analysis again.",
        );
      } else {
        setNotice(
          `Analysis complete (${result.detection_method}): ${result.buckets_analyzed} bucket(s) scanned.` +
            (result.ai_assessment ? ` AI assessment: ${result.ai_assessment}` : " No new alerts."),
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setAnalyzing(false);
    }
  };

  const handleUpload = async (file: File) => {
    setUploading(true);
    setError(null);
    setNotice(null);
    try {
      const result = await uploadLogFile(file);
      await refresh();
      setNotice(
        `Uploaded ${result.source_file} (${result.format_detected}): ${result.accepted} events ingested.`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleScanSources = async () => {
    setScanning(true);
    setError(null);
    setNotice(null);
    try {
      const result = await scanLogSources();
      await refresh();
      setNotice(
        `Scanned ${result.scanned_files} file(s) from data/incoming: ${result.accepted_events} events ingested.`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Source scan failed");
    } finally {
      setScanning(false);
    }
  };

  const handleSeed = async () => {
    setSeeding(true);
    setError(null);
    setNotice(null);
    try {
      const result = await seedSampleData();
      await refresh();
      setNotice(`Loaded ${result.accepted} sample log events. Click 'Run Analysis' to detect spikes.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load sample data");
    } finally {
      setSeeding(false);
    }
  };

  const handleAlertStatus = async (alertId: string, status: "ACKNOWLEDGED" | "RESOLVED") => {
    setUpdatingAlertId(alertId);
    setError(null);
    try {
      await updateAlertStatus(alertId, status);
      await refresh({ silent: true });
      setNotice(`Alert ${status.toLowerCase()}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update alert");
    } finally {
      setUpdatingAlertId(null);
    }
  };

  return (
    <div className="page">
      <header className="header">
        <div>
          <p className="eyebrow">Wolters Kluwer Assessment</p>
          <h1>Observability Watchdog</h1>
          <p className="subtitle">Intelligent log anomaly detection and alerting</p>
        </div>
        <div className="actions">
          <label className="hours-filter">
            Trend window
            <select
              value={trendHours}
              onChange={(event) => setTrendHours(Number(event.target.value))}
            >
              <option value={6}>6h</option>
              <option value={12}>12h</option>
              <option value={24}>24h</option>
              <option value={48}>48h</option>
            </select>
          </label>
          <button onClick={() => void refresh()} disabled={loading && !summary}>
            Refresh
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json,.jsonl,.ndjson,.log,.txt"
            className="hidden-input"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void handleUpload(file);
            }}
          />
          <button onClick={() => fileInputRef.current?.click()} disabled={uploading}>
            {uploading ? "Uploading..." : "Upload Log File"}
          </button>
          <button onClick={() => void handleScanSources()} disabled={scanning}>
            {scanning ? "Scanning..." : "Scan Incoming"}
          </button>
          {demoEnabled ? (
            <button onClick={() => void handleSeed()} disabled={seeding}>
              {seeding ? "Loading..." : "Load Sample Data"}
            </button>
          ) : null}
          <button className="primary" onClick={() => void handleAnalyze()} disabled={analyzing}>
            {analyzing ? "Analyzing..." : "Run Analysis"}
          </button>
        </div>
      </header>

      {error ? (
        <div className="error-banner" role="alert" aria-live="polite">
          {error}
        </div>
      ) : null}
      {notice ? (
        <div className="notice-banner" role="status" aria-live="polite">
          {notice}
        </div>
      ) : null}
      {loading && !summary ? <p>Loading dashboard...</p> : null}

      {summary ? (
        <>
          <HealthOverview summary={summary} />
          {summary.total_logs === 0 ? (
            <div className="empty-state">
              No logs ingested yet. <strong>Upload Log File</strong>, drop files in{" "}
              <code>data/incoming</code> and click <strong>Scan Incoming</strong>
              {demoEnabled ? (
                <>
                  , or use <strong>Load Sample Data</strong>
                </>
              ) : null}{" "}
              — then <strong>Run Analysis</strong>.
            </div>
          ) : null}
          <div className="grid">
            <TrendChart points={trends} />
            <AlertTable
              alerts={alerts}
              onUpdateStatus={handleAlertStatus}
              updatingId={updatingAlertId}
            />
          </div>
          <WebhookPanel deliveries={deliveries} />
        </>
      ) : null}
    </div>
  );
}
