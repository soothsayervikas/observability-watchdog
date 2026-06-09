import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { TrendPoint } from "../api/client";

type Props = {
  points: TrendPoint[];
};

const SERIES_COLORS = ["#38bdf8", "#a78bfa", "#34d399", "#fbbf24", "#f87171"];

function formatBucketLabel(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function buildChartData(points: TrendPoint[]) {
  const byBucket = new Map<string, Record<string, string | number>>();

  for (const point of points) {
    const bucketKey = point.bucket_start;
    const label = formatBucketLabel(point.bucket_start);
    const seriesKey = point.service ?? "global";
    const row = byBucket.get(bucketKey) ?? { label, bucketKey };
    row[seriesKey] = Number((point.error_rate * 100).toFixed(2));
    byBucket.set(bucketKey, row);
  }

  return Array.from(byBucket.values()).sort((a, b) =>
    String(a.bucketKey).localeCompare(String(b.bucketKey)),
  );
}

function seriesKeys(points: TrendPoint[]): string[] {
  const keys = new Set<string>();
  for (const point of points) {
    keys.add(point.service ?? "global");
  }
  return Array.from(keys).sort();
}

export function TrendChart({ points }: Props) {
  const data = buildChartData(points);
  const keys = seriesKeys(points);

  return (
    <section className="panel">
      <h2>Error Rate Trend</h2>
      {data.length === 0 ? (
        <p className="empty">No trend data yet. Ingest logs and run analysis.</p>
      ) : (
        <div className="chart-wrap">
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="label" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" unit="%" />
              <Tooltip />
              {keys.length > 1 ? <Legend /> : null}
              {keys.map((key, index) => (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  name={key === "global" ? "All services" : key}
                  stroke={SERIES_COLORS[index % SERIES_COLORS.length]}
                  strokeWidth={2}
                  dot={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}
