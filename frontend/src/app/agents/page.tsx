'use client';

import { useEffect, useState, useCallback } from 'react';
import { api, Agent, Team, RateLimitError, GatewayRestartError } from '@/lib/api';
import { useRateLimit } from '@/lib/useRateLimit';

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showTeamsModal, setShowTeamsModal] = useState(false);
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);
  const [editingTeam, setEditingTeam] = useState<Team | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<{ type: 'agent' | 'team'; id: number; name: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [newTeam, setNewTeam] = useState({ name: '', description: '', color: '' });
  const [editTeam, setEditTeam] = useState({ name: '', description: '', color: '' });
  const [newAgent, setNewAgent] = useState({
    name: '',
    role: '',
    chief_id: undefined as number | undefined,
    team_id: undefined as number | undefined,
    can_spawn_subagents: false,
    heartbeat_frequency: 15,
  });
  const [editAgent, setEditAgent] = useState({
    name: '',
    role: '',
    chief_id: undefined as number | undefined,
    team_id: undefined as number | undefined,
    can_spawn_subagents: false,
    heartbeat_frequency: 15,
  });

  const { isLimited, getRemainingSeconds, setRateLimit } = useRateLimit();

  const fetchData = async () => {
    try {
      setError(null);
      const [agentsData, teamsData] = await Promise.all([
        api.agents.list(),
        api.teams.list(),
      ]);
      setAgents(agentsData);
      setTeams(teamsData);
    } catch (error) {
      console.error('Failed to fetch data:', error);
      setError('Failed to load data. Is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreateAgent = async () => {
    if (!newAgent.name.trim()) {
      alert('Agent name is required');
      return;
    }
    if (!newAgent.role.trim()) {
      alert('Agent role is required');
      return;
    }
    
    try {
      setError(null);
      await api.agents.create(newAgent);
      setNewAgent({
        name: '',
        role: '',
        chief_id: undefined,
        team_id: undefined,
        can_spawn_subagents: false,
        heartbeat_frequency: 15,
      });
      setShowCreateModal(false);
      fetchData();
    } catch (error) {
      console.error('Failed to create agent:', error);
      const errMsg = error instanceof Error ? error.message : 'Unknown error';
      setError(`Failed to create agent: ${errMsg}`);
      alert('Failed to create agent. Check console for details.');
    }
  };

  const handleCreateTeam = async () => {
    if (!newTeam.name.trim()) {
      alert('Team name is required');
      return;
    }
    try {
      await api.teams.create(newTeam);
      setNewTeam({ name: '', description: '', color: '' });
      setShowTeamsModal(false);
      fetchData();
    } catch (error) {
      console.error('Failed to create team:', error);
      setError('Failed to create team');
    }
  };

  const handleDeleteAgent = async (id: number) => {
    try {
      await api.agents.delete(id);
      setDeleteConfirm(null);
      setSelectedAgent(null);
      fetchData();
    } catch (error) {
      console.error('Failed to delete agent:', error);
      setError('Failed to delete agent');
    }
  };

  const handleDeleteTeam = async (id: number) => {
    try {
      await api.teams.delete(id);
      setDeleteConfirm(null);
      fetchData();
    } catch (error) {
      console.error('Failed to delete team:', error);
      setError('Failed to delete team');
    }
  };

  const handleStartAgent = async (id: number) => {
    try {
      await api.agents.start(id);
      setError(null);
      fetchData();
    } catch (error) {
      if (error instanceof RateLimitError) {
        setRateLimit(id, error.retrySeconds);
        setError(`Rate limited. Retry in ${error.retrySeconds}s.`);
      } else if (error instanceof GatewayRestartError) {
        setRateLimit(id, error.retrySeconds);
        setError(`OpenClaw Gateway restarting. Retry in ${error.retrySeconds}s.`);
      } else {
        console.error('Failed to start agent:', error);
        alert('Failed to start agent: ' + (error instanceof Error ? error.message : 'Unknown error'));
      }
    }
  };

  const handleStopAgent = async (id: number) => {
    try {
      await api.agents.stop(id);
      setError(null);
      fetchData();
    } catch (error) {
      if (error instanceof RateLimitError) {
        setRateLimit(id, error.retrySeconds);
        setError(`Rate limited. Retry in ${error.retrySeconds}s.`);
      } else if (error instanceof GatewayRestartError) {
        setRateLimit(id, error.retrySeconds);
        setError(`OpenClaw Gateway restarting. Retry in ${error.retrySeconds}s.`);
      } else {
        console.error('Failed to stop agent:', error);
        alert('Failed to stop agent: ' + (error instanceof Error ? error.message : 'Unknown error'));
      }
    }
  };

  const handleEditAgent = (agent: Agent) => {
    setEditingAgent(agent);
    setEditAgent({
      name: agent.name,
      role: agent.role,
      chief_id: agent.chief_id ?? undefined,
      team_id: agent.team_id ?? undefined,
      can_spawn_subagents: agent.can_spawn_subagents,
      heartbeat_frequency: agent.heartbeat_frequency,
    });
  };

  const handleUpdateAgent = async () => {
    if (!editingAgent || !editAgent.name.trim() || !editAgent.role.trim()) {
      alert('Agent name and role are required');
      return;
    }
    try {
      setError(null);
      await api.agents.update(editingAgent.id, {
        name: editAgent.name,
        role: editAgent.role,
        chief_id: editAgent.chief_id,
        team_id: editAgent.team_id,
        can_spawn_subagents: editAgent.can_spawn_subagents,
        heartbeat_frequency: editAgent.heartbeat_frequency,
      });
      setError(null);
      setEditingAgent(null);
      fetchData();
    } catch (error) {
      if (error instanceof RateLimitError) {
        setRateLimit(editingAgent.id, error.retrySeconds);
        setError(`Rate limited. Retry in ${error.retrySeconds}s.`);
      } else if (error instanceof GatewayRestartError) {
        setRateLimit(editingAgent.id, error.retrySeconds);
        setError(`OpenClaw Gateway restarting. Retry in ${error.retrySeconds}s.`);
      } else {
        setError('Failed to update agent');
      }
    }
  };

  const handleEditTeam = (team: Team) => {
    setEditingTeam(team);
    setEditTeam({
      name: team.name,
      description: team.description || '',
      color: team.color || '#FF6B6B',
    });
  };

  const handleUpdateTeam = async () => {
    if (!editingTeam || !editTeam.name.trim()) {
      alert('Team name is required');
      return;
    }
    try {
      setError(null);
      await api.teams.update(editingTeam.id, editTeam);
      setEditingTeam(null);
      fetchData();
    } catch (error) {
      console.error('Failed to update team:', error);
      setError('Failed to update team');
    }
  };

  const getStatusClass = (status: string) => {
    switch (status) {
      case 'active': return 'status-active';
      case 'idle': return 'status-idle';
      case 'overheated': return 'status-overheated';
      default: return 'status-idle';
    }
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
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold gold-text">Agent Studio</h1>
          <p className="text-[#888] mt-1">Create and manage AI agents</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowTeamsModal(true)} className="btn-ghost">
            + New Team
          </button>
          <button onClick={() => setShowCreateModal(true)} className="btn-gold">
            + New Agent
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto scrollbar-thin">
        {agents.length === 0 ? (
          <div className="text-center text-[#888] py-12">
            <p className="text-lg mb-2">No agents yet</p>
            <p className="text-sm mb-4">Create your first agent to get started</p>
            <button onClick={() => setShowCreateModal(true)} className="btn-gold">
              + Create Agent
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {agents.map((agent) => (
              <div key={agent.id} className="card-cyber p-4 cursor-pointer hover:border-[#FBC02D]" onClick={() => setSelectedAgent(agent)}>
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-[#FBC02D] flex items-center justify-center text-black font-bold">
                      {agent.name[0]}
                    </div>
                    <div>
                      <h3 className="font-bold">{agent.name}</h3>
                      <p className="text-sm text-[#888]">{agent.role}</p>
                    </div>
                  </div>
                  <span className={`status-badge ${getStatusClass(agent.status)}`}>
                    {agent.status}
                  </span>
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-[#888]">Team:</span>
                    <span>{teams.find(t => t.id === agent.team_id)?.name || 'None'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#888]">Reports to:</span>
                    <span>{agents.find(a => a.id === agent.chief_id)?.name || 'Boss'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#888]">Heartbeat:</span>
                    <span>{agent.heartbeat_frequency}m</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[#888]">Spawn Sub-agents:</span>
                    <span>{agent.can_spawn_subagents ? 'Yes' : 'No'}</span>
                  </div>
                  {agent.failure_count > 0 && (
                    <div className="flex justify-between">
                      <span className="text-[#888]">Failures:</span>
                      <span className="text-red-500">{agent.failure_count}</span>
                    </div>
                  )}
                </div>
                <div className="flex gap-2 mt-4">
                  {isLimited(agent.id) ? (
                    <button 
                      disabled
                      className="bg-orange-600 text-white font-bold py-2 px-4 rounded text-sm flex-1 cursor-not-allowed opacity-75"
                      title={`Rate limited. Wait ${getRemainingSeconds(agent.id)}s`}
                    >
                      Wait {getRemainingSeconds(agent.id)}s...
                    </button>
                  ) : agent.heartbeat_frequency > 0 ? (
                    <button 
                      onClick={(e) => { e.stopPropagation(); handleStopAgent(agent.id); }} 
                      className="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded text-sm flex-1"
                    >
                      Stop
                    </button>
                  ) : (
                    <button 
                      onClick={(e) => { e.stopPropagation(); handleStartAgent(agent.id); }} 
                      className="btn-gold text-sm flex-1"
                    >
                      Start
                    </button>
                  )}
                  <button 
                    onClick={(e) => { e.stopPropagation(); handleEditAgent(agent); }} 
                    className="btn-ghost text-sm"
                    title="Edit agent"
                  >
                    ✏️
                  </button>
                  <button 
                    onClick={(e) => { e.stopPropagation(); setDeleteConfirm({ type: 'agent', id: agent.id, name: agent.name }); }} 
                    className="btn-ghost text-sm hover:border-red-500 hover:text-red-500"
                    title="Delete agent"
                  >
                    🗑️
                  </button>
                  {!isLimited(agent.id) && agent.status === 'overheated' && (
                    <button 
                      onClick={(e) => { e.stopPropagation(); handleStartAgent(agent.id); }} 
                      className="btn-gold text-sm flex-1"
                    >
                      Restart
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
        
        {teams.length > 0 && (
          <div className="mt-8">
            <h2 className="text-xl font-bold mb-4 gold-text">Teams</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {teams.map((team) => (
                <div key={team.id} className="card-cyber p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      {team.color && (
                        <div 
                          className="w-4 h-4 rounded-full"
                          style={{ backgroundColor: team.color }}
                        />
                      )}
                      <div>
                        <h3 className="font-bold">{team.name}</h3>
                        <p className="text-sm text-[#888]">{team.description || 'No description'}</p>
                      </div>
                    </div>
                    <div className="flex gap-1">
                      <button 
                        onClick={() => handleEditTeam(team)} 
                        className="btn-ghost text-sm"
                        title="Edit team"
                      >
                        ✏️
                      </button>
                      <button 
                        onClick={() => setDeleteConfirm({ type: 'team', id: team.id, name: team.name })} 
                        className="btn-ghost text-sm hover:border-red-500 hover:text-red-500"
                        title="Delete team"
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                  <div className="mt-2 text-sm text-[#666]">
                    {agents.filter(a => a.team_id === team.id).length} agents
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        
        {error && (
          <div className="fixed bottom-4 left-4 right-4 bg-red-900/80 border border-red-500 text-white p-4 rounded-lg">
            <div className="flex items-center justify-between">
              <span>{error}</span>
              <button onClick={() => setError(null)} className="text-white/80 hover:text-white">✕</button>
            </div>
          </div>
        )}
      </div>

      {showCreateModal && (
        <div className="fixed inset-0 modal-overlay flex items-center justify-center z-50">
          <div className="card-cyber p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4 gold-text">Create New Agent</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-[#888] mb-1">Name</label>
                <input
                  type="text"
                  value={newAgent.name}
                  onChange={(e) => setNewAgent({ ...newAgent, name: e.target.value })}
                  className="input-cyber"
                  placeholder="Agent name"
                />
              </div>
              <div>
                <label className="block text-sm text-[#888] mb-1">Role</label>
                <input
                  type="text"
                  value={newAgent.role}
                  onChange={(e) => setNewAgent({ ...newAgent, role: e.target.value })}
                  className="input-cyber"
                  placeholder="e.g., COO, Developer, Designer"
                />
              </div>
              <div>
                <label className="block text-sm text-[#888] mb-1">Team</label>
                <select
                  value={newAgent.team_id || ''}
                  onChange={(e) => setNewAgent({ ...newAgent, team_id: e.target.value ? Number(e.target.value) : undefined })}
                  className="input-cyber"
                >
                  <option value="">No Team</option>
                  {teams.map((team) => (
                    <option key={team.id} value={team.id}>{team.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-[#888] mb-1">Reports To (Chief)</label>
                <select
                  value={newAgent.chief_id || ''}
                  onChange={(e) => setNewAgent({ ...newAgent, chief_id: e.target.value ? Number(e.target.value) : undefined })}
                  className="input-cyber"
                >
                  <option value="">Reports directly to Boss</option>
                  {agents.map((agent) => (
                    <option key={agent.id} value={agent.id}>{agent.name} ({agent.role})</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-[#888] mb-1">Heartbeat (minutes)</label>
                <input
                  type="number"
                  value={newAgent.heartbeat_frequency}
                  onChange={(e) => setNewAgent({ ...newAgent, heartbeat_frequency: Number(e.target.value) })}
                  className="input-cyber"
                  min="0"
                  max="60"
                />
                <p className="text-xs text-[#666] mt-1">0 = disabled</p>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="can_spawn"
                  checked={newAgent.can_spawn_subagents}
                  onChange={(e) => setNewAgent({ ...newAgent, can_spawn_subagents: e.target.checked })}
                  className="w-4 h-4"
                />
                <label htmlFor="can_spawn" className="text-sm">Can Spawn Sub-agents</label>
              </div>
              <div className="flex gap-3">
                <button onClick={handleCreateAgent} className="btn-gold flex-1">
                  Create
                </button>
                <button onClick={() => setShowCreateModal(false)} className="btn-ghost flex-1">
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {showTeamsModal && (
        <div className="fixed inset-0 modal-overlay flex items-center justify-center z-50">
          <div className="card-cyber p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4 gold-text">Create New Team</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-[#888] mb-1">Name</label>
                <input
                  type="text"
                  value={newTeam.name}
                  onChange={(e) => setNewTeam({ ...newTeam, name: e.target.value })}
                  className="input-cyber"
                  placeholder="Team name"
                />
              </div>
              <div>
                <label className="block text-sm text-[#888] mb-1">Description</label>
                <textarea
                  value={newTeam.description}
                  onChange={(e) => setNewTeam({ ...newTeam, description: e.target.value })}
                  className="input-cyber"
                  placeholder="Team description"
                />
              </div>
              <div className="flex gap-3">
                <button onClick={handleCreateTeam} className="btn-gold flex-1">
                  Create
                </button>
                <button onClick={() => setShowTeamsModal(false)} className="btn-ghost flex-1">
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {editingAgent && (
        <div className="fixed inset-0 modal-overlay flex items-center justify-center z-50">
          <div className="card-cyber p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4 gold-text">Edit Agent</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-[#888] mb-1">Name</label>
                <input
                  type="text"
                  value={editAgent.name}
                  disabled
                  className="input-cyber opacity-50 cursor-not-allowed"
                />
                <p className="text-xs text-[#666] mt-1">Name cannot be changed after creation</p>
              </div>
              <div>
                <label className="block text-sm text-[#888] mb-1">Role</label>
                <input
                  type="text"
                  value={editAgent.role}
                  onChange={(e) => setEditAgent({ ...editAgent, role: e.target.value })}
                  className="input-cyber"
                  placeholder="e.g., COO, Developer, Designer"
                />
              </div>
              <div>
                <label className="block text-sm text-[#888] mb-1">Team</label>
                <select
                  value={editAgent.team_id || ''}
                  onChange={(e) => setEditAgent({ ...editAgent, team_id: e.target.value ? Number(e.target.value) : undefined })}
                  className="input-cyber"
                >
                  <option value="">No Team</option>
                  {teams.map((team) => (
                    <option key={team.id} value={team.id}>{team.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-[#888] mb-1">Reports To (Chief)</label>
                <select
                  value={editAgent.chief_id || ''}
                  onChange={(e) => setEditAgent({ ...editAgent, chief_id: e.target.value ? Number(e.target.value) : undefined })}
                  className="input-cyber"
                >
                  <option value="">Reports directly to Boss</option>
                  {agents.filter(a => a.id !== editingAgent.id).map((agent) => (
                    <option key={agent.id} value={agent.id}>{agent.name} ({agent.role})</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-[#888] mb-1">Heartbeat (minutes)</label>
                <input
                  type="number"
                  value={editAgent.heartbeat_frequency}
                  onChange={(e) => setEditAgent({ ...editAgent, heartbeat_frequency: Number(e.target.value) })}
                  className="input-cyber"
                  min="0"
                  max="60"
                />
                <p className="text-xs text-[#666] mt-1">0 = disabled</p>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="edit_can_spawn"
                  checked={editAgent.can_spawn_subagents}
                  onChange={(e) => setEditAgent({ ...editAgent, can_spawn_subagents: e.target.checked })}
                  className="w-4 h-4"
                />
                <label htmlFor="edit_can_spawn" className="text-sm">Can Spawn Sub-agents</label>
              </div>
              <div className="flex gap-3">
                {isLimited(editingAgent.id) ? (
                  <button disabled className="bg-orange-600 text-white font-bold py-2 px-4 rounded flex-1 cursor-not-allowed opacity-75">
                    Wait {getRemainingSeconds(editingAgent.id)}s...
                  </button>
                ) : (
                  <button onClick={handleUpdateAgent} className="btn-gold flex-1">
                    Save
                  </button>
                )}
                <button onClick={() => setEditingAgent(null)} className="btn-ghost flex-1">
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {editingTeam && (
        <div className="fixed inset-0 modal-overlay flex items-center justify-center z-50">
          <div className="card-cyber p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4 gold-text">Edit Team</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-[#888] mb-1">Name</label>
                <input
                  type="text"
                  value={editTeam.name}
                  onChange={(e) => setEditTeam({ ...editTeam, name: e.target.value })}
                  className="input-cyber"
                  placeholder="Team name"
                />
              </div>
              <div>
                <label className="block text-sm text-[#888] mb-1">Description</label>
                <textarea
                  value={editTeam.description}
                  onChange={(e) => setEditTeam({ ...editTeam, description: e.target.value })}
                  className="input-cyber"
                  placeholder="Team description"
                />
              </div>
              <div>
                <label className="block text-sm text-[#888] mb-1">Color</label>
                <div className="flex gap-2 items-center">
                  <input
                    type="color"
                    value={editTeam.color}
                    onChange={(e) => setEditTeam({ ...editTeam, color: e.target.value })}
                    className="w-10 h-10 rounded cursor-pointer"
                  />
                  <input
                    type="text"
                    value={editTeam.color}
                    onChange={(e) => setEditTeam({ ...editTeam, color: e.target.value })}
                    className="input-cyber flex-1"
                    placeholder="#FF6B6B"
                  />
                </div>
              </div>
              <div className="flex gap-3">
                <button onClick={handleUpdateTeam} className="btn-gold flex-1">
                  Save
                </button>
                <button onClick={() => setEditingTeam(null)} className="btn-ghost flex-1">
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {deleteConfirm && (
        <div className="fixed inset-0 modal-overlay flex items-center justify-center z-50">
          <div className="card-cyber p-6 w-full max-w-md border-red-500/50">
            <h2 className="text-xl font-bold mb-4 text-red-500">Delete {deleteConfirm.type === 'agent' ? 'Agent' : 'Team'}</h2>
            <p className="text-[#888] mb-4">
              Are you sure you want to delete <span className="text-white font-bold">{deleteConfirm.name}</span>?
              {deleteConfirm.type === 'agent' && ' This will also remove the agent from OpenClaw.'}
            </p>
            <div className="flex gap-3">
              <button 
                onClick={() => {
                  if (deleteConfirm.type === 'agent') {
                    handleDeleteAgent(deleteConfirm.id);
                  } else {
                    handleDeleteTeam(deleteConfirm.id);
                  }
                }} 
                className="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded flex-1"
              >
                Delete
              </button>
              <button onClick={() => setDeleteConfirm(null)} className="btn-ghost flex-1">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
