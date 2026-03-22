'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { api, AgentLog, Agent } from '@/lib/api';

const ACTION_FILTERS = ['ALL', 'CREATED', 'DELETED', 'FAILED', 'RUN', 'MOVED', 'STARTED', 'STOPPED', 'UPDATED'];
const WS_URL = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8002').replace('http', 'ws') + '/ws/logs';
const HEIGHT_PRESETS = [
  { label: 'S', value: 200 },
  { label: 'M', value: 300 },
  { label: 'L', value: 400 },
  { label: 'XL', value: 600 },
];

interface BackendLog {
  timestamp: string;
  level: string;
  logger: string;
  message: string;
}

export default function LogTerminal() {
  const [isExpanded, setIsExpanded] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const [terminalHeight, setTerminalHeight] = useState(300);
  const [backendLogs, setBackendLogs] = useState<BackendLog[]>([]);
  const [agentLogs, setAgentLogs] = useState<AgentLog[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [actionFilter, setActionFilter] = useState('ALL');
  const [agentFilter, setAgentFilter] = useState<number | 'ALL'>('ALL');
  const [sourceFilter, setSourceFilter] = useState<'all' | 'backend' | 'agent'>('all');
  const logsEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const fetchAgents = useCallback(async () => {
    try {
      const data = await api.agents.list();
      setAgents(data);
    } catch (error) {
      console.error('Failed to fetch agents:', error);
    }
  }, []);

  const fetchAgentLogs = useCallback(async () => {
    try {
      const params: { limit: number; action?: string; agent_id?: number } = { limit: 50 };
      if (actionFilter !== 'ALL') params.action = actionFilter;
      if (agentFilter !== 'ALL') params.agent_id = agentFilter as number;
      const data = await api.logs.list(params);
      setAgentLogs(data);
    } catch (error) {
      console.error('Failed to fetch agent logs:', error);
    }
  }, [actionFilter, agentFilter]);

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  useEffect(() => {
    if (!isExpanded) {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      return;
    }

    const connect = () => {
      try {
        wsRef.current = new WebSocket(WS_URL);

        wsRef.current.onmessage = (event) => {
          const log: BackendLog = JSON.parse(event.data);
          setBackendLogs(prev => {
            const next = [...prev, log];
            return next.length > 500 ? next.slice(-500) : next;
          });
        };

        wsRef.current.onclose = () => {
          if (isExpanded) {
            setTimeout(connect, 3000);
          }
        };

        wsRef.current.onerror = () => {
          wsRef.current?.close();
        };
      } catch {
      }
    };

    connect();
    fetchAgentLogs();

    const agentPollInterval = setInterval(fetchAgentLogs, 5000);

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      clearInterval(agentPollInterval);
    };
  }, [isExpanded, fetchAgentLogs]);

  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [backendLogs, agentLogs, autoScroll]);

  const getActionColor = (action: string) => {
    if (action.includes('RATE_LIMITED')) return 'text-orange-400';
    if (action.includes('CREATED') || action.includes('STARTED')) return 'text-green-400';
    if (action.includes('DELETED') || action.includes('FAILED')) return 'text-red-400';
    if (action.includes('RUN')) return 'text-blue-400';
    if (action.includes('MOVED')) return 'text-yellow-400';
    if (action.includes('STOPPED')) return 'text-orange-400';
    if (action.includes('UPDATED')) return 'text-purple-400';
    return 'text-[#888]';
  };

  const getBackendLogColor = (level: string) => {
    if (level === 'DEBUG') return 'text-[#555]';
    if (level === 'INFO') return 'text-blue-400';
    if (level === 'WARNING' || level === 'WARN') return 'text-yellow-400';
    if (level === 'ERROR') return 'text-red-400';
    if (level === 'TRACE') return 'text-[#666]';
    return 'text-[#888]';
  };

  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleTimeString('en-US', { hour12: false });
  };

  const getAgentName = (agentId: number | null) => {
    if (!agentId) return 'System';
    const agent = agents.find(a => a.id === agentId);
    return agent ? agent.name : `#${agentId}`;
  };

  const filteredAgentLogs = agentLogs.filter(log => {
    if (actionFilter !== 'ALL' && !log.action.includes(actionFilter)) return false;
    if (agentFilter !== 'ALL' && log.agent_id !== agentFilter) return false;
    return true;
  });

  const latestLog = [...backendLogs, ...filteredAgentLogs.map(l => ({ ...l, timestamp: l.created_at, level: l.action, logger: 'agent', message: l.details || '—', id: l.id }))].sort((a, b) => {
    const ta = new Date(a.timestamp).getTime();
    const tb = new Date(b.timestamp).getTime();
    return tb - ta;
  })[0];

  const wsConnected = wsRef.current?.readyState === WebSocket.OPEN;

  return (
    <div
      className={`fixed bottom-0 left-[240px] right-0 bg-[#0a0a0a] border-t border-[#333] transition-all duration-300 z-40 ${
        isExpanded ? '' : 'h-[44px]'
      }`}
      style={isExpanded ? { height: `${terminalHeight}px` } : undefined}
    >
      <div
        className="h-[44px] flex items-center justify-between px-4 cursor-pointer hover:bg-[#111]"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <span className="text-[#FBC02D] text-lg">⬢</span>
          <span className="text-white font-medium text-sm">Terminal</span>
          {latestLog && !isExpanded && (
            <span className="text-[#666] text-xs ml-4">
              [{formatTime(latestLog.timestamp)}]{' '}
              <span className={latestLog.logger === 'agent' ? getActionColor(latestLog.level) : getBackendLogColor(latestLog.level)}>
                {latestLog.logger === 'agent' ? latestLog.level : `[${latestLog.level}]`}
              </span>{' '}
              {latestLog.logger === 'agent' ? `${getAgentName((latestLog as any).agent_id)}:` : `${latestLog.logger}:`}{' '}
              {String(latestLog.message).slice(0, 50)}{String(latestLog.message).length > 50 ? '...' : ''}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3" onClick={(e) => e.stopPropagation()}>
          <span className="text-[#888] text-xs">
            {backendLogs.length + filteredAgentLogs.length} entries
          </span>
          <span className="text-[#666] text-xs" title="System timezone">
            {Intl.DateTimeFormat().resolvedOptions().timeZone}
          </span>
          <span className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-500' : 'bg-[#555]'}`} title={wsConnected ? 'Backend logs connected' : 'Connecting...'} />
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsExpanded(!isExpanded);
            }}
            className="text-[#888] hover:text-white transition-colors"
          >
            {isExpanded ? '▼' : '▲'}
          </button>
        </div>
      </div>

      {isExpanded && (
        <div className="h-[calc(100%-44px)] flex flex-col">
          <div className="flex items-center gap-3 px-4 py-2 border-b border-[#222] overflow-x-auto">
            <div className="flex items-center gap-2 shrink-0">
              <label className="text-[#888] text-xs">Source:</label>
              <select
                value={sourceFilter}
                onChange={(e) => setSourceFilter(e.target.value as 'all' | 'backend' | 'agent')}
                className="bg-[#1a1a1a] border border-[#333] rounded px-2 py-1 text-xs text-white focus:outline-none focus:border-[#FBC02D]"
              >
                <option value="all">All</option>
                <option value="backend">Backend</option>
                <option value="agent">Agent</option>
              </select>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <label className="text-[#888] text-xs">Action:</label>
              <select
                value={actionFilter}
                onChange={(e) => setActionFilter(e.target.value)}
                className="bg-[#1a1a1a] border border-[#333] rounded px-2 py-1 text-xs text-white focus:outline-none focus:border-[#FBC02D]"
              >
                {ACTION_FILTERS.map((f) => (
                  <option key={f} value={f}>{f}</option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <label className="text-[#888] text-xs">Agent:</label>
              <select
                value={agentFilter}
                onChange={(e) => setAgentFilter(e.target.value === 'ALL' ? 'ALL' : Number(e.target.value))}
                className="bg-[#1a1a1a] border border-[#333] rounded px-2 py-1 text-xs text-white focus:outline-none focus:border-[#FBC02D]"
              >
                <option value="ALL">All</option>
                {agents.map((a) => (
                  <option key={a.id} value={a.id}>{a.name}</option>
                ))}
              </select>
            </div>

            <button
              onClick={fetchAgentLogs}
              className="text-[#888] hover:text-[#FBC02D] text-xs transition-colors shrink-0"
            >
              🔄 Refresh
            </button>

            <div className="flex items-center gap-2 ml-auto shrink-0">
              <label className="text-[#888] text-xs">Size:</label>
              <div className="flex gap-0.5">
                {HEIGHT_PRESETS.map((p) => (
                  <button
                    key={p.value}
                    onClick={() => setTerminalHeight(p.value)}
                    className={`px-1.5 py-0.5 text-xs rounded transition-colors ${
                      terminalHeight === p.value
                        ? 'bg-[#FBC02D] text-black font-medium'
                        : 'bg-[#1a1a1a] text-[#888] hover:text-white border border-[#333]'
                    }`}
                    title={`${p.value}px`}
                  >
                    {p.label}
                  </button>
                ))}
              </div>

              <label className="text-[#888] text-xs cursor-pointer ml-2">
                <input
                  type="checkbox"
                  checked={autoScroll}
                  onChange={(e) => setAutoScroll(e.target.checked)}
                  className="mr-1"
                />
                Auto-scroll
              </label>
            </div>
          </div>

          <div className="flex-1 overflow-auto scrollbar-thin">
            <div className="p-2 font-mono text-xs space-y-0.5">
              {backendLogs.map((log, i) => {
                if (sourceFilter === 'agent') return null;
                return (
                  <div
                    key={`backend-${i}`}
                    className="flex gap-3 py-0.5 px-2 hover:bg-[#1a1a1a] rounded"
                  >
                    <span className="text-[#555] shrink-0">
                      {formatTime(log.timestamp)}
                    </span>
                    <span className={`shrink-0 ${getBackendLogColor(log.level)}`}>
                      {log.level}
                    </span>
                    <span className="text-[#666] shrink-0">
                      {log.logger}:
                    </span>
                    <span className="text-[#aaa] flex-1 truncate">
                      {log.message}
                    </span>
                  </div>
                );
              })}

              {filteredAgentLogs.map((log) => {
                if (sourceFilter === 'backend') return null;
                return (
                  <div
                    key={`agent-${log.id}`}
                    className="flex gap-3 py-0.5 px-2 hover:bg-[#1a1a1a] rounded"
                  >
                    <span className="text-[#555] shrink-0">
                      {formatTime(log.created_at)}
                    </span>
                    <span className={`shrink-0 ${getActionColor(log.action)}`}>
                      {log.action}
                    </span>
                    <span className="text-[#666] shrink-0">
                      {getAgentName(log.agent_id)}:
                    </span>
                    <span className="text-[#aaa] flex-1 truncate">
                      {log.details || '—'}
                    </span>
                  </div>
                );
              })}

              {backendLogs.length === 0 && filteredAgentLogs.length === 0 && (
                <div className="text-center text-[#555] py-4">
                  No logs yet. Actions will appear here in real-time.
                </div>
              )}
              <div ref={logsEndRef} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
