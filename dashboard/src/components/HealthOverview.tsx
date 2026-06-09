import { HealthSummary } from "../api/client";

type Props = {
  summary: HealthSummary;
};

function scoreClass(score: number): string {
  if (score >= 80) return "score-good";
  if (score >= 50) return "score-warn";
  return "score-bad";
}

function formatAnalyzedAt(value: string | null): string {
  if (!value) {
    return "Never";
  }
  return new Date(value).toLocaleString();
}

export function HealthOverview({ summary }: Props) {
  return (
    <section className="cards">
      <article className={`card score ${scoreClass(summary.health_score)}`}>
        <h2>Health Score</h2>
        <p className="metric">{summary.health_score}</p>
      </article>
      <article className="card">
        <h2>Total Logs</h2>
        <p className="metric">{summary.total_logs}</p>
      </article>
      <article className="card">
        <h2>Error Rate</h2>
        <p className="metric">{(summary.error_rate * 100).toFixed(1)}%</p>
      </article>
      <article className="card">
        <h2>Open Alerts</h2>
        <p className="metric">{summary.open_alerts}</p>
        <p className="hint">{summary.open_critical_alerts} critical</p>
      </article>
      <article className="card">
        <h2>Last Analysis</h2>
        <p className="metric metric-small">{formatAnalyzedAt(summary.last_analyzed_at)}</p>
      </article>
    </section>
  );
}
