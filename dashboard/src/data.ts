import { useEffect, useState } from "react";
import type { Report } from "./types";

interface UseReportResult {
  report: Report | null;
  loading: boolean;
  error: string | null;
}

export function useReport(): UseReportResult {
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}data/report.json`)
      .then((res) => {
        if (!res.ok) throw new Error(`report.json: HTTP ${res.status}`);
        return res.json();
      })
      .then((data: Report) => setReport(data))
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));
  }, []);

  return { report, loading, error };
}
