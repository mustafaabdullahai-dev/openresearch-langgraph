import ReactMarkdown from "react-markdown";
import type { ResearchResult } from "../types";

interface Props {
  result: ResearchResult;
  onFollowUp: () => void;
}

export function ReportView({ result, onFollowUp }: Props) {
  const elapsed = result.duration_seconds.toFixed(1);
  return (
    <section className="space-y-6">
      <div className="rounded-2xl border border-gray-200 bg-white p-8 shadow-sm dark:border-gray-800 dark:bg-gray-900">
        <div className="mb-4 flex flex-wrap items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
          <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 font-medium text-emerald-700 dark:bg-emerald-800/30 dark:text-emerald-400">
            completed
          </span>
          <span>{result.iterations} iterations</span>
          <span>&middot;</span>
          <span>{elapsed}s</span>
          <span>&middot;</span>
          <span>{result.sources.length} sources</span>
        </div>

        <article className="prose prose-sm max-w-none dark:prose-invert prose-headings:text-gray-800 prose-p:text-gray-700 dark:prose-headings:text-gray-100 dark:prose-p:text-gray-300">
          <ReactMarkdown>{result.final_report}</ReactMarkdown>
        </article>
      </div>

      {result.sources.length > 0 && (
        <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-gray-900">
          <h3 className="mb-4 text-sm font-semibold text-gray-700 dark:text-gray-200">
            Sources ({result.sources.length})
          </h3>
          <ul className="space-y-3">
            {result.sources.map((src, i) => (
              <li
                key={`${src.url}-${i}`}
                className="rounded-lg border border-gray-100 bg-gray-50 p-3 dark:border-gray-800 dark:bg-gray-800/50"
              >
                <div className="flex items-start justify-between gap-2">
                  <a
                    href={src.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm font-medium text-brand-600 hover:underline dark:text-brand-400"
                  >
                    {src.title || src.url}
                  </a>
                  <span
                    className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${
                      src.quality_tier === "high"
                        ? "bg-green-100 text-green-700 dark:bg-green-800/30 dark:text-green-400"
                        : src.quality_tier === "medium"
                          ? "bg-amber-100 text-amber-700 dark:bg-amber-800/30 dark:text-amber-400"
                          : "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400"
                    }`}
                  >
                    {src.quality_tier}
                  </span>
                </div>
                {src.snippet && (
                  <p className="mt-1.5 text-xs text-gray-500 dark:text-gray-400">
                    {src.snippet.length > 200
                      ? src.snippet.slice(0, 200) + "..."
                      : src.snippet}
                  </p>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      <button
        type="button"
        onClick={onFollowUp}
        className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-200 dark:hover:bg-gray-800"
      >
        Ask a follow-up
      </button>
    </section>
  );
}
