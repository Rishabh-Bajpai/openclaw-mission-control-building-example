'use client';

import { useState, useEffect, useCallback, useRef } from 'react';

export interface RateLimitEntry {
  agentId: number;
  retrySeconds: number;
  expiresAt: number;
}

export function useRateLimit() {
  const [limits, setLimits] = useState<Map<number, RateLimitEntry>>(new Map());
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    intervalRef.current = setInterval(() => {
      const now = Date.now();
      setLimits(prev => {
        const next = new Map(prev);
        let changed = false;
        for (const [agentId, entry] of next.entries()) {
          if (entry.expiresAt <= now) {
            next.delete(agentId);
            changed = true;
          }
        }
        return changed ? next : prev;
      });
    }, 1000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, []);

  const setRateLimit = useCallback((agentId: number, retrySeconds: number) => {
    const expiresAt = Date.now() + retrySeconds * 1000;
    setLimits(prev => {
      const next = new Map(prev);
      next.set(agentId, { agentId, retrySeconds, expiresAt });
      return next;
    });
  }, []);

  const getRemainingSeconds = useCallback((agentId: number): number => {
    const entry = limits.get(agentId);
    if (!entry) return 0;
    const remaining = Math.ceil((entry.expiresAt - Date.now()) / 1000);
    return Math.max(0, remaining);
  }, [limits]);

  const isLimited = useCallback((agentId: number): boolean => {
    return limits.has(agentId);
  }, [limits]);

  return { limits, setRateLimit, getRemainingSeconds, isLimited };
}
