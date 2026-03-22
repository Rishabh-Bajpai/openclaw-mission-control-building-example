'use client';

import { useEffect, useState } from 'react';
import { api, DashboardStats } from '@/lib/api';

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await api.dashboard.stats();
        setStats(data);
      } catch (error) {
        console.error('Failed to fetch stats:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-[#FBC02D] text-lg">Loading...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold gold-text">Command Center</h1>
          <p className="text-[#888] mt-1">Mission Control Dashboard</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-green-500 pulse-gold"></div>
          <span className="text-sm text-[#888]">System Online</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="stat-card">
          <div className="flex items-center justify-between">
            <span className="text-[#888]">Total Agents</span>
            <span className="text-2xl">🤖</span>
          </div>
          <div className="stat-value mt-2">{stats?.total_agents || 0}</div>
        </div>

        <div className="stat-card">
          <div className="flex items-center justify-between">
            <span className="text-[#888]">Active</span>
            <span className="text-2xl">⚡</span>
          </div>
          <div className="stat-value mt-2 text-green-500">{stats?.active_agents || 0}</div>
        </div>

        <div className="stat-card">
          <div className="flex items-center justify-between">
            <span className="text-[#888]">Idle</span>
            <span className="text-2xl">💤</span>
          </div>
          <div className="stat-value mt-2 text-[#888]">{stats?.idle_agents || 0}</div>
        </div>

        <div className="stat-card">
          <div className="flex items-center justify-between">
            <span className="text-[#888]">Overheated</span>
            <span className="text-2xl">🔥</span>
          </div>
          <div className="stat-value mt-2 text-red-500">{stats?.overheated_agents || 0}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="stat-card">
          <div className="flex items-center justify-between">
            <span className="text-[#888]">Total Tasks</span>
            <span className="text-2xl">📋</span>
          </div>
          <div className="stat-value mt-2">{stats?.total_tasks || 0}</div>
        </div>

        <div className="stat-card">
          <div className="flex items-center justify-between">
            <span className="text-[#888]">In Progress</span>
            <span className="text-2xl">🔄</span>
          </div>
          <div className="stat-value mt-2 text-blue-500">{stats?.in_progress_tasks || 0}</div>
        </div>

        <div className="stat-card">
          <div className="flex items-center justify-between">
            <span className="text-[#888]">In Review</span>
            <span className="text-2xl">👀</span>
          </div>
          <div className="stat-value mt-2 text-yellow-500">{stats?.review_tasks || 0}</div>
        </div>

        <div className="stat-card">
          <div className="flex items-center justify-between">
            <span className="text-[#888]">Teams</span>
            <span className="text-2xl">🏢</span>
          </div>
          <div className="stat-value mt-2">{stats?.total_teams || 0}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card-cyber p-6">
          <h2 className="text-xl font-bold mb-4 gold-text">Quick Actions</h2>
          <div className="space-y-3">
            <a href="/agents" className="btn-gold w-full block text-center">
              Create New Agent
            </a>
            <a href="/standup" className="btn-ghost w-full block text-center">
              Run Daily Standup
            </a>
            <a href="/kanban" className="btn-ghost w-full block text-center">
              View Kanban Board
            </a>
          </div>
        </div>

        <div className="card-cyber p-6">
          <h2 className="text-xl font-bold mb-4 gold-text">System Status</h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between py-2 border-b border-[#222]">
              <span>Backend API</span>
              <span className="text-green-500">● Online</span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-[#222]">
              <span>Database</span>
              <span className="text-green-500">● Connected</span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-[#222]">
              <span>LLM Service</span>
              <span className="text-yellow-500">● Ready</span>
            </div>
            <div className="flex items-center justify-between py-2">
              <span>Scheduler</span>
              <span className="text-green-500">● Active</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
