"use client";

import { useCallback, useEffect, useState } from "react";

// Retry reads after an outage; successful pages do not poll or replay writes.
export function useLoadRetry(failed:boolean, loading:boolean) {
  const [attempt, setAttempt] = useState(0);
  const retry = useCallback(() => setAttempt((value) => value + 1), []);

  useEffect(() => {
    if (!failed || loading) return;
    let requested = false;
    const reconnect = () => {
      if (requested || !navigator.onLine) return;
      requested = true;
      retry();
    };
    const timer = window.setTimeout(reconnect, 15_000);
    window.addEventListener("online", reconnect);
    window.addEventListener("focus", reconnect);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("online", reconnect);
      window.removeEventListener("focus", reconnect);
    };
  }, [failed, loading, attempt, retry]);

  return { attempt, retry };
}
