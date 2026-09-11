import type { ProgressEvent } from "../types";

const STEP_ICONS: Record<string, { icon: string; color: string }> = {
  analyzing: { icon: "🔍", color: "text-blue-500" },
  planning: { icon: "📋", color: "text-indigo-500" },
  searching: { icon: "🌐", color: "text-cyan-500" },
  sources: { icon: "📄", color: "text-emerald-500" },
  "fact-checking": { icon: "✅", color: "text-green-500" },
  evaluating: { icon: "⚖️", color: "text-amber-500" },
  reporting: { icon: "📝", color: "text-purple-500" },
  reviewing: { icon: "👁️", color: "text-pink-500" },
  finalizing: { icon: "🏁", color: "text-gray-500" },
  error: { icon: "❌", color: "text-red-500" },
  started: { icon: "🚀", color: "text-brand-500" },
  complete: { icon: "✨", color: "text-green-600" },
};

function getStepStyle(step: string) {
  return STEP_ICONS[step] ?? { icon: "•", color: "text-gray-400" };
}

interface Props {
  events: ProgressEvent[];
  error?: string | null;
}

export function ProgressTimeline({ events, error }: Props) {
  return (
    <section className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-900">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200">
          Research Progress
        </h3>
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
      </div>

      <ol className="space-y-3">
        {events.map((ev, i) => {
          const { icon, color } = getStepStyle(ev.step);
          return (
            <li key={`${ev.step}-${i}`} className="flex items-start gap-3">
              <span className={`mt-0.5 text-base ${color}`}>{icon}</span>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-800 dark:text-gray-100">
                  {ev.message}
                </p>
                <p className="mt-0.5 text-xs text-gray-400 dark:text-gray-500">
                  {ev.step} &middot; {ev.timestamp.toFixed(1)}s
                </p>
              </div>
            </li>
          );
        })}
      </ol>

      {error && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/30 dark:text-red-300">
          {error}
        </div>
      )}
    </section>
  );
}
