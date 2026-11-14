/**
 * WorkConnect Modern ChatGPT-like Chatbot Component (React / Next.js)
 * Features:
 * 1. Streaming Responses via fetch ReadableStream / SSE
 * 2. Clickable Suggested Prompts pills
 * 3. Markdown rendering support
 * 4. Clear chat history reset button
 * 5. Thumbs Up / Down feedback buttons
 */

import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';

export default function WorkConnectChatbot() {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hello! I am your WorkConnect Assistant. How can I help you find work or hire today?' }
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef(null);

  const suggestedPrompts = [
    "How does matching work?",
    "What is the minimum wage?",
    "Find me a job"
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isStreaming]);

  // 1. Streaming Response Handler (ReadableStream / SSE)
  const handleSendMessage = async (textToSend) => {
    const query = textToSend || inputQuery;
    if (!query.trim() || isStreaming) return;

    const userMessage = { role: 'user', content: query };
    setMessages(prev => [...prev, userMessage]);
    setInputQuery('');
    setIsStreaming(true);

    // Add empty assistant bubble for streaming
    setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

    try {
      const response = await fetch('/api/ai/stream-chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: query })
      });

      if (!response.body) throw new Error("ReadableStream not supported");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let accumulatedReply = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        accumulatedReply += chunk;

        setMessages(prev => {
          const updated = [...prev];
          updated[updated.length - 1] = { role: 'assistant', content: accumulatedReply };
          return updated;
        });
      }
    } catch (error) {
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = { role: 'assistant', content: "⚠️ Connection error or service busy. Please try again." };
        return updated;
      });
    } finally {
      setIsStreaming(false);
    }
  };

  // 4. Clear Chat / Reset
  const handleClearChat = () => {
    setMessages([
      { role: 'assistant', content: 'Chat history cleared. How can I help you today?' }
    ]);
  };

  return (
    <div className="flex flex-col h-[600px] w-full max-w-lg bg-white rounded-2xl shadow-2xl border border-gray-200 overflow-hidden font-sans">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-blue-600 text-white font-bold text-base shadow-md">
        <div className="flex items-center gap-2">
          <span>🤖 WorkConnect Smart Assistant</span>
        </div>
        <button
          onClick={handleClearChat}
          className="text-xs bg-blue-700 hover:bg-blue-800 px-2.5 py-1 rounded-lg transition"
          title="Clear Chat"
        >
          🗑️ Clear Chat
        </button>
      </div>

      {/* Messages List */}
      <div className="flex-1 p-4 overflow-y-auto space-y-4 bg-gray-50">
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
          >
            <div
              className={`max-w-[85%] px-4 py-3 rounded-2xl text-sm leading-relaxed shadow-sm ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white rounded-br-none'
                  : 'bg-white text-gray-900 border border-gray-200 rounded-bl-none'
              }`}
            >
              {/* 3. Markdown Rendering */}
              <ReactMarkdown>{msg.content}</ReactMarkdown>
            </div>

            {/* 5. Thumbs Up / Down Feedback under assistant messages */}
            {msg.role === 'assistant' && msg.content && (
              <div className="flex items-center gap-2 mt-1 ml-1 text-xs text-gray-400">
                <button
                  onClick={() => alert("Thank you for your feedback!")}
                  className="hover:text-blue-600 transition"
                  title="Helpful"
                >
                  👍
                </button>
                <button
                  onClick={() => alert("Thank you for your feedback!")}
                  className="hover:text-red-600 transition"
                  title="Not helpful"
                >
                  👎
                </button>
              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* 2. Suggested Prompts Pill Buttons */}
      <div className="px-4 py-2 bg-white border-t border-gray-100 flex gap-2 overflow-x-auto">
        {suggestedPrompts.map((prompt, idx) => (
          <button
            key={idx}
            onClick={() => handleSendMessage(prompt)}
            className="text-xs bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-semibold px-3 py-1.5 rounded-full whitespace-nowrap border border-indigo-200 transition shadow-sm"
          >
            {prompt}
          </button>
        ))}
      </div>

      {/* Input Bar */}
      <div className="p-3 bg-white border-t border-gray-200 flex items-center gap-2">
        <input
          type="text"
          value={inputQuery}
          onChange={(e) => setInputQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
          placeholder="Ask in English, Telugu, or Hindi..."
          disabled={isStreaming}
          className="flex-1 px-4 py-2.5 text-sm border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
        />
        <button
          onClick={() => handleSendMessage()}
          disabled={isStreaming || !inputQuery.trim()}
          className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-4 py-2.5 rounded-xl font-bold text-sm transition shadow-md"
        >
          Send
        </button>
      </div>
    </div>
  );
}
