import { useEffect, useState } from "react";
import axios from "axios";
import { API_BASE } from "../utils/constants";

export function useStockData(endpoint, enabled = true) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(Boolean(enabled));
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    if (!enabled || !endpoint) {
      setLoading(false);
      return undefined;
    }

    async function fetchData() {
      try {
        setLoading(true);
        setError(null);
        const response = await axios.get(`${API_BASE}${endpoint}`);
        if (active) {
          setData(response.data);
        }
      } catch (err) {
        if (active) {
          setError(err?.response?.data?.detail?.error || err.message || "Request failed");
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    fetchData();
    return () => {
      active = false;
    };
  }, [endpoint, enabled]);

  return { data, loading, error, setData };
}
