import {
  Bar,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { PERIOD_OPTIONS } from "../utils/constants";
import { formatNumber } from "../utils/formatters";

export default function StockChart({ ticker, data, period, onPeriodChange, loading, error }) {
  const chartData = data?.data || [];

  return (
    <section className="card-shell p-5">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="section-title">Price Action</div>
          <div className="mt-2 font-mono text-xl text-white">{ticker || "Select a stock"}</div>
        </div>
        <div className="flex flex-wrap gap-2">
          {PERIOD_OPTIONS.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => onPeriodChange(option.value)}
              className={`rounded-full px-3 py-1.5 text-xs ${
                option.value === period ? "bg-accent text-bg" : "bg-white/5 text-white/70"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="skeleton mt-6 h-[620px]" />
      ) : error ? (
        <div className="mt-6 rounded-2xl bg-danger/10 p-4 text-sm text-danger">{error}</div>
      ) : chartData.length ? (
        <div className="mt-6 grid gap-5">
          <div className="h-80">
            <ResponsiveContainer>
              <ComposedChart data={chartData}>
                <XAxis dataKey="date" hide />
                <YAxis domain={["auto", "auto"]} tick={{ fill: "#8C96B8" }} />
                <Tooltip
                  contentStyle={{ background: "#0F1629", border: "1px solid rgba(255,255,255,0.08)" }}
                  formatter={(value) => formatNumber(value)}
                />
                <Bar dataKey="high" fill="rgba(0,0,0,0)" stroke="#3A4668" />
                <Bar dataKey="low" fill="rgba(0,0,0,0)" stroke="#3A4668" />
                <Line type="monotone" dataKey="close" stroke="#00D4AA" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="sma_20" stroke="#F4D35E" dot={false} />
                <Line type="monotone" dataKey="sma_50" stroke="#4D9DE0" dot={false} />
                <Line type="monotone" dataKey="bb_upper" stroke="#9B5DE5" strokeDasharray="5 5" dot={false} />
                <Line type="monotone" dataKey="bb_lower" stroke="#9B5DE5" strokeDasharray="5 5" dot={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          <div className="h-40">
            <ResponsiveContainer>
              <ComposedChart data={chartData}>
                <XAxis dataKey="date" tick={{ fill: "#8C96B8", fontSize: 10 }} />
                <YAxis tick={{ fill: "#8C96B8" }} />
                <Tooltip />
                <Bar dataKey="volume" fill="#00D4AA" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          <div className="h-32">
            <ResponsiveContainer>
              <ComposedChart data={chartData}>
                <XAxis dataKey="date" hide />
                <YAxis domain={[0, 100]} tick={{ fill: "#8C96B8" }} />
                <Tooltip />
                <Line type="monotone" dataKey="rsi" stroke="#FF6B35" dot={false} />
                <Line type="monotone" data={[{ rsi: 70 }, { rsi: 70 }]} dataKey="rsi" stroke="#ffffff33" dot={false} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
      ) : (
        <div className="mt-6 text-sm text-muted">No chart data available.</div>
      )}
    </section>
  );
}
