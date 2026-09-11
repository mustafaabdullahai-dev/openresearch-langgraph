import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { sendChat } from "../services/api";

interface Props {
  threadId: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
}

export function ChatPanel({ threadId }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    const msg = input.trim();
    if (!msg || loading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: msg }]);
    setLoading(true);
    setError(null);

    try {
      const res = await sendChat(threadId, msg);
      setMessages((prev) => [...prev, { role: "assistant", content: res.response }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-900">
      <h3 className="mb-4 text-sm font-semibold text-gray-700 dark:text-gray-200">
        Follow-up Questions
      </h3>

      {messages.length > 0 && (
        <div className="mb-4 space-y-3">
          {messages.map((msg, i) => (
            <div
              key={`${msg.role}-${i}`}
              className={`rounded-lg p-3 text-sm ${
                msg.role === "user"
                  ? "ml-8 bg-brand-50 text-brand-800 dark:bg-brand-700/10 dark:text-brand-200"
                  : "mr-8 bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-200"
              }`}
            >
              {msg.role === "assistant" ? (
                <article className="prose prose-sm max-w-none dark:prose-invert prose-p:text-inherit">
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </article>
              ) : (
                msg.content
              )}
            </div>
          ))}
        </div>
      )}

      <form onSubmit={handleSend} className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a follow-up..."
          disabled={loading}
          className="flex-1 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100"
        />
        <button
          type="submit"
          disabled={loading || input.trim().length === 0}
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "..." : "Send"}
        </button>
      </form>

      {error && (
        <p className="mt-2 text-xs text-red-600 dark:text-red-400">{error}</p>
      )}
    </section>
  );
}
