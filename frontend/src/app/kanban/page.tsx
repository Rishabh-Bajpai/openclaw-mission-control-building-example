'use client';

import { useEffect, useState } from 'react';
import { api, Task, Agent } from '@/lib/api';

const columns = [
  { id: 'backlog', title: 'Backlog', color: '#888' },
  { id: 'in_progress', title: 'In Progress', color: '#2196F3' },
  { id: 'review', title: 'Review', color: '#FF9800' },
  { id: 'done', title: 'Done', color: '#4CAF50' },
];

export default function KanbanPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [draggedTask, setDraggedTask] = useState<Task | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<{ type: 'task'; id: number; name: string } | null>(null);
  const [newTask, setNewTask] = useState({ title: '', description: '', agent_id: undefined as number | undefined });
  const [assignAgentId, setAssignAgentId] = useState<number | undefined>(undefined);

  const fetchData = async () => {
    try {
      const [tasksData, agentsData] = await Promise.all([
        api.tasks.list(),
        api.agents.list(),
      ]);
      setTasks(tasksData);
      setAgents(agentsData);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleDragStart = (task: Task) => {
    setDraggedTask(task);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = async (status: string) => {
    if (!draggedTask) return;
    
    try {
      await api.tasks.update(draggedTask.id, { status, move_reason: 'Dragged to ' + status });
      fetchData();
    } catch (error) {
      console.error('Failed to update task:', error);
    }
    setDraggedTask(null);
  };

  const handleCreateTask = async () => {
    if (!newTask.title.trim()) {
      alert('Task title is required');
      return;
    }
    try {
      await api.tasks.create({
        title: newTask.title,
        description: newTask.description,
        agent_id: newTask.agent_id,
      });
      setNewTask({ title: '', description: '', agent_id: undefined });
      setShowCreateModal(false);
      fetchData();
    } catch (error) {
      console.error('Failed to create task:', error);
      alert('Failed to create task');
    }
  };

  const handleAssignTask = async () => {
    if (!selectedTask) return;
    try {
      await api.tasks.update(selectedTask.id, { agent_id: assignAgentId, move_reason: 'Assigned to agent' });
      setSelectedTask(null);
      setAssignAgentId(undefined);
      setShowAssignModal(false);
      fetchData();
    } catch (error) {
      console.error('Failed to assign task:', error);
    }
  };

  const handleDeleteTask = async (id: number) => {
    try {
      await api.tasks.delete(id);
      setDeleteConfirm(null);
      setSelectedTask(null);
      fetchData();
    } catch (error) {
      console.error('Failed to delete task:', error);
      alert('Failed to delete task');
    }
  };

  const openAssignModal = (task: Task) => {
    setSelectedTask(task);
    setAssignAgentId(task.agent_id || undefined);
    setShowAssignModal(true);
  };

  const openDeleteConfirm = (task: Task, e: React.MouseEvent) => {
    e.stopPropagation();
    setDeleteConfirm({ type: 'task', id: task.id, name: task.title });
  };

  const getTasksByStatus = (status: string) => tasks.filter(t => t.status === status);
  const getAgentName = (agentId: number | null) => {
    if (!agentId) return 'Unassigned';
    const agent = agents.find(a => a.id === agentId);
    return agent ? agent.name : 'Unknown';
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
          <h1 className="text-3xl font-bold gold-text">Kanban Board</h1>
          <p className="text-[#888] mt-1">{tasks.length} total tasks</p>
        </div>
        <button onClick={() => setShowCreateModal(true)} className="btn-gold">
          + New Task
        </button>
      </div>

      <div className="flex gap-4 flex-1 overflow-x-auto pb-4">
        {columns.map((column) => (
          <div
            key={column.id}
            className="kanban-column flex-1 min-w-[280px]"
            onDragOver={handleDragOver}
            onDrop={() => handleDrop(column.id)}
          >
            <div className="p-4 border-b border-[#333]">
              <div className="flex items-center justify-between">
                <h3 className="font-bold" style={{ color: column.color }}>{column.title}</h3>
                <span className="text-[#888] text-sm">{getTasksByStatus(column.id).length}</span>
              </div>
            </div>
            <div className="p-4 space-y-3">
              {getTasksByStatus(column.id).map((task) => (
                <div
                  key={task.id}
                  className="kanban-card cursor-move group"
                  draggable
                  onDragStart={() => handleDragStart(task)}
                  onClick={() => openAssignModal(task)}
                >
                  <div className="flex items-start justify-between">
                    <h4 className="font-medium mb-2 flex-1">{task.title}</h4>
                    <button
                      onClick={(e) => openDeleteConfirm(task, e)}
                      className="opacity-0 group-hover:opacity-100 text-red-500 hover:text-red-400 transition-opacity p-1"
                      title="Delete task"
                    >
                      🗑️
                    </button>
                  </div>
                  {task.description && (
                    <p className="text-sm text-[#888] mb-2 line-clamp-2">{task.description}</p>
                  )}
                  <div className="flex items-center justify-between text-xs">
                    <span className={`px-2 py-1 rounded ${
                      task.agent_id ? 'bg-[#FBC02D]/20 text-[#FBC02D]' : 'bg-[#333] text-[#888]'
                    }`}>
                      {getAgentName(task.agent_id)}
                    </span>
                    <span className="text-[#666]">P{task.priority}</span>
                  </div>
                  {task.move_reason && (
                    <p className="text-xs text-[#666] mt-2 italic">{task.move_reason}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {showCreateModal && (
        <div className="fixed inset-0 modal-overlay flex items-center justify-center z-50">
          <div className="card-cyber p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4 gold-text">Create New Task</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-[#888] mb-1">Title</label>
                <input
                  type="text"
                  value={newTask.title}
                  onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
                  className="input-cyber"
                  placeholder="Task title"
                />
              </div>
              <div>
                <label className="block text-sm text-[#888] mb-1">Description</label>
                <textarea
                  value={newTask.description}
                  onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
                  className="input-cyber min-h-[100px]"
                  placeholder="Task description"
                />
              </div>
              <div>
                <label className="block text-sm text-[#888] mb-1">Assign to Agent</label>
                <select
                  value={newTask.agent_id || ''}
                  onChange={(e) => setNewTask({ ...newTask, agent_id: e.target.value ? Number(e.target.value) : undefined })}
                  className="input-cyber"
                >
                  <option value="">Unassigned</option>
                  {agents.map((agent) => (
                    <option key={agent.id} value={agent.id}>{agent.name} ({agent.role})</option>
                  ))}
                </select>
              </div>
              <div className="flex gap-3">
                <button onClick={handleCreateTask} className="btn-gold flex-1">
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

      {showAssignModal && selectedTask && (
        <div className="fixed inset-0 modal-overlay flex items-center justify-center z-50">
          <div className="card-cyber p-6 w-full max-w-md">
            <div className="flex items-start justify-between mb-4">
              <h2 className="text-xl font-bold gold-text">Task Options</h2>
              <button 
                onClick={() => openDeleteConfirm(selectedTask, {} as React.MouseEvent)} 
                className="text-red-500 hover:text-red-400"
                title="Delete task"
              >
                🗑️
              </button>
            </div>
            <p className="text-[#888] mb-4">{selectedTask.title}</p>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-[#888] mb-1">Assign to Agent</label>
                <select
                  value={assignAgentId || ''}
                  onChange={(e) => setAssignAgentId(e.target.value ? Number(e.target.value) : undefined)}
                  className="input-cyber"
                >
                  <option value="">Unassigned</option>
                  {agents.map((agent) => (
                    <option key={agent.id} value={agent.id}>{agent.name} ({agent.role})</option>
                  ))}
                </select>
              </div>
              <div className="flex gap-3">
                <button onClick={handleAssignTask} className="btn-gold flex-1">
                  Save
                </button>
                <button onClick={() => { setShowAssignModal(false); setSelectedTask(null); }} className="btn-ghost flex-1">
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {deleteConfirm && (
        <div className="fixed inset-0 modal-overlay flex items-center justify-center z-50">
          <div className="card-cyber p-6 w-full max-w-md border-red-500/50">
            <h2 className="text-xl font-bold mb-4 text-red-500">Delete Task</h2>
            <p className="text-[#888] mb-4">
              Are you sure you want to delete <span className="text-white font-bold">{deleteConfirm.name}</span>?
            </p>
            <div className="flex gap-3">
              <button 
                onClick={() => handleDeleteTask(deleteConfirm.id)} 
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
