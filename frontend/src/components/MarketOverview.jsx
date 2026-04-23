import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatNumber, formatPercent } from "../utils/formatters";

export default function MarketOverview({ overview, sectors }) {
  const overviewItems = Object.entries(overview || {});
  const breadth = {
    advances: (sectors || []).filter((item) => item.avg_return_pct > 0).length,
    declines: (sectors || []).filter((item) => item.avg_return_pct < 0).length,
  };

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        {overviewItems.map(([name, item]) => (
          <div key={name} className="card-shell p-5">
            <div className="section-title">{name}</div>
            <div className="mt-3 font-mono text-2xl">{formatNumber(item.current_value)}</div>
            <div className={`mt-1 font-mono text-sm ${item.day_change_pct >= 0 ? "text-buy" : "text-danger"}`}>
              {formatPercent(item.day_change_pct)}
            </div>
            <div className="mt-3 text-xs text-muted">
              52W: {formatNumber(item.fifty_two_week_low)} - {formatNumber(item.fifty_two_week_high)}
            </div>
          </div>
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-[2fr_1fr]">
        <div className="card-shell p-5">
          <div className="section-title">Sector Performance</div>
          <div className="mt-4 h-80">
            <ResponsiveContainer>
              <BarChart data={sectors || []}>
                <CartesianGrid stroke="rgba(255,255,255,0.05)" vertical={false} />
                <XAxis dataKey="sector" tick={{ fill: "#8C96B8", fontSize: 11 }} angle={-20} textAnchor="end" height={70} />
                <YAxis tick={{ fill: "#8C96B8" }} />
                <Tooltip />
                <Bar dataKey="avg_return_pct" fill="#00D4AA" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card-shell p-5">
          <div className="section-title">Market Breadth</div>
          <div className="mt-6 space-y-4">
            <div className="rounded-2xl bg-buy/10 p-4">
              <div className="text-sm text-muted">Advances</div>
              <div className="font-mono text-3xl text-buy">{breadth.advances}</div>
            </div>
            <div className="rounded-2xl bg-danger/10 p-4">
              <div className="text-sm text-muted">Declines</div>
              <div className="font-mono text-3xl text-danger">{breadth.declines}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
