"use client";

import { useState, useEffect, useRef } from "react";
import { api, Agent, ChatMessage } from "@/lib/api";

export default function ChatPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [newMessage, setNewMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadAgents();
  }, []);

  useEffect(() => {
    if (selectedAgent) {
      loadMessages(selectedAgent.id, true);
      const interval = setInterval(() => loadMessages(selectedAgent.id, false), 3000);
      return () => clearInterval(interval);
    }
  }, [selectedAgent]);

  useEffect(() => {
    // Disabled auto-scrolling - user can scroll manually
    // messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const loadAgents = async () => {
    try {
      const data = await api.agents.list();
      setAgents(data);
    } catch (err) {
      console.error("Failed to fetch agents:", err);
    }
  };

  const loadMessages = async (agentId: number, sync: boolean = false) => {
    try {
      setIsLoading(true);
      const data = await api.chat.messages(agentId, sync);
      setMessages(data);
    } catch (err) {
      console.error("Failed to fetch messages:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAgent || !newMessage.trim() || isSending) return;

    setIsSending(true);
    const messageToSend = newMessage;
    setNewMessage("");

    try {
      const data = await api.chat.send(selectedAgent.id, messageToSend);
      setMessages((prev) => [...prev, data]);
    } catch (err) {
      console.error("Failed to send message:", err);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="flex h-[calc(100vh-4rem)]">
      <div className="w-80 border-r border-gray-800 bg-gray-900/50">
        <div className="p-4 border-b border-gray-800">
          <h2 className="text-lg font-semibold text-gold-400">Agents</h2>
        </div>
        <div className="overflow-y-auto h-full">
          {agents.length === 0 ? (
            <div className="p-4 text-gray-500 text-sm">No agents created yet</div>
          ) : (
            agents.map((agent) => (
              <button
                key={agent.id}
                onClick={() => setSelectedAgent(agent)}
                className={`w-full p-4 text-left border-b border-gray-800 transition-colors ${
                  selectedAgent?.id === agent.id
                    ? "bg-gold-500/10 border-l-2 border-l-gold-500"
                    : "hover:bg-gray-800/50"
                }`}
              >
                <div className="font-medium text-gray-200">{agent.name}</div>
                <div className="text-sm text-gray-500">{agent.role}</div>
                <div className="flex items-center gap-2 mt-1">
                  <span
                    className={`w-2 h-2 rounded-full ${
                      agent.status === "active"
                        ? "bg-green-500"
                        : agent.status === "overheated"
                        ? "bg-red-500"
                        : "bg-gray-500"
                    }`}
                  />
                  <span className="text-xs text-gray-600">{agent.status}</span>
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      <div className="flex-1 flex flex-col">
        {selectedAgent ? (
          <>
            <div className="p-4 border-b border-gray-800 bg-gray-900/50">
              <h2 className="text-xl font-semibold text-gold-400">
                Chat with {selectedAgent.name}
              </h2>
              <p className="text-sm text-gray-500">{selectedAgent.role}</p>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {isLoading && messages.length === 0 && (
                <div className="text-center text-gray-500 mt-8">
                  <p>Loading messages...</p>
                </div>
              )}
              {messages.length === 0 && !isLoading && (
                <div className="text-center text-gray-500 mt-8">
                  <p>No messages yet. Start the conversation!</p>
                </div>
              )}
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex ${
                    msg.is_from_user ? "justify-end" : "justify-start"
                  }`}
                >
                  <div
                    className={`max-w-[70%] rounded-lg p-3 ${
                      msg.is_from_user
                        ? "bg-gold-600 text-black"
                        : msg.sender === "system"
                        ? "bg-purple-600/30 text-purple-200 border border-purple-500/30"
                        : "bg-gray-800 text-gray-200"
                    }`}
                  >
                    {msg.sender !== "user" && msg.sender !== "system" && (
                      <div className="text-xs text-gray-400 mb-1">{msg.sender}</div>
                    )}
                    {msg.sender === "system" && (
                      <div className="text-xs text-purple-400 mb-1">System</div>
                    )}
                    <div className="whitespace-pre-wrap">{msg.content}</div>
                    <div className="text-xs text-gray-400 mt-1">
                      {new Date(msg.created_at).toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>

            <form onSubmit={sendMessage} className="p-4 border-t border-gray-800">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  placeholder="Type your message..."
                  disabled={isSending}
                  className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-gray-200 placeholder-gray-500 focus:outline-none focus:border-gold-500 disabled:opacity-50"
                />
                <button
                  type="submit"
                  disabled={!newMessage.trim() || isSending}
                  className="px-6 py-2 bg-gold-600 hover:bg-gold-500 disabled:bg-gray-700 disabled:text-gray-500 text-black font-medium rounded-lg transition-colors"
                >
                  {isSending ? "Sending..." : "Send"}
                </button>
              </div>
            </form>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-gray-500">
            <div className="text-center">
              <svg
                className="w-16 h-16 mx-auto mb-4 text-gray-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                />
              </svg>
              <p>Select an agent to start chatting</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
