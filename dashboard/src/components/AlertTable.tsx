import { Alert } from "../api/client";

type Props = {
  alerts: Alert[];
  onUpdateStatus: (alertId: string, status: "ACKNOWLEDGED" | "RESOLVED") => Promise<void>;
  updatingId: string | null;
};

function severityClass(severity: string): string {
  return `badge badge-${severity.toLowerCase()}`;
}

function statusClass(status: string): string {
  return `badge badge-status-${status.toLowerCase()}`;
}

export function AlertTable({ alerts, onUpdateStatus, updatingId }: Props) {
  return (
    <section className="panel">
      <h2>Alert Timeline</h2>
      {alerts.length === 0 ? (
        <p className="empty">No alerts detected.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Severity</th>
              <th>Type</th>
              <th>Title</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {alerts.map((alert) => (
              <tr key={alert.id}>
                <td>{new Date(alert.detected_at).toLocaleString()}</td>
                <td>
                  <span className={severityClass(alert.severity)}>{alert.severity}</span>
                </td>
                <td>{alert.alert_type}</td>
                <td title={alert.description}>{alert.title}</td>
                <td>
                  <span className={statusClass(alert.status)}>{alert.status}</span>
                </td>
                <td className="actions-cell">
                  {alert.status === "OPEN" ? (
                    <button
                      type="button"
                      className="small"
                      disabled={updatingId === alert.id}
                      onClick={() => void onUpdateStatus(alert.id, "ACKNOWLEDGED")}
                    >
                      ACK
                    </button>
                  ) : null}
                  {alert.status !== "RESOLVED" ? (
                    <button
                      type="button"
                      className="small"
                      disabled={updatingId === alert.id}
                      onClick={() => void onUpdateStatus(alert.id, "RESOLVED")}
                    >
                      Resolve
                    </button>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
