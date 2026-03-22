'use client';

import { useEffect, useState } from 'react';
import { api, Meeting } from '@/lib/api';

export default function StandupPage() {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [selectedMeeting, setSelectedMeeting] = useState<Meeting | null>(null);

  const fetchMeetings = async () => {
    try {
      const data = await api.meetings.list('standup');
      setMeetings(data);
    } catch (error) {
      console.error('Failed to fetch meetings:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMeetings();
  }, []);

  const handleRunStandup = async () => {
    setRunning(true);
    try {
      await api.meetings.runStandup();
      fetchMeetings();
    } catch (error) {
      console.error('Failed to run standup:', error);
    } finally {
      setRunning(false);
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
          <h1 className="text-3xl font-bold gold-text">Executive Standup</h1>
          <p className="text-[#888] mt-1">Daily sync meetings and briefings</p>
        </div>
        <button onClick={handleRunStandup} disabled={running} className="btn-gold">
          {running ? 'Running...' : '🎙️ Run Daily Standup'}
        </button>
      </div>

      <div className="flex-1 overflow-auto scrollbar-thin">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div>
            <h2 className="text-xl font-bold mb-4">Meeting Archive</h2>
            <div className="space-y-3">
              {meetings.map((meeting) => (
                <div
                  key={meeting.id}
                  className="card-cyber p-4 cursor-pointer hover:border-[#FBC02D]"
                  onClick={() => setSelectedMeeting(meeting)}
                >
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-medium">{meeting.title}</h3>
                    <span className="text-sm text-[#888]">
                      {new Date(meeting.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  {meeting.briefing && (
                    <p className="text-sm text-[#888] line-clamp-2">{meeting.briefing}</p>
                  )}
                </div>
              ))}
              {meetings.length === 0 && (
                <p className="text-[#888] text-center py-8">No standups yet. Run one to get started!</p>
              )}
            </div>
          </div>

          <div>
            <h2 className="text-xl font-bold mb-4">Meeting Details</h2>
            {selectedMeeting ? (
              <div className="card-cyber p-6">
                <h3 className="font-bold text-lg mb-4 gold-text">{selectedMeeting.title}</h3>
                <div className="mb-4">
                  <h4 className="font-medium mb-2">Briefing:</h4>
                  <p className="text-[#888] whitespace-pre-wrap">{selectedMeeting.briefing || 'No briefing available'}</p>
                </div>
                {selectedMeeting.transcript && (
                  <div>
                    <h4 className="font-medium mb-2">Full Transcript:</h4>
                    <div className="bg-[#0d0d0d] p-4 rounded-lg max-h-[400px] overflow-auto scrollbar-thin">
                      <pre className="text-sm whitespace-pre-wrap">{selectedMeeting.transcript}</pre>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="card-cyber p-8 text-center">
                <p className="text-[#888]">Select a meeting to view details</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
