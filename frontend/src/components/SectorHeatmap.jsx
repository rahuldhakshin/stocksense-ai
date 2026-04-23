import { formatPercent } from "../utils/formatters";

function getTileColor(value) {
  if (value > 1.5) return "bg-buy/25 border-buy/40";
  if (value > 0) return "bg-buy/10 border-buy/20";
  if (value < -1.5) return "bg-danger/25 border-danger/40";
  if (value < 0) return "bg-danger/10 border-danger/20";
  return "bg-white/5 border-white/10";
}

export default function SectorHeatmap({ sectors, onSelect }) {
  return (
    <section className="card-shell p-5">
      <div className="section-title">Sector Heatmap</div>
      <div className="mt-4 grid gap-3 md:grid-cols-3 xl:grid-cols-4">
        {sectors?.length ? (
          sectors.map((sector) => (
            <button
              key={sector.sector}
              type="button"
              onClick={() => onSelect?.(sector.sector)}
              className={`min-h-28 rounded-2xl border p-4 text-left transition hover:-translate-y-0.5 ${getTileColor(sector.avg_return_pct)}`}
            >
              <div className="font-medium text-white">{sector.sector}</div>
              <div className="mt-3 font-mono text-lg">{formatPercent(sector.avg_return_pct)}</div>
              <div className="mt-2 text-xs text-muted">{sector.count} stocks tracked</div>
            </button>
          ))
        ) : (
          <div className="text-sm text-muted">Sector performance is not available.</div>
        )}
      </div>
    </section>
  );
}
