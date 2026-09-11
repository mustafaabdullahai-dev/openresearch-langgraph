import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { deleteResearch, listSessions } from "../services/api";
import type { Session } from "../types";

const STATUS_STYLES: Record<string, string> = {
  running:
    "bg-amber-100 text-amber-700 dark:bg-amber-800/30 dark:text-amber-400",
  completed:
    "bg-emerald-100 text-emerald-700 dark:bg-emerald-800/30 dark:text-emerald-400",
  failed: "bg-red-100 text-red-700 dark:bg-red-800/30 dark:text-red-400",
};

export function DashboardPage() {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setSessions(await listSessions(50));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to list sessions");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleDelete = async (id: string) => {
    try {
      await deleteResearch(id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete session");
    }
  };

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });

  return (
    <section className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-900">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-50">
          Research History
        </h2>
        <button
          type="button"
          onClick={() => void refresh()}
          className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
        >
          Refresh
        </button>
      </div>

      {error && (
        <p className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
          {error}
        </p>
      )}

      {loading ? (
        <p className="py-8 text-center text-sm text-gray-400">
          Loading sessions…
        </p>
      ) : sessions.length === 0 ? (
        <p className="py-8 text-center text-sm text-gray-400">
          No research sessions yet.
        </p>
      ) : (
        <ul className="divide-y divide-gray-100 dark:divide-gray-800">
          {sessions.map((s) => (
            <li
              key={s.thread_id}
              className="flex flex-wrap items-center justify-between gap-3 py-3"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-gray-800 dark:text-gray-100">
                  {s.question}
                </p>
                <p className="mt-0.5 text-xs text-gray-400">
                  {formatDate(s.created_at)} · {s.source_count} sources
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                    STATUS_STYLES[s.status] ??
                    "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400"
                  }`}
                >
                  {s.status}
                </span>
                <button
                  type="button"
                  onClick={() => navigate(`/?thread=${s.thread_id}`)}
                  className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-brand-600 transition hover:bg-brand-50 dark:border-gray-700 dark:text-brand-400 dark:hover:bg-gray-800"
                >
                  View
                </button>
                <button
                  type="button"
                  onClick={() => void handleDelete(s.thread_id)}
                  className="rounded-lg border border-red-200 px-3 py-1.5 text-xs font-medium text-red-600 transition hover:bg-red-50 dark:border-red-800/50 dark:text-red-400 dark:hover:bg-red-900/20"
                >
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}