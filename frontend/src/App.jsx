import { useMemo, useState } from "react";
import AnalysisCard from "./components/AnalysisCard";
import Dashboard from "./components/Dashboard";
import MarketOverview from "./components/MarketOverview";
import Navbar from "./components/Navbar";
import PortfolioAnalyzer from "./components/PortfolioAnalyzer";
import PredictionPanel from "./components/PredictionPanel";
import StockChart from "./components/StockChart";
import { usePrediction } from "./hooks/usePrediction";
import { useStockData } from "./hooks/useStockData";

function ErrorBlock({ message }) {
  return <div className="card-shell p-5 text-sm text-danger">{message}</div>;
}

export default function App() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [selectedTicker, setSelectedTicker] = useState("RELIANCE.NS");
  const [period, setPeriod] = useState("1y");
  const [sectorFilter, setSectorFilter] = useState("");
  const [model, setModel] = useState("rf");

  const stocks = useStockData("/api/stocks/list");
  const overview = useStockData("/api/market/overview");
  const movers = useStockData("/api/market/top-movers");
  const sectors = useStockData("/api/market/sector-performance");
  const history = useStockData(selectedTicker ? `/api/stock/${selectedTicker}/history?period=${period}` : null, Boolean(selectedTicker));
  const analysis = useStockData(selectedTicker ? `/api/stock/${selectedTicker}/analysis` : null, Boolean(selectedTicker));
  const prediction = usePrediction(selectedTicker, model);

  const analysisView = useMemo(
    () => (
      <div className="space-y-6">
        <StockChart ticker={selectedTicker} data={history.data} period={period} onPeriodChange={setPeriod} loading={history.loading} error={history.error} />
        <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <PredictionPanel prediction={prediction.data} model={model} onModelChange={setModel} loading={prediction.loading} />
          <AnalysisCard analysis={analysis.data} loading={analysis.loading} />
        </div>
      </div>
    ),
    [analysis.data, analysis.loading, history.data, history.error, history.loading, model, period, prediction.data, prediction.loading, selectedTicker]
  );

  return (
    <div className="min-h-screen px-4 py-4 md:px-6">
      <Navbar activeTab={activeTab} onChange={setActiveTab} />

      <main className="mx-auto mt-6 max-w-7xl">
        {stocks.error ? <ErrorBlock message={stocks.error} /> : null}

        {activeTab === "dashboard" && (
          <Dashboard
            overview={overview.data}
            movers={movers.data}
            sectors={sectors.data}
            stocks={stocks.data}
            loadingOverview={overview.loading}
            loadingMovers={movers.loading}
            onSelectTicker={(ticker) => {
              setSelectedTicker(ticker);
              setActiveTab("analysis");
            }}
            onSelectSector={setSectorFilter}
            sectorFilter={sectorFilter}
          />
        )}

        {activeTab === "analysis" && analysisView}
        {activeTab === "portfolio" && <PortfolioAnalyzer stocks={stocks.data} />}
        {activeTab === "market" && <MarketOverview overview={overview.data} sectors={sectors.data} />}
      </main>
    </div>
  );
}
