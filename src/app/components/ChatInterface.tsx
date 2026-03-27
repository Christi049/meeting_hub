import { useState, useRef, useEffect } from "react";
import { Send, Bot, User } from "lucide-react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { ScrollArea } from "./ui/scroll-area";

export interface ChatMessage {
  id: string;
  text: string;
  sender: "user" | "bot";
  timestamp: Date;
}

interface ChatInterfaceProps {
  messages: ChatMessage[];
  onSendMessage: (message: string) => void;
}

export function ChatInterface({ messages, onSendMessage }: ChatInterfaceProps) {
  const [inputValue, setInputValue] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Scroll to bottom when new messages arrive
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim()) {
      onSendMessage(inputValue.trim());
      setInputValue("");
    }
  };

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="p-4 border-b flex items-center gap-3">
        <div className="size-10 rounded-full bg-blue-100 flex items-center justify-center">
          <Bot className="size-6 text-blue-600" />
        </div>
        <div>
          <h2 className="font-semibold">AI Assistant</h2>
          <p className="text-xs text-gray-500">Always here to help</p>
        </div>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center text-gray-500">
            <Bot className="size-12 mb-3 text-gray-300" />
            <p className="text-sm">Start a conversation</p>
            <p className="text-xs mt-1">Ask me anything about your files</p>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex gap-3 ${
                message.sender === "user" ? "flex-row-reverse" : ""
              }`}
            >
              <div
                className={`size-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                  message.sender === "user"
                    ? "bg-blue-600"
                    : "bg-gray-200"
                }`}
              >
                {message.sender === "user" ? (
                  <User className="size-4 text-white" />
                ) : (
                  <Bot className="size-4 text-gray-700" />
                )}
              </div>
              <div
                className={`flex flex-col ${
                  message.sender === "user" ? "items-end" : "items-start"
                } flex-1 max-w-[80%]`}
              >
                <div
                  className={`rounded-lg px-4 py-2 ${
                    message.sender === "user"
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 text-gray-900"
                  }`}
                >
                  <p className="text-sm whitespace-pre-wrap break-words">{message.text}</p>
                </div>
                <span className="text-xs text-gray-500 mt-1">
                  {message.timestamp.toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </span>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Input */}
      <div className="p-4 border-t">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Type your message..."
            className="flex-1"
          />
          <Button type="submit" size="icon" disabled={!inputValue.trim()}>
            <Send className="size-4" />
          </Button>
        </form>
      </div>
    </div>
  );
}
