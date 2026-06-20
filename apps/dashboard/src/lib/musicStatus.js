// Phase 2B — read-only music status loader.
// Fetches the same-origin API path (proxied by nginx to the FastAPI service).
// It NEVER calls http://localhost:8000 directly: the Docker path is /api/...
import { useEffect, useState } from "react";

export const API_PATH = "/api/music/status";
export const RESPONSE_SCHEMA_VERSION = "phase2b.musicStatus.v1";

export const DataState = {
  LOADING: "loading",
  LIVE: "live",
  DEGRADED: "degraded",
  UNAVAILABLE: "unavailable",
};

// Fetch and validate the status envelope. Throws on any condition the UI should
// treat as "API unavailable" — including a proxy misconfiguration that returns
// the HTML shell instead of JSON.
export async function fetchMusicStatus(signal) {
  const response = await fetch(API_PATH, {
    signal,
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    throw new Error(`unexpected HTTP ${response.status}`);
  }
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    // e.g. nginx returned index.html — proxy/prefix-strip misconfigured.
    throw new Error("response was not JSON");
  }
  const data = await response.json();
  if (!data || data.schemaVersion !== RESPONSE_SCHEMA_VERSION) {
    throw new Error("unrecognized status schema");
  }
  return data;
}

// React hook: loads once on mount and reports a coarse data state.
export function useMusicStatus() {
  const [result, setResult] = useState({ state: DataState.LOADING, data: null });

  useEffect(() => {
    const controller = new AbortController();
    fetchMusicStatus(controller.signal)
      .then((data) => {
        setResult({
          state: data.status === "degraded" ? DataState.DEGRADED : DataState.LIVE,
          data,
        });
      })
      .catch((error) => {
        if (error.name === "AbortError") return;
        setResult({ state: DataState.UNAVAILABLE, data: null });
      });
    return () => controller.abort();
  }, []);

  return result;
}
