import { WebhookDelivery } from "../api/client";

type Props = {
  deliveries: WebhookDelivery[];
};

export function WebhookPanel({ deliveries }: Props) {
  return (
    <section className="panel">
      <h2>Webhook Deliveries</h2>
      {deliveries.length === 0 ? (
        <p className="empty">No webhook deliveries yet. Run analysis after loading logs.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Alert</th>
              <th>Status</th>
              <th>Attempt</th>
              <th>Target</th>
            </tr>
          </thead>
          <tbody>
            {deliveries.map((delivery) => (
              <tr key={delivery.id}>
                <td>{new Date(delivery.delivered_at).toLocaleString()}</td>
                <td title={delivery.alert_id}>{delivery.alert_id.slice(0, 8)}…</td>
                <td>
                  <span className={delivery.success ? "badge badge-low" : "badge badge-critical"}>
                    {delivery.success ? "OK" : "FAILED"}
                  </span>
                  {delivery.status_code ? ` (${delivery.status_code})` : null}
                </td>
                <td>{delivery.attempt}</td>
                <td title={delivery.error_message ?? undefined}>{delivery.target_url}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
