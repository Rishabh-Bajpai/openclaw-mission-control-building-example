const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8002';

interface Agent {
  id: number;
  name: string;
  role: string;
  chief_id: number | null;
  team_id: number | null;
  model: string | null;
  status: 'active' | 'idle' | 'overheated' | 'offline';
  heartbeat_frequency: number;
  active_hours_start: string;
  active_hours_end: string;
  can_spawn_subagents: boolean;
  failure_count: number;
  created_at: string;
  updated_at: string;
  warnings?: string[] | null;
  rate_limited?: boolean | null;
  retry_seconds?: number | null;
}

interface AgentHierarchy {
  id: number;
  name: string;
  role: string;
  status: string;
  chief_id: number | null;
  chief_name: string | null;
  team_id: number | null;
  team_name: string | null;
  model: string | null;
  heartbeat_frequency: number;
  active_hours_start: string;
  active_hours_end: string;
  can_spawn_subagents: boolean;
  failure_count: number;
}

interface Team {
  id: number;
  name: string;
  description: string | null;
  color: string | null;
}

interface Task {
  id: number;
  title: string;
  description: string | null;
  goal_id: number | null;
  agent_id: number | null;
  status: 'backlog' | 'in_progress' | 'review' | 'done';
  priority: number;
  move_reason: string | null;
  created_at: string;
  updated_at: string;
}

interface Goal {
  id: number;
  title: string;
  description: string | null;
  is_main_goal: boolean;
}

interface DashboardStats {
  total_agents: number;
  active_agents: number;
  idle_agents: number;
  overheated_agents: number;
  total_tasks: number;
  backlog_tasks: number;
  in_progress_tasks: number;
  review_tasks: number;
  done_tasks: number;
  total_teams: number;
}

interface ChatMessage {
  id: number;
  agent_id: number;
  sender: string;
  content: string;
  is_from_user: boolean;
  created_at: string;
}

interface Meeting {
  id: number;
  title: string;
  meeting_type: string;
  transcript: string | null;
  briefing: string | null;
  created_at: string;
}

interface AgentLog {
  id: number;
  agent_id: number | null;
  action: string;
  details: string | null;
  created_at: string;
}

export class RateLimitError extends Error {
  retrySeconds: number;
  agentId: number | null;

  constructor(retrySeconds: number, agentId: number | null = null, message?: string) {
    super(message || `Rate limited. Retry in ${retrySeconds} seconds.`);
    this.name = 'RateLimitError';
    this.retrySeconds = retrySeconds;
    this.agentId = agentId;
  }
}

export class GatewayRestartError extends Error {
  retrySeconds: number;
  agentId: number | null;

  constructor(retrySeconds: number, agentId: number | null = null, message?: string) {
    super(message || `OpenClaw Gateway is restarting. Retry in ${retrySeconds} seconds.`);
    this.name = 'GatewayRestartError';
    this.retrySeconds = retrySeconds;
    this.agentId = agentId;
  }
}

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (res.status === 429) {
    let retrySeconds = 60;
    let agentId: number | null = null;
    try {
      const data = await res.json();
      if (data.detail?.retry_seconds) {
        retrySeconds = data.detail.retry_seconds;
        agentId = data.detail.agent_id;
      }
    } catch {}
    throw new RateLimitError(retrySeconds, agentId);
  }
  if (res.status === 503) {
    let retrySeconds = 5;
    let agentId: number | null = null;
    try {
      const data = await res.json();
      if (data.detail?.retry_seconds) {
        retrySeconds = data.detail.retry_seconds;
        agentId = data.detail.agent_id;
      }
    } catch {}
    throw new GatewayRestartError(retrySeconds, agentId);
  }
  if (!res.ok) {
    const error = await res.text();
    throw new Error(`API Error ${res.status}: ${error}`);
  }
  return res.json();
}

