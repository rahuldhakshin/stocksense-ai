import { formatPercent } from "../utils/formatters";

function MoverTable({ title, items, positive }) {
  return (
    <div className="card-shell p-5">
      <div className="section-title">{title}</div>
      <div className="mt-4 space-y-3">
        {items?.length ? (
          items.map((item) => (
            <div key={item.ticker} className="flex items-center justify-between rounded-xl bg-white/5 px-4 py-3">
              <div>
                <div className="font-mono text-sm text-white">{item.ticker}</div>
                <div className="text-xs text-muted">{item.name}</div>
              </div>
              <div className={`font-mono text-sm ${positive ? "text-buy" : "text-danger"}`}>
                {formatPercent(item.change_pct)}
              </div>
            </div>
          ))
        ) : (
          <div className="text-sm text-muted">No movers available.</div>
        )}
      </div>
    </div>
  );
}

export default function TopMovers({ data, loading }) {
  if (loading) {
    return <div className="grid gap-4 lg:grid-cols-2"><div className="skeleton h-64" /><div className="skeleton h-64" /></div>;
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <MoverTable title="Top Gainers" items={data?.gainers || []} positive />
      <MoverTable title="Top Losers" items={data?.losers || []} positive={false} />
    </div>
  );
}
