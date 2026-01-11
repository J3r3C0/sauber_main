import { useState } from "react";
import { MessageSquare, Send, Bot, User } from "lucide-react";
import { mockConversations } from "../../data/mockData";
import type { ChatMessage } from "../../types";

const sampleMessages: ChatMessage[] = [
  {
    id: "msg1",
    role: "user",
    content: "Let's review the mesh discovery protocol implementation",
    timestamp: "2025-12-11T14:10:00Z",
  },
  {
    id: "msg2",
    role: "assistant",
    content: "I'll analyze the current mesh protocol. The UDP broadcast on port 9001 handles node discovery, while TCP connections on dynamic ports handle data transfer. Should we optimize the discovery interval?",
    timestamp: "2025-12-11T14:10:15Z",
  },
  {
    id: "msg3",
    role: "user",
    content: "Yes, what's the current interval and what would you recommend?",
    timestamp: "2025-12-11T14:11:00Z",
  },
  {
    id: "msg4",
    role: "assistant",
    content: "Current interval is 5 seconds. For a local dev environment, I'd recommend 10-15 seconds to reduce network chatter. For production mesh with dynamic nodes, keep it at 5 seconds or even reduce to 3 seconds for faster convergence.",
    timestamp: "2025-12-11T14:11:20Z",
  },
];

export function ChatTab() {
  const [selectedConversation, setSelectedConversation] = useState(mockConversations[0]);
  const [messages] = useState<ChatMessage[]>(sampleMessages);
  const [input, setInput] = useState("");

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-xl">Prompt / Chat</h1>
        <p className="text-sm text-slate-400 mt-1">
          Kontextbezogene Chat-Sessions pro Projekt mit Agent- und System-Prompts.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 h-[calc(100vh-220px)]">
        {/* Conversation List */}
        <div className="lg:col-span-1 bg-sheratan-card border border-slate-700 rounded-lg overflow-hidden flex flex-col">
          <div className="px-4 py-3 border-b border-slate-700">
            <h3 className="text-sm">Conversations</h3>
            <p className="text-xs text-slate-400 mt-0.5">{mockConversations.length} active</p>
          </div>
          <div className="flex-1 overflow-y-auto divide-y divide-slate-800">
            {mockConversations.map((conv) => (
              <button
                key={conv.id}
                onClick={() => setSelectedConversation(conv)}
                className={`w-full text-left px-4 py-3 hover:bg-slate-900/40 transition ${
                  selectedConversation.id === conv.id ? "bg-sheratan-accent/5 border-l-2 border-sheratan-accent" : ""
                }`}
              >
                <div className="flex items-start gap-2 mb-1">
                  <MessageSquare className="w-4 h-4 text-slate-400 flex-shrink-0 mt-0.5" />
                  <span className="text-sm text-slate-200 line-clamp-1">{conv.name}</span>
                </div>
                <p className="text-xs text-slate-400 line-clamp-2 ml-6">{conv.lastMessage}</p>
                <div className="flex items-center gap-2 mt-2 ml-6 text-xs text-slate-500">
                  <span>{conv.messageCount} msgs</span>
                  {conv.projectId && (
                    <>
                      <span>•</span>
                      <span className="text-sheratan-accent">{conv.projectId}</span>
                    </>
                  )}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Chat Window */}
        <div className="lg:col-span-3 bg-sheratan-card border border-slate-700 rounded-lg flex flex-col">
          <div className="px-4 py-3 border-b border-slate-700">
            <h3 className="text-sm">{selectedConversation.name}</h3>
            {selectedConversation.projectId && (
              <p className="text-xs text-slate-400 mt-0.5">Project: {selectedConversation.projectId}</p>
            )}
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {msg.role === "assistant" && (
                  <div className="w-8 h-8 rounded-full bg-sheratan-accent/10 border border-sheratan-accent/40 flex items-center justify-center flex-shrink-0">
                    <Bot className="w-4 h-4 text-sheratan-accent" />
                  </div>
                )}
                <div
                  className={`max-w-[70%] rounded-lg p-3 ${
                    msg.role === "user"
                      ? "bg-sheratan-accent/10 border border-sheratan-accent/30"
                      : "bg-slate-800/50 border border-slate-700"
                  }`}
                >
                  <p className="text-sm text-slate-100">{msg.content}</p>
                  <span className="text-xs text-slate-500 mt-1 block">
                    {new Date(msg.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                {msg.role === "user" && (
                  <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center flex-shrink-0">
                    <User className="w-4 h-4 text-slate-300" />
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Input */}
          <div className="p-4 border-t border-slate-700">
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Type your message..."
                className="flex-1 bg-slate-800/50 border border-slate-700 rounded-lg px-4 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-sheratan-accent/40"
              />
              <button className="bg-sheratan-accent/10 border border-sheratan-accent/40 text-sheratan-accent rounded-lg px-4 py-2 hover:bg-sheratan-accent/20 transition flex items-center gap-2">
                <Send className="w-4 h-4" />
                <span className="text-sm">Send</span>
              </button>
            </div>
            <p className="text-xs text-slate-500 mt-2">
              Context: System prompt + {selectedConversation.projectId || "General"}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