export const api = {
  dashboard: {
    stats: () => fetchJSON<DashboardStats>('/dashboard/stats'),
  },
  teams: {
    list: () => fetchJSON<Team[]>('/teams/'),
    get: (id: number) => fetchJSON<Team>(`/teams/${id}`),
    create: (data: { name: string; description?: string }) =>
      fetchJSON<Team>('/teams/', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: number, data: Partial<Team>) =>
      fetchJSON<Team>(`/teams/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    delete: (id: number) => fetch(`${API_BASE}/teams/${id}`, { method: 'DELETE' }),
  },
  agents: {
    list: () => fetchJSON<Agent[]>('/agents/'),
    hierarchy: () => fetchJSON<AgentHierarchy[]>('/agents/hierarchy'),
    get: (id: number) => fetchJSON<Agent>(`/agents/${id}`),
    create: (data: { name: string; role: string; chief_id?: number; team_id?: number; heartbeat_frequency?: number; can_spawn_subagents?: boolean }) =>
      fetchJSON<Agent>('/agents/', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: number, data: Partial<Agent>) =>
      fetchJSON<Agent>(`/agents/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    delete: (id: number) => fetch(`${API_BASE}/agents/${id}`, { method: 'DELETE' }),
    reset: (id: number) => fetchJSON<Agent>(`/agents/${id}/reset`, { method: 'POST' }),
    start: (id: number) => fetchJSON<Agent>(`/agents/${id}/start`, { method: 'POST' }),
    stop: (id: number) => fetchJSON<Agent>(`/agents/${id}/stop`, { method: 'POST' }),
    getFiles: (id: number) => fetchJSON<any>(`/agents/${id}/files`),
    updateFiles: (id: number, files: Record<string, string>) =>
      fetchJSON<{ message: string }>(`/agents/${id}/files`, { method: 'PUT', body: JSON.stringify(files) }),
    getLogs: (id: number, limit = 50) => fetchJSON<AgentLog[]>(`/agents/${id}/logs?limit=${limit}`),
  },
  tasks: {
    list: (params?: { status?: string; agent_id?: number; goal_id?: number }) => {
      const query = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : '';
      return fetchJSON<Task[]>(`/tasks/${query}`);
    },
    get: (id: number) => fetchJSON<Task>(`/tasks/${id}`),
    create: (data: { title: string; description?: string; agent_id?: number; priority?: number }) =>
      fetchJSON<Task>('/tasks/', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: number, data: { status?: string; agent_id?: number; move_reason?: string; title?: string; description?: string }) =>
      fetchJSON<Task>(`/tasks/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    delete: (id: number) => fetch(`${API_BASE}/tasks/${id}`, { method: 'DELETE' }),
  },
  goals: {
    list: () => fetchJSON<Goal[]>('/goals/'),
    get: (id: number) => fetchJSON<Goal>(`/goals/${id}`),
    create: (data: Partial<Goal>) =>
      fetchJSON<Goal>('/goals/', { method: 'POST', body: JSON.stringify(data) }),
    delete: (id: number) => fetch(`${API_BASE}/goals/${id}`, { method: 'DELETE' }),
  },
  chat: {
    messages: (agentId: number, sync: boolean = false) => 
      fetchJSON<ChatMessage[]>(`/chat/${agentId}/messages${sync ? '?sync=true' : ''}`),
    send: (agentId: number, content: string) =>
      fetchJSON<ChatMessage>(`/chat/${agentId}/messages`, { method: 'POST', body: JSON.stringify({ content, is_from_user: true }) }),
    status: (agentId: number) => fetchJSON<any>(`/chat/${agentId}/status`),
    clear: (agentId: number) => fetch(`${API_BASE}/chat/${agentId}/messages`, { method: 'DELETE' }),
  },
  messages: {
    list: (params?: { sender_id?: number; receiver_id?: number; limit?: number }) => {
      const query = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : '';
      return fetchJSON<Message[]>(`/messages/${query}`);
    },
    send: (data: { sender_id: number; receiver_id?: number; content: string }) =>
      fetchJSON<Message>('/messages/', { method: 'POST', body: JSON.stringify(data) }),
  },
  meetings: {
    list: (type?: string) => {
      const query = type ? `?meeting_type=${type}` : '';
      return fetchJSON<Meeting[]>(`/meetings/${query}`);
    },
    runStandup: () => fetchJSON<Meeting>('/meetings/standup', { method: 'POST' }),
  },
  logs: {
    list: (params?: { agent_id?: number; action?: string; limit?: number }) => {
      const query = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : '';
      return fetchJSON<AgentLog[]>(`/logs/${query}`);
    },
  },
};

export type { Agent, AgentHierarchy, Team, Task, Goal, DashboardStats, Message, Meeting, AgentLog };
