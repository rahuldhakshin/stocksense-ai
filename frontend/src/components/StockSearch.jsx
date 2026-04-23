import { Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

export default function StockSearch({ stocks, onSelect, sectorFilter }) {
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");

  useEffect(() => {
    const handle = window.setTimeout(() => setDebounced(query), 300);
    return () => window.clearTimeout(handle);
  }, [query]);

  const results = useMemo(() => {
    const source = (stocks || []).filter((item) => !sectorFilter || item.sector === sectorFilter);
    if (!debounced) return source.slice(0, 8);
    const lower = debounced.toLowerCase();
    return source
      .filter((item) => item.ticker.toLowerCase().includes(lower) || item.company_name.toLowerCase().includes(lower))
      .slice(0, 8);
  }, [stocks, debounced, sectorFilter]);

  return (
    <div className="card-shell p-5">
      <div className="section-title">Search Stocks</div>
      <div className="relative mt-4">
        <Search className="pointer-events-none absolute left-4 top-3.5 h-4 w-4 text-muted" />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search ticker or company name"
          className="w-full rounded-2xl border border-white/10 bg-white/5 py-3 pl-11 pr-4 text-white placeholder:text-muted focus:border-accent focus:ring-0"
        />
      </div>

      <div className="mt-4 space-y-2">
        {results.map((item) => (
          <button
            key={item.ticker}
            type="button"
            onClick={() => onSelect(item.ticker)}
            className="flex w-full items-center justify-between rounded-xl bg-white/5 px-4 py-3 text-left transition hover:bg-white/10"
          >
            <div>
              <div className="font-mono text-sm text-white">{item.ticker}</div>
              <div className="text-xs text-muted">{item.company_name}</div>
            </div>
            <div className="text-xs text-muted">{item.sector}</div>
          </button>
        ))}
      </div>
    </div>
  );
}
