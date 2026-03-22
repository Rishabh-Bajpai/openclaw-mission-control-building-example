'use client';

import { useEffect, useState, useRef } from 'react';
import { api, AgentLog } from '@/lib/api';

export default function TerminalPage() {
  const [logs, setLogs] = useState<AgentLog[]>([]);
  const [loading, setLoading] = useState(true);
  const logsEndRef = useRef<HTMLDivElement>(null);

  const fetchLogs = async () => {
    try {
      const data = await api.logs.list({ limit: 100 });
      setLogs(data);
    } catch (error) {
      console.error('Failed to fetch logs:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const getActionColor = (action: string) => {
    if (action.includes('CREATED')) return 'text-green-500';
    if (action.includes('DELETED') || action.includes('FAILED')) return 'text-red-500';
    if (action.includes('RUN')) return 'text-blue-500';
    if (action.includes('MOVED')) return 'text-yellow-500';
    return 'text-[#888]';
  };

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleTimeString('en-US', { hour12: false });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-[#FBC02D] text-lg">Loading...</div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-3xl font-bold gold-text">Live Terminal</h1>
          <p className="text-[#888] mt-1">Agent activity logs</p>
        </div>
        <button onClick={fetchLogs} className="btn-ghost">
          🔄 Refresh
        </button>
      </div>

      <div className="flex-1 bg-[#0d0d0d] rounded-lg border border-[#222] overflow-hidden">
        <div className="p-4 font-mono text-sm h-full overflow-auto scrollbar-thin">
          <div className="space-y-1">
            {logs.map((log) => (
              <div key={log.id} className="flex gap-4 py-1 border-b border-[#1a1a1a]">
                <span className="text-[#666] shrink-0">
                  [{formatTime(log.created_at)}]
                </span>
                <span className={`shrink-0 ${getActionColor(log.action)}`}>
                  [{log.action}]
                </span>
                <span className="text-[#888]">
                  Agent #{log.agent_id}:
                </span>
                <span className="text-white flex-1">
                  {log.details || 'No details'}
                </span>
              </div>
            ))}
            {logs.length === 0 && (
              <div className="text-center text-[#888] py-8">
                No logs yet. Actions will appear here in real-time.
              </div>
            )}
            <div ref={logsEndRef} />
          </div>
        </div>
      </div>

      <div className="mt-4 flex items-center justify-between text-sm text-[#888]">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-500"></span>
            Connected
          </span>
          <span>Auto-refresh: 5s</span>
          <span title="System timezone">{Intl.DateTimeFormat().resolvedOptions().timeZone}</span>
        </div>
        <span>{logs.length} entries</span>
      </div>
    </div>
  );
}
