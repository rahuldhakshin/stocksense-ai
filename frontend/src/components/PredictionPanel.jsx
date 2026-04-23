import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatCurrency, formatPercent } from "../utils/formatters";

const SIGNAL_CLASS = {
  BUY: "bg-buy/15 text-buy animate-pulse-signal",
  SELL: "bg-danger/15 text-danger animate-pulse-signal",
  HOLD: "bg-white/10 text-white",
};

export default function PredictionPanel({ prediction, model, onModelChange, loading }) {
  const importanceData = Object.entries(prediction?.feature_importance || {}).map(([name, value]) => ({ name, value }));

  return (
    <section className="card-shell p-5">
      <div className="flex items-center justify-between">
        <div className="section-title">Prediction Engine</div>
        <div className="flex gap-2">
          <button type="button" onClick={() => onModelChange("rf")} className={`rounded-full px-3 py-1.5 text-xs ${model === "rf" ? "bg-accent text-bg" : "bg-white/5 text-white/70"}`}>Random Forest</button>
          <button type="button" onClick={() => onModelChange("gb")} className={`rounded-full px-3 py-1.5 text-xs ${model === "gb" ? "bg-accent text-bg" : "bg-white/5 text-white/70"}`}>Gradient Boosting</button>
        </div>
      </div>

      {loading ? (
        <div className="skeleton mt-5 h-80" />
      ) : prediction?.error ? (
        <div className="mt-5 rounded-2xl bg-white/5 p-4 text-sm text-muted">Models not ready</div>
      ) : (
        <div className="mt-5 space-y-5">
          <div className={`inline-flex rounded-full px-5 py-3 font-mono text-xl ${SIGNAL_CLASS[prediction?.direction || "HOLD"]}`}>
            {prediction?.direction || "HOLD"}
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-2xl bg-white/5 p-4">
              <div className="text-xs text-muted">Current Price</div>
              <div className="mt-2 font-mono text-2xl">{formatCurrency(prediction?.current_price)}</div>
            </div>
            <div className="rounded-2xl bg-white/5 p-4">
              <div className="text-xs text-muted">Predicted Price</div>
              <div className="mt-2 font-mono text-2xl">{formatCurrency(prediction?.predicted_price)}</div>
            </div>
            <div className="rounded-2xl bg-white/5 p-4">
              <div className="text-xs text-muted">Expected Change</div>
              <div className={`mt-2 font-mono text-2xl ${prediction?.predicted_change_pct >= 0 ? "text-buy" : "text-danger"}`}>
                {formatPercent(prediction?.predicted_change_pct)}
              </div>
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-[160px_1fr]">
            <div className="flex h-40 w-40 items-center justify-center rounded-full border-8 border-accent/20 bg-white/5 font-mono text-3xl text-accent">
              {Math.round(prediction?.confidence || 0)}%
            </div>

            <div className="h-48 rounded-2xl bg-white/5 p-3">
              <div className="mb-2 text-xs text-muted">Top Feature Importance</div>
              <ResponsiveContainer>
                <BarChart data={importanceData} layout="vertical">
                  <XAxis type="number" hide />
                  <YAxis dataKey="name" type="category" width={110} tick={{ fill: "#8C96B8", fontSize: 10 }} />
                  <Tooltip />
                  <Bar dataKey="value" fill="#00D4AA" radius={[0, 6, 6, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="text-xs text-muted">For educational purposes only. Not financial advice.</div>
        </div>
      )}
    </section>
  );
}
