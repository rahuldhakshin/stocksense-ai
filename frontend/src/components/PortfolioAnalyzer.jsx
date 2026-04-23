import { Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import axios from "axios";
import { API_BASE } from "../utils/constants";
import { formatCurrency, formatPercent } from "../utils/formatters";

export default function PortfolioAnalyzer({ stocks }) {
  const [holdings, setHoldings] = useState([{ ticker: "RELIANCE.NS", quantity: 10, avg_buy_price: 2500 }]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const options = useMemo(() => (stocks || []).slice(0, 100), [stocks]);

  const updateHolding = (index, key, value) => {
    setHoldings((current) => current.map((item, itemIndex) => (itemIndex === index ? { ...item, [key]: value } : item)));
  };

  const addHolding = () => setHoldings((current) => [...current, { ticker: "TCS.NS", quantity: 1, avg_buy_price: 1000 }]);
  const removeHolding = (index) => setHoldings((current) => current.filter((_, itemIndex) => itemIndex !== index));

  const analyze = async () => {
    setLoading(true);
    try {
      const response = await axios.post(`${API_BASE}/api/portfolio/analyze`, { holdings });
      setResult(response.data);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <section className="card-shell p-5">
        <div className="flex items-center justify-between">
          <div className="section-title">Portfolio Inputs</div>
          <button type="button" onClick={addHolding} className="rounded-full bg-accent px-4 py-2 text-sm text-bg">
            Add Holding
          </button>
        </div>
        <div className="mt-4 space-y-3">
          {holdings.map((holding, index) => (
            <div key={`${holding.ticker}-${index}`} className="grid gap-3 rounded-2xl bg-white/5 p-4 md:grid-cols-[2fr_1fr_1fr_auto]">
              <select value={holding.ticker} onChange={(event) => updateHolding(index, "ticker", event.target.value)} className="rounded-xl border-white/10 bg-bg/60">
                {options.map((option) => <option key={option.ticker} value={option.ticker}>{option.ticker} - {option.company_name}</option>)}
              </select>
              <input value={holding.quantity} onChange={(event) => updateHolding(index, "quantity", Number(event.target.value))} type="number" className="rounded-xl border-white/10 bg-bg/60" placeholder="Qty" />
              <input value={holding.avg_buy_price} onChange={(event) => updateHolding(index, "avg_buy_price", Number(event.target.value))} type="number" className="rounded-xl border-white/10 bg-bg/60" placeholder="Buy Price" />
              <button type="button" onClick={() => removeHolding(index)} className="rounded-xl bg-danger/15 px-3 text-danger"><Trash2 className="h-4 w-4" /></button>
            </div>
          ))}
        </div>
        <button type="button" onClick={analyze} className="mt-4 rounded-full bg-accent px-4 py-2 text-sm text-bg">
          {loading ? "Analyzing..." : "Analyze Portfolio"}
        </button>
      </section>

      {result && (
        <section className="space-y-6">
          <div className="grid gap-4 md:grid-cols-4">
            <div className="card-shell p-5"><div className="section-title">Total Invested</div><div className="mt-3 font-mono text-2xl">{formatCurrency(result.total_invested)}</div></div>
            <div className="card-shell p-5"><div className="section-title">Current Value</div><div className="mt-3 font-mono text-2xl">{formatCurrency(result.current_value)}</div></div>
            <div className="card-shell p-5"><div className="section-title">Total P&L</div><div className="mt-3 font-mono text-2xl">{formatCurrency(result.pnl)}</div></div>
            <div className="card-shell p-5"><div className="section-title">Risk Score</div><div className="mt-3 font-mono text-2xl">{result.risk_score.label}</div></div>
          </div>

          <div className="card-shell overflow-hidden p-5">
            <div className="section-title">Holdings</div>
            <div className="mt-4 overflow-x-auto">
              <table className="min-w-full text-left text-sm">
                <thead className="text-muted">
                  <tr><th className="pb-3">Ticker</th><th>Qty</th><th>Avg</th><th>CMP</th><th>P&L</th><th>P&L%</th><th>Signal</th></tr>
                </thead>
                <tbody>
                  {result.holdings.map((item) => (
                    <tr key={item.ticker} className="border-t border-white/5">
                      <td className="py-3 font-mono">{item.ticker}</td>
                      <td>{item.quantity}</td>
                      <td>{formatCurrency(item.avg_buy_price)}</td>
                      <td>{formatCurrency(item.cmp)}</td>
                      <td>{formatCurrency(item.pnl)}</td>
                      <td>{formatPercent(item.pnl_pct)}</td>
                      <td><span className="rounded-full bg-white/10 px-3 py-1 font-mono text-xs">{item.signal}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
