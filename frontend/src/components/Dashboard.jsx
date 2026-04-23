import MarketOverview from "./MarketOverview";
import SectorHeatmap from "./SectorHeatmap";
import StockSearch from "./StockSearch";
import TopMovers from "./TopMovers";

export default function Dashboard({
  overview,
  movers,
  sectors,
  stocks,
  loadingOverview,
  loadingMovers,
  onSelectTicker,
  onSelectSector,
  sectorFilter,
}) {
  return (
    <div className="space-y-6">
      <MarketOverview overview={overview} sectors={(sectors || []).slice(0, 10)} />
      <StockSearch stocks={stocks} onSelect={onSelectTicker} sectorFilter={sectorFilter} />
      <TopMovers data={movers} loading={loadingMovers || loadingOverview} />
      <SectorHeatmap sectors={sectors} onSelect={onSelectSector} />
    </div>
  );
}
