import { useState } from "react";
import { FileUpload } from "./components/FileUpload";
import { FileManager, UploadedFile, FileGroup } from "./components/FileManager";
import { ChatInterface, ChatMessage } from "./components/ChatInterface";

const COLORS = [
  "#3B82F6", // blue
  "#10B981", // green
  "#F59E0B", // amber
  "#EF4444", // red
  "#8B5CF6", // violet
  "#EC4899", // pink
  "#06B6D4", // cyan
];

export default function App() {
  const API_BASE = "http://127.0.0.1:8000";
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [groups, setGroups] = useState<FileGroup[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "1",
      text: "Hello! I'm your AI assistant. I can help you manage your files and answer any questions you have.",
      sender: "bot",
      timestamp: new Date(),
    },
  ]);

  const handleFilesUploaded = async (uploadedFiles: File[]) => {
    const formData = new FormData();
    uploadedFiles.forEach((file) => formData.append("files", file));

    const response = await fetch(`${API_BASE}/upload-transcripts`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      throw new Error(`Upload failed (${response.status})`);
    }
    const uploadedResults = await response.json();

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

    // Add bot message about uploaded files
    const botMessage: ChatMessage = {
      id: Math.random().toString(36).substr(2, 9),
      text: `I've received ${uploadedFiles.length} file${
        uploadedFiles.length > 1 ? "s" : ""
      } and indexed them for semantic search. ${
        uploadedFiles.length === 1
          ? `The file "${uploadedFiles[0].name}" has been uploaded successfully.`
          : "All files have been uploaded successfully."
      } You can now ask cross-meeting questions with citations.`,
      sender: "bot",
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, botMessage]);
  };

  const handleDeleteFile = (fileId: string) => {
    const file = files.find((f) => f.id === fileId);
    setFiles((prev) => prev.filter((f) => f.id !== fileId));

    if (file) {
      const botMessage: ChatMessage = {
        id: Math.random().toString(36).substr(2, 9),
        text: `I've deleted "${file.name}" for you.`,
        sender: "bot",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, botMessage]);
    }
  };

  const handleMoveToGroup = (fileId: string, groupId: string | null) => {
    const file = files.find((f) => f.id === fileId);
    const group = groupId ? groups.find((g) => g.id === groupId) : null;

    setFiles((prev) =>
      prev.map((f) => (f.id === fileId ? { ...f, groupId } : f))
    );

    if (file) {
      const botMessage: ChatMessage = {
        id: Math.random().toString(36).substr(2, 9),
        text: `I've moved "${file.name}" to ${
          group ? `the "${group.name}" group` : "ungrouped files"
        }.`,
        sender: "bot",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, botMessage]);
    }
  };

  const handleCreateGroup = (name: string) => {
    const newGroup: FileGroup = {
      id: Math.random().toString(36).substr(2, 9),
      name,
      color: COLORS[groups.length % COLORS.length],
    };
    setGroups((prev) => [...prev, newGroup]);

    const botMessage: ChatMessage = {
      id: Math.random().toString(36).substr(2, 9),
      text: `Great! I've created a new group called "${name}". You can now organize your files into this group.`,
      sender: "bot",
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, botMessage]);
  };

  const handleDeleteGroup = (groupId: string) => {
    const group = groups.find((g) => g.id === groupId);
    // Move all files in this group to ungrouped
    setFiles((prev) =>
      prev.map((f) => (f.groupId === groupId ? { ...f, groupId: null } : f))
    );
    setGroups((prev) => prev.filter((g) => g.id !== groupId));

    if (group) {
      const filesInGroup = files.filter((f) => f.groupId === groupId).length;
      const botMessage: ChatMessage = {
        id: Math.random().toString(36).substr(2, 9),
        text: `I've deleted the "${group.name}" group. ${
          filesInGroup > 0
            ? `The ${filesInGroup} file${
                filesInGroup > 1 ? "s" : ""
              } in this group have been moved to ungrouped.`
            : ""
        }`,
        sender: "bot",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, botMessage]);
    }
  };

  const handleSendMessage = async (text: string) => {
    // Add user message
    const userMessage: ChatMessage = {
      id: Math.random().toString(36).substr(2, 9),
      text,
      sender: "user",
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);

    try {
      const response = await fetch(`${API_BASE}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: text }),
      });
      if (!response.ok) {
        throw new Error(`Query failed (${response.status})`);
      }
      const data = await response.json();
      const citations = (data.citations || [])
        .slice(0, 5)
        .map((c: { meeting?: string; section?: string }) => `- ${c.meeting || "Meeting"} (${c.section || "chunk"})`)
        .join("\n");
      const botResponse = citations
        ? `${data.answer}\n\nSources:\n${citations}`
        : data.answer;
      const botMessage: ChatMessage = {
        id: Math.random().toString(36).substr(2, 9),
        text: botResponse || "No answer generated.",
        sender: "bot",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      const botMessage: ChatMessage = {
        id: Math.random().toString(36).substr(2, 9),
        text: `Query failed: ${error instanceof Error ? error.message : "unknown error"}`,
        sender: "bot",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, botMessage]);
    }
  };

  return (
    <div className="size-full flex flex-col md:flex-row bg-gray-100">
      {/* Left Panel - File Management */}
      <div className="w-full md:w-1/2 flex flex-col border-r bg-white">
        {/* Upload Section */}
        <div className="p-4 border-b">
          <h1 className="text-xl font-bold mb-4">File Manager</h1>
          <FileUpload onFilesUploaded={handleFilesUploaded} />
        </div>

        {/* File Manager */}
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

      {/* Right Panel - Chat Interface */}
      <div className="w-full md:w-1/2 flex flex-col">
        <ChatInterface messages={messages} onSendMessage={handleSendMessage} />
      </div>
    </div>
  );
}
