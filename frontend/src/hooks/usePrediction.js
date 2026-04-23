import { useStockData } from "./useStockData";

export function usePrediction(ticker, model = "rf") {
  return useStockData(
    ticker ? `/api/stock/${ticker}/predict?model=${model}` : null,
    Boolean(ticker)
  );
}
