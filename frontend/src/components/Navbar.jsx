import { format } from "date-fns";
import { useEffect, useState } from "react";
import { NAV_ITEMS } from "../utils/constants";

function isMarketOpen(date) {
  const day = date.getDay();
  const hours = date.getHours();
  const minutes = date.getMinutes();
  if (day === 0 || day === 6) return false;
  const current = hours * 60 + minutes;
  return current >= 9 * 60 + 15 && current <= 15 * 60 + 30;
}

export default function Navbar({ activeTab, onChange }) {
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <header className="card-shell sticky top-4 z-20 mx-auto flex max-w-7xl items-center justify-between gap-6 px-6 py-4">
      <div>
        <div className="font-mono text-lg font-bold text-accent">📈 StockSense AI</div>
        <div className="text-sm text-muted">Indian Stock Market Analytics & Prediction</div>
      </div>

      <nav className="hidden gap-2 md:flex">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => onChange(item.id)}
            className={`rounded-full px-4 py-2 text-sm transition ${
              activeTab === item.id ? "bg-accent text-bg" : "bg-white/5 text-white/80 hover:bg-white/10"
            }`}
          >
            {item.label}
          </button>
        ))}
      </nav>

      <div className="text-right">
        <div className="font-mono text-sm">{format(now, "dd MMM yyyy, HH:mm:ss")}</div>
        <div className={`text-xs ${isMarketOpen(now) ? "text-buy" : "text-danger"}`}>
          {isMarketOpen(now) ? "OPEN 09:15–15:30 IST" : "CLOSED"}
        </div>
      </div>
    </header>
  );
}
