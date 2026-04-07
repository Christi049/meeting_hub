import { useState } from "react";
import { FileUpload } from "./components/FileUpload";
import { FileManager, UploadedFile, FileGroup } from "./components/FileManager";
import { ChatInterface, ChatMessage } from "./components/ChatInterface";
import { AnalysisResults } from "./components/AnalysisResults";
import { Dashboard } from "./components/Dashboard";
import { LayoutDashboard, Upload } from "lucide-react";

const COLORS = [
  "#3B82F6",
  "#10B981",
  "#F59E0B",
  "#EF4444",
  "#8B5CF6",
  "#EC4899",
  "#06B6D4",
];

type View = "dashboard" | "workspace";

export default function App() {
  const API_BASE = "http://127.0.0.1:8001";
  const [view, setView] = useState<View>("workspace");
  const [dashboardKey, setDashboardKey] = useState(0);
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [groups, setGroups] = useState<FileGroup[]>([]);
  const [analysisResults, setAnalysisResults] = useState<any[]>([]);
  const [activeMeetingId, setActiveMeetingId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "1",
      text: "Hello! I'm your AI assistant. I can help you manage your files and answer any questions you have.",
      sender: "bot",
      timestamp: new Date(),
    },
  ]);

  const handleFilesUploaded = async (uploadedFiles: File[]) => {
    try {
      const formData = new FormData();
      uploadedFiles.forEach((file) => formData.append("files", file));

      const response = await fetch(`${API_BASE}/upload-transcripts`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Upload failed (${response.status}): ${errorText}`);
      }

      const uploadedResults = await response.json();
      setAnalysisResults((prev) => [...prev, ...uploadedResults]);

      const newFiles: UploadedFile[] = uploadedFiles.map((file, idx) => ({
        id: Math.random().toString(36).substr(2, 9),
        name: file.name,
        size: file.size,
        type: file.type,
        uploadDate: new Date(),
        groupId: null,
        meetingId: uploadedResults[idx]?.meeting_id ?? null,
      }));

      setFiles((prev) => [...prev, ...newFiles]);

      if (uploadedResults.length > 0) {
        setActiveMeetingId(uploadedResults[0].meeting_id);
      }

      setDashboardKey((k) => k + 1);

      const botMessage: ChatMessage = {
        id: Math.random().toString(36).substr(2, 9),
        text: `I've received ${uploadedFiles.length} file${uploadedFiles.length > 1 ? "s" : ""} and analyzed them. Check the analysis results below.`,
        sender: "bot",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error);
      const botMessage: ChatMessage = {
        id: Math.random().toString(36).substr(2, 9),
        text: `Upload failed: ${errorMsg}`,
        sender: "bot",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, botMessage]);
    }
  };

  const handleDeleteFile = (fileId: string) => {
    const file = files.find((f) => f.id === fileId);
    setFiles((prev) => prev.filter((f) => f.id !== fileId));
    if (file) {
      setMessages((prev) => [...prev, {
        id: Math.random().toString(36).substr(2, 9),
        text: `I've deleted "${file.name}" for you.`,
        sender: "bot",
        timestamp: new Date(),
      }]);
    }
  };

  const handleMoveToGroup = (fileId: string, groupId: string | null) => {
    const file = files.find((f) => f.id === fileId);
    const group = groupId ? groups.find((g) => g.id === groupId) : null;
    setFiles((prev) => prev.map((f) => (f.id === fileId ? { ...f, groupId } : f)));
    if (file) {
      setMessages((prev) => [...prev, {
        id: Math.random().toString(36).substr(2, 9),
        text: `I've moved "${file.name}" to ${group ? `the "${group.name}" group` : "ungrouped files"}.`,
        sender: "bot",
        timestamp: new Date(),
      }]);
    }
  };

  const handleCreateGroup = (name: string) => {
    const newGroup: FileGroup = {
      id: Math.random().toString(36).substr(2, 9),
      name,
      color: COLORS[groups.length % COLORS.length],
    };
    setGroups((prev) => [...prev, newGroup]);
    setMessages((prev) => [...prev, {
      id: Math.random().toString(36).substr(2, 9),
      text: `Great! I've created a new group called "${name}".`,
      sender: "bot",
      timestamp: new Date(),
    }]);
  };

  const handleDeleteGroup = (groupId: string) => {
    const group = groups.find((g) => g.id === groupId);
    const filesInGroup = files.filter((f) => f.groupId === groupId).length;
    setFiles((prev) => prev.map((f) => (f.groupId === groupId ? { ...f, groupId: null } : f)));
    setGroups((prev) => prev.filter((g) => g.id !== groupId));
    if (group) {
      setMessages((prev) => [...prev, {
        id: Math.random().toString(36).substr(2, 9),
        text: `I've deleted the "${group.name}" group.${filesInGroup > 0 ? ` ${filesInGroup} file(s) moved to ungrouped.` : ""}`,
        sender: "bot",
        timestamp: new Date(),
      }]);
    }
  };

  const handleSendMessage = async (text: string) => {
    const userMessage: ChatMessage = {
      id: Math.random().toString(36).substr(2, 9),
      text,
      sender: "user",
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);

    try {
      const queryBody: any = { question: text };
      if (activeMeetingId !== null) queryBody.meeting_id = activeMeetingId;

      const response = await fetch(`${API_BASE}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(queryBody),
      });

      if (!response.ok) throw new Error(`Query failed (${response.status})`);

      const data = await response.json();
      const citations = (data.citations || [])
        .slice(0, 5)
        .map((c: { meeting?: string; section?: string }) => `- ${c.meeting || "Meeting"} (${c.section || "chunk"})`)
        .join("\n");
      const botResponse = citations ? `${data.answer}\n\nSources:\n${citations}` : data.answer;

      setMessages((prev) => [...prev, {
        id: Math.random().toString(36).substr(2, 9),
        text: botResponse || "No answer generated.",
        sender: "bot",
        timestamp: new Date(),
      }]);
    } catch (error) {
      setMessages((prev) => [...prev, {
        id: Math.random().toString(36).substr(2, 9),
        text: `Query failed: ${error instanceof Error ? error.message : "unknown error"}`,
        sender: "bot",
        timestamp: new Date(),
      }]);
    }
  };

  const handleSelectMeeting = (id: number) => {
    setActiveMeetingId(id);
    setView("workspace");
  };

  // Convert analysisResults to Meeting format for dashboard
  const dashboardMeetings = analysisResults.map((result: any) => {
    // Calculate overall sentiment from segments
    let overallSentiment: "positive" | "negative" | "neutral" = "neutral";
    let sentimentScore = 0;

    if (result.segments && result.segments.length > 0) {
      const avgScore = result.segments.reduce((sum: number, s: any) => sum + (s.sentiment_score || 0), 0) / result.segments.length;
      sentimentScore = avgScore;

      if (avgScore > 0) overallSentiment = "positive";
      else if (avgScore < 0) overallSentiment = "negative";
      else overallSentiment = "neutral";
    }

    return {
      id: result.meeting_id,
      file_name: result.file_name,
      title: result.title,
      date: result.date,
      num_speakers: result.speakers,
      word_count: result.word_count,
      summary: result.abstractive_summary,
      created_at: new Date().toISOString(),
      decision_count: result.decisions?.length || 0,
      action_count: result.action_items?.length || 0,
      overall_sentiment: overallSentiment,
      sentiment_score: sentimentScore,
    };
  });

  return (
    <div className="size-full flex flex-col h-screen bg-gray-100">
      {/* Top nav */}
      <nav className="bg-white border-b px-4 py-2 flex items-center gap-2 shrink-0">
        <span className="font-bold text-gray-900 mr-4">Meeting Hub</span>
        <button
          onClick={() => setView("dashboard")}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-colors ${
            view === "dashboard"
              ? "bg-blue-50 text-blue-700 font-medium"
              : "text-gray-600 hover:bg-gray-100"
          }`}
        >
          <LayoutDashboard className="w-4 h-4" />
          Dashboard
        </button>
        <button
          onClick={() => setView("workspace")}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition-colors ${
            view === "workspace"
              ? "bg-blue-50 text-blue-700 font-medium"
              : "text-gray-600 hover:bg-gray-100"
          }`}
        >
          <Upload className="w-4 h-4" />
          Workspace
        </button>
      </nav>

      {/* Dashboard view */}
      {view === "dashboard" && (
        <div className="flex-1 overflow-y-auto">
          <Dashboard
            key={dashboardKey}
            meetings={dashboardMeetings}
            onSelectMeeting={handleSelectMeeting}
          />
        </div>
      )}

      {/* Workspace view */}
      {view === "workspace" && (
        <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
          {/* Left Panel */}
          <div className="w-full md:w-1/2 flex flex-col border-r bg-white overflow-y-auto">
            <div className="p-4 border-b sticky top-0 bg-white z-10">
              <h1 className="text-xl font-bold mb-4">File Manager</h1>
              <FileUpload onFilesUploaded={handleFilesUploaded} />
            </div>

            {analysisResults.length > 0 && (
              <div className="p-4 border-b bg-gray-50">
                <h2 className="text-lg font-bold mb-4">Analysis Results</h2>
                <div className="space-y-4">
                  {analysisResults.map((result, idx) => (
                    <AnalysisResults key={idx} data={result} />
                  ))}
                </div>
              </div>
            )}

            <div className="flex-1 overflow-hidden">
              <FileManager
                files={files}
                groups={groups}
                onDeleteFile={handleDeleteFile}
                onMoveToGroup={handleMoveToGroup}
                onCreateGroup={handleCreateGroup}
                onDeleteGroup={handleDeleteGroup}
              />
            </div>
          </div>

          {/* Right Panel */}
          <div className="w-full md:w-1/2 flex flex-col overflow-hidden">
            <ChatInterface messages={messages} onSendMessage={handleSendMessage} />
          </div>
        </div>
      )}
    </div>
  );
}