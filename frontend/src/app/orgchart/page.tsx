'use client';

import { useEffect, useState } from 'react';
import { api, AgentHierarchy, Team } from '@/lib/api';

const BOSS_NODE = {
  id: -1,
  name: 'Boss',
  role: 'CEO',
  status: 'active',
  chief_id: null,
  chief_name: null,
  team_id: null,
  team_name: null,
  model: null,
  heartbeat_frequency: 0,
  active_hours_start: '00:00',
  active_hours_end: '23:59',
  can_spawn_subagents: false,
  failure_count: 0,
};

const DEFAULT_COLORS = [
  '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
  '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9',
];

export default function OrgChartPage() {
  const [agents, setAgents] = useState<AgentHierarchy[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingTeam, setEditingTeam] = useState<number | null>(null);
  const [editColor, setEditColor] = useState('#FF6B6B');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [agentsData, teamsData] = await Promise.all([
          api.agents.hierarchy(),
          api.teams.list(),
        ]);
        setAgents(agentsData);
        setTeams(teamsData);
      } catch (error) {
        console.error('Failed to fetch data:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const getTeamColor = (teamId: number | null) => {
    if (!teamId) return null;
    const team = teams.find(t => t.id === teamId);
    return team?.color || null;
  };

  const getStatusClass = (status: string) => {
    switch (status) {
      case 'active': return 'status-active';
      case 'idle': return 'status-idle';
      case 'overheated': return 'status-overheated';
      default: return 'status-idle';
    }
  };

  const getAgentsByChiefId = (chiefId: number | null) => {
    return agents.filter(a => a.chief_id === chiefId);
  };

  const handleColorChange = async (teamId: number, color: string) => {
    try {
      await api.teams.update(teamId, { color });
      setTeams(teams.map(t => t.id === teamId ? { ...t, color } : t));
      setEditingTeam(null);
    } catch (error) {
      console.error('Failed to update team color:', error);
    }
  };

  const renderAgent = (agent: AgentHierarchy, level: number = 0, isBoss: boolean = false) => {
    const subordinates = getAgentsByChiefId(agent.id);
    const teamColor = getTeamColor(agent.team_id);
    const borderStyle = teamColor ? { borderColor: teamColor } : {};
    
    return (
      <div key={agent.id} className="flex flex-col items-center">
        <div 
          className={`org-node ${level === 0 ? 'ceo' : ''}`}
          style={borderStyle}
          onClick={() => agent.team_id && setEditingTeam(agent.team_id)}
        >
          <div className={`w-12 h-12 rounded-full flex items-center justify-center text-black font-bold mx-auto mb-2 ${
            isBoss ? 'bg-[#FBC02D] border-4 border-white' : level === 0 ? 'bg-[#FBC02D]' : 'bg-[#1a1a1a]'
          }`}
          style={!isBoss && teamColor ? { border: `3px solid ${teamColor}` } : !isBoss && level > 0 ? { border: '3px solid #FBC02D' } : {}}>
            {agent.name[0]}
          </div>
          <h3 className="font-bold text-lg">{agent.name}</h3>
          <p className="text-[#FBC02D] text-sm">{agent.role}</p>
          {agent.team_name && (
            <div className="flex items-center gap-1 mt-1">
              {teamColor && (
                <div 
                  className="w-3 h-3 rounded-full cursor-pointer hover:opacity-80"
                  style={{ backgroundColor: teamColor }}
                  onClick={(e) => {
                    e.stopPropagation();
                    setEditingTeam(agent.team_id);
                    setEditColor(teamColor);
                  }}
                />
              )}
              <p className="text-[#888] text-xs">{agent.team_name}</p>
            </div>
          )}
          {agent.id !== -1 && (
            <span className={`status-badge ${getStatusClass(agent.status)} mt-2`}>
              {agent.status}
            </span>
          )}
          {agent.heartbeat_frequency > 0 && (
            <p className="text-[#666] text-xs mt-2">Heartbeat: {agent.heartbeat_frequency}m</p>
          )}
        </div>
        
        {subordinates.length > 0 && (
          <>
            <svg className="h-4 w-2 text-[#333]">
              <line x1="1" y1="0" x2="1" y2="16" stroke="currentColor" strokeWidth="2" />
            </svg>
            <div className="flex gap-4 flex-wrap justify-center mt-2">
              {subordinates.map(sub => renderAgent(sub, level + 1))}
            </div>
          </>
        )}
      </div>
    );
  };

  const agentsWithNoChief = getAgentsByChiefId(null);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-[#FBC02D] text-lg">Loading...</div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col relative">
      <div className="mb-6">
        <h1 className="text-3xl font-bold gold-text">Organization Chart</h1>
        <p className="text-[#888] mt-1">Agent Hierarchy ({agents.length} agents)</p>
        {teams.length > 0 && (
          <p className="text-[#666] text-xs mt-1">Click on a team badge to change its color</p>
        )}
      </div>

      {editingTeam && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setEditingTeam(null)}>
          <div className="bg-[#1a1a1a] border border-[#333] rounded-lg p-6 w-80" onClick={e => e.stopPropagation()}>
            <h3 className="text-lg font-bold text-white mb-4">
              Team Color: {teams.find(t => t.id === editingTeam)?.name}
            </h3>
            <div className="grid grid-cols-5 gap-2 mb-4">
              {DEFAULT_COLORS.map(color => (
                <button
                  key={color}
                  onClick={() => setEditColor(color)}
                  className={`w-10 h-10 rounded-full border-2 ${editColor === color ? 'border-white scale-110' : 'border-transparent'}`}
                  style={{ backgroundColor: color }}
                />
              ))}
            </div>
            <div className="flex gap-2 mb-4">
              <input
                type="color"
                value={editColor}
                onChange={(e) => setEditColor(e.target.value)}
                className="w-10 h-10 rounded cursor-pointer"
              />
              <input
                type="text"
                value={editColor}
                onChange={(e) => setEditColor(e.target.value)}
                className="input-cyber flex-1"
                placeholder="#FF6B6B"
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => handleColorChange(editingTeam, editColor)}
                className="btn-gold flex-1"
              >
                Save
              </button>
              <button
                onClick={() => setEditingTeam(null)}
                className="btn-ghost"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="flex-1 overflow-auto scrollbar-thin p-4">
        {agents.length === 0 ? (
          <div className="text-center text-[#888] py-8">
            <p className="text-lg mb-2">No agents yet</p>
            <p className="text-sm">Create agents in the Agent Studio to see the org chart</p>
          </div>
        ) : (
          <div className="flex flex-col items-center">
            {renderAgent(BOSS_NODE, 0, true)}
            {agentsWithNoChief.length > 0 && (
              <>
                <svg className="h-4 w-2 text-[#333]">
                  <line x1="1" y1="0" x2="1" y2="16" stroke="currentColor" strokeWidth="2" />
                </svg>
                <div className="flex gap-4 flex-wrap justify-center mt-2">
                  {agentsWithNoChief.map(agent => renderAgent(agent, 1))}
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
