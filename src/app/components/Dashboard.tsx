import { useState } from "react";
import { FileText, Users, CheckSquare, ListTodo, TrendingUp, TrendingDown, Minus } from "lucide-react";

interface Meeting {
  id: number;
  file_name: string;
  title: string;
  date: string;
  num_speakers: number;
  word_count: number;
  summary: string;
  created_at: string;
  decision_count: number;
  action_count: number;
  overall_sentiment: "positive" | "negative" | "neutral";
  sentiment_score: number;
}

interface DashboardProps {
  meetings: Meeting[];
  onSelectMeeting: (id: number) => void;
}

function SentimentBadge({ sentiment }: { sentiment: string }) {
  if (sentiment === "positive") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
        <TrendingUp className="w-3 h-3" /> Positive
      </span>
    );
  }
  if (sentiment === "negative") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
        <TrendingDown className="w-3 h-3" /> Negative
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
      <Minus className="w-3 h-3" /> Neutral
    </span>
  );
}

function StatCard({ label, value, icon }: { label: string; value: number | string; icon: React.ReactNode }) {
  return (
    <div className="bg-white rounded-xl border p-4 flex items-center gap-4">
      <div className="p-2 bg-blue-50 rounded-lg text-blue-600">
        {icon}
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
        <p className="text-xs text-gray-500">{label}</p>
      </div>
    </div>
  );
}

export function Dashboard({ meetings, onSelectMeeting }: DashboardProps) {

  const totalDecisions = meetings.reduce((s, m) => s + m.decision_count, 0);
  const totalActions = meetings.reduce((s, m) => s + m.action_count, 0);
  const totalSpeakers = meetings.reduce((s, m) => s + m.num_speakers, 0);

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Meeting Intelligence Hub</h1>
          <p className="text-sm text-gray-500 mt-1">Current session ({meetings.length} uploaded)</p>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total meetings" value={meetings.length} icon={<FileText className="w-5 h-5" />} />
        <StatCard label="Total speakers" value={totalSpeakers} icon={<Users className="w-5 h-5" />} />
        <StatCard label="Decisions made" value={totalDecisions} icon={<CheckSquare className="w-5 h-5" />} />
        <StatCard label="Action items" value={totalActions} icon={<ListTodo className="w-5 h-5" />} />
      </div>

      {/* Meeting list */}
      {meetings.length === 0 && (
        <div className="text-center py-16 text-gray-400">
          <FileText className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p className="text-sm">No meetings uploaded yet.</p>
          <p className="text-xs mt-1">Go to the Upload tab to get started.</p>
        </div>
      )}

      {meetings.length > 0 && (
        <div className="space-y-3">
          {meetings.map((meeting) => (
            <div
              key={meeting.id}
              onClick={() => onSelectMeeting(meeting.id)}
              className="bg-white border rounded-xl p-5 hover:border-blue-300 hover:shadow-sm transition-all cursor-pointer"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="font-semibold text-gray-900 truncate">{meeting.title}</h3>
                    <SentimentBadge sentiment={meeting.overall_sentiment} />
                  </div>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {meeting.date !== "Unknown" ? meeting.date : "Date unknown"} · {meeting.file_name}
                  </p>
                  {meeting.summary && (
                    <p className="text-sm text-gray-600 mt-2 line-clamp-2">{meeting.summary}</p>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-4 mt-4 pt-3 border-t text-xs text-gray-500">
                <span className="flex items-center gap-1">
                  <Users className="w-3.5 h-3.5" />
                  {meeting.num_speakers} speaker{meeting.num_speakers !== 1 ? "s" : ""}
                </span>
                <span className="flex items-center gap-1">
                  <FileText className="w-3.5 h-3.5" />
                  {meeting.word_count.toLocaleString()} words
                </span>
                <span className="flex items-center gap-1">
                  <CheckSquare className="w-3.5 h-3.5" />
                  {meeting.decision_count} decision{meeting.decision_count !== 1 ? "s" : ""}
                </span>
                <span className="flex items-center gap-1">
                  <ListTodo className="w-3.5 h-3.5" />
                  {meeting.action_count} action{meeting.action_count !== 1 ? "s" : ""}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}