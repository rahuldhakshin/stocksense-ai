import { formatNumber, formatPercent } from "../utils/formatters";

function Tile({ title, children }) {
  return (
    <div className="rounded-2xl bg-white/5 p-4">
      <div className="text-xs uppercase tracking-[0.18em] text-muted">{title}</div>
      <div className="mt-3">{children}</div>
    </div>
  );
}

export default function AnalysisCard({ analysis, loading }) {
  if (loading) return <div className="skeleton h-96" />;
  if (!analysis) return <div className="card-shell p-5 text-sm text-muted">Analysis unavailable.</div>;

  return (
    <section className="card-shell p-5">
      <div className="section-title">Technical Analysis</div>
      <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <Tile title="RSI Gauge">
          <div className="font-mono text-3xl text-accent">{formatNumber(analysis.rsi?.value)}</div>
          <div className="mt-2 text-sm text-muted">{analysis.rsi?.interpretation}</div>
        </Tile>
        <Tile title="MACD Signal">
          <div className="font-medium text-white">{analysis.macd?.signal}</div>
        </Tile>
        <Tile title="Bollinger Position">
          <div className="font-medium text-white">{analysis.bollinger_position}</div>
        </Tile>
        <Tile title="Volume Trend">
          <div className="font-medium text-white">{analysis.volume_analysis?.status}</div>
          <div className="mt-2 text-sm text-muted">
            Avg 20D: {formatNumber(analysis.volume_analysis?.average_20d)}
          </div>
        </Tile>
        <Tile title="52 Week Range">
          <div className="font-mono text-sm text-white">
            {formatNumber(analysis.fifty_two_week_low)} - {formatNumber(analysis.fifty_two_week_high)}
          </div>
        </Tile>
        <Tile title="Sentiment">
          <div className="font-medium text-white">{analysis.overall_sentiment}</div>
          <div className="mt-2 font-mono text-sm text-accent">{formatPercent(analysis.confidence_score)}</div>
        </Tile>
        <Tile title="Support Levels">
          <div className="space-y-1 font-mono text-sm text-white">
            {(analysis.support_resistance?.support || []).map((value) => <div key={value}>{formatNumber(value)}</div>)}
          </div>
        </Tile>
        <Tile title="Resistance Levels">
          <div className="space-y-1 font-mono text-sm text-white">
            {(analysis.support_resistance?.resistance || []).map((value) => <div key={value}>{formatNumber(value)}</div>)}
          </div>
        </Tile>
        <Tile title="Momentum Window">
          <div className="space-y-1 text-sm">
            <div>Day: {formatPercent(analysis.day_change_pct)}</div>
            <div>Week: {formatPercent(analysis.week_change_pct)}</div>
            <div>Month: {formatPercent(analysis.month_change_pct)}</div>
          </div>
        </Tile>
      </div>
    </section>
  );
}
