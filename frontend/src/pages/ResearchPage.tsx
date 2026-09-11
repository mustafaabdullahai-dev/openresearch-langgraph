import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ChatPanel } from "../components/ChatPanel";
import { GraphVisual } from "../components/GraphVisual";
import { ProgressTimeline } from "../components/ProgressTimeline";
import { ReportView } from "../components/ReportView";
import { ResearchForm } from "../components/ResearchForm";
import { getResearchResult, startResearch, streamResearch } from "../services/api";
import type {
  ProgressEvent,
  ResearchResult,
  ResearchStatus,
} from "../types";

export function ResearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [status, setStatus] = useState<ResearchStatus>("idle");
  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [question, setQuestion] = useState("");
  const [threadId, setThreadId] = useState("");
  const [result, setResult] = useState<ResearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showChat, setShowChat] = useState(false);
  const esRef = useRef<EventSource | null>(null);

  const loadExisting = useCallback(async (id: string) => {
    try {
      setStatus("loading-result");
      setThreadId(id);
      const res = await getResearchResult(id);
      setResult(res);
      setQuestion(res.question);
      setStatus("done");
    } catch (err) {
      setStatus("error");
      setError(
        err instanceof Error ? err.message : "Failed to load session",
      );
    }
  }, []);

  useEffect(() => {
    const loaded = searchParams.get("thread");
    if (loaded) {
      void loadExisting(loaded);
    }
  }, [searchParams, loadExisting]);

  useEffect(() => {
    return () => esRef.current?.close();
  }, []);

  const handleStart = async (q: string) => {
    setStatus("starting");
    setError(null);
    setResult(null);
    setEvents([]);
    setQuestion(q);
    setShowChat(false);
    setSearchParams({}, { replace: true });

    try {
      const { thread_id } = await startResearch(q);
      setThreadId(thread_id);
      setStatus("streaming");
      esRef.current = streamResearch(
        thread_id,
        (ev) => setEvents((prev) => [...prev, ev]),
        () => setStatus("loading-result"),
        () =>
          setError("Stream connection closed unexpectedly."),
      );
    } catch (err) {
      setStatus("error");
      setError(
        err instanceof Error ? err.message : "Failed to start research",
      );
    }
  };

  useEffect(() => {
    if (status !== "loading-result" || !threadId) return;
    let cancelled = false;
    getResearchResult(threadId)
      .then((res) => {
        if (cancelled) return;
        setResult(res);
        setStatus("done");
      })
      .catch((err) => {
        if (cancelled) return;
        setStatus("error");
        setError(
          err instanceof Error ? err.message : "Failed to load result",
        );
      });
    return () => {
      cancelled = true;
    };
  }, [status, threadId]);

  const handleReset = () => {
    esRef.current?.close();
    esRef.current = null;
    setStatus("idle");
    setResult(null);
    setEvents([]);
    setQuestion("");
    setThreadId("");
    setShowChat(false);
    setError(null);
    setSearchParams({}, { replace: true });
  };

  if (status === "idle") {
    return <ResearchForm onSubmit={(q) => void handleStart(q)} />;
  }

  if (status === "error") {
    return (
      <div className="space-y-4">
        <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/30 dark:text-red-300">
          <h2 className="mb-1 text-base font-semibold">Something went wrong</h2>
          <p>{error}</p>
        </div>
        <ResearchForm onSubmit={(q) => void handleStart(q)} />
      </div>
    );
  }

  if (status === "done" && result) {
    return (
      <div className="space-y-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-50">
              {question}
            </h2>
            <p className="mt-0.5 text-xs text-gray-400">
              Session {threadId.slice(0, 8)}…
            </p>
          </div>
          <button
            type="button"
            onClick={handleReset}
            className="shrink-0 rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200 dark:hover:bg-gray-800"
          >
            New research
          </button>
        </div>

        <ReportView
          result={result}
          onFollowUp={() => setShowChat((v) => !v)}
        />
        {showChat && threadId && <ChatPanel threadId={threadId} />}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="min-w-0">
          <h2 className="truncate text-lg font-semibold text-gray-900 dark:text-gray-50">
            {question}
          </h2>
          <p className="mt-0.5 text-xs text-gray-400">
            Session {threadId.slice(0, 8)}… · running in background
          </p>
        </div>
        <button
          type="button"
          onClick={handleReset}
          className="shrink-0 rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200 dark:hover:bg-gray-800"
        >
          Cancel
        </button>
      </div>
      <GraphVisual
        events={events}
        status={status === "loading-result" ? "done" : status}
      />
      <ProgressTimeline
        events={events}
        error={status === "streaming" ? error : null}
      />
    </div>
  );
}