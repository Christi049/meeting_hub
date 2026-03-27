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

  const handleFilesUploaded = (uploadedFiles: File[]) => {
    const newFiles: UploadedFile[] = uploadedFiles.map((file) => ({
      id: Math.random().toString(36).substr(2, 9),
      name: file.name,
      size: file.size,
      type: file.type,
      uploadDate: new Date(),
      groupId: null,
    }));

    setFiles((prev) => [...prev, ...newFiles]);

    // Add bot message about uploaded files
    const botMessage: ChatMessage = {
      id: Math.random().toString(36).substr(2, 9),
      text: `I've received ${uploadedFiles.length} file${
        uploadedFiles.length > 1 ? "s" : ""
      }. ${
        uploadedFiles.length === 1
          ? `The file "${uploadedFiles[0].name}" has been uploaded successfully.`
          : "All files have been uploaded successfully."
      } You can organize them into groups if you'd like!`,
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

  const handleSendMessage = (text: string) => {
    // Add user message
    const userMessage: ChatMessage = {
      id: Math.random().toString(36).substr(2, 9),
      text,
      sender: "user",
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);

    // Generate bot response
    setTimeout(() => {
      let botResponse = "";
      const lowerText = text.toLowerCase();

      if (lowerText.includes("help") || lowerText.includes("what can you do")) {
        botResponse = "I can help you manage your files! You can:\n• Upload files by dragging and dropping\n• Create groups to organize your files\n• Move files between groups\n• Delete files or groups\n• Ask me questions about your file collection";
      } else if (lowerText.includes("how many") && lowerText.includes("file")) {
        botResponse = `You currently have ${files.length} file${
          files.length !== 1 ? "s" : ""
        } uploaded.`;
      } else if (lowerText.includes("group")) {
        botResponse = `You have ${groups.length} group${
          groups.length !== 1 ? "s" : ""
        }. ${
          groups.length > 0
            ? `Your groups are: ${groups.map((g) => g.name).join(", ")}.`
            : "You can create groups to organize your files!"
        }`;
      } else if (lowerText.includes("upload")) {
        botResponse =
          "To upload files, you can either drag and drop them into the upload area, or click on it to select files from your computer. I support multiple file uploads at once!";
      } else {
        botResponse =
          "I'm here to help you manage your files! You can upload files, create groups to organize them, and I'll keep track of everything. Is there anything specific you'd like to know?";
      }

      const botMessage: ChatMessage = {
        id: Math.random().toString(36).substr(2, 9),
        text: botResponse,
        sender: "bot",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, botMessage]);
    }, 500);
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
