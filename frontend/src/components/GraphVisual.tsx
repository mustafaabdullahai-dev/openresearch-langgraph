import type { ProgressEvent } from "../types";

const PIPELINE: { step: string; label: string }[] = [
  { step: "analyzing", label: "Analyze" },
  { step: "planning", label: "Plan" },
  { step: "searching", label: "Search" },
  { step: "sources", label: "Sources" },
  { step: "fact-checking", label: "Fact-check" },
  { step: "evaluating", label: "Evaluate" },
  { step: "reporting", label: "Report" },
  { step: "reviewing", label: "Review" },
  { step: "finalizing", label: "Finalize" },
];

const ERROR_STEPS = new Set(["error"]);

interface Props {
  events: ProgressEvent[];
  status: string;
}

export function GraphVisual({ events, status }: Props) {
  const lastEvent = events[events.length - 1];
  const activeStep = lastEvent ? lastEvent.step : "analyzing";
  const hasError = status === "error" || ERROR_STEPS.has(activeStep);

  const activeIndex = PIPELINE.findIndex((p) => p.step === activeStep);
  const shownCount = activeIndex === -1 ? -1 : activeIndex;

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-800 dark:bg-gray-900">
      <h3 className="mb-4 text-sm font-semibold text-gray-700 dark:text-gray-200">
        Research Pipeline
      </h3>
      <ol className="flex items-center gap-1 overflow-x-auto">
        {PIPELINE.map((node, i) => {
          const done = shownCount > i;
          const active = shownCount === i && !hasError;
          const failed = hasError && shownCount === i;
          return (
            <li key={node.step} className="flex flex-1 items-center gap-1">
              <span
                className={`whitespace-nowrap rounded-lg border px-2.5 py-1.5 text-xs font-medium ${
                  failed
                    ? "border-red-300 bg-red-50 text-red-700 dark:border-red-800 dark:bg-red-900/30 dark:text-red-400"
                    : active
                      ? "border-brand-500 bg-brand-50 text-brand-700 dark:border-brand-500 dark:bg-brand-600/10 dark:text-brand-300"
                      : done
                        ? "border-green-200 bg-green-50 text-green-700 dark:border-green-800/50 dark:bg-green-900/20 dark:text-green-400"
                        : "border-gray-200 bg-gray-50 text-gray-400 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-500"
                }`}
              >
                {done ? "✓ " : active ? "● " : ""}
                {node.label}
              </span>
              {i < PIPELINE.length - 1 && (
                <span
                  className={`h-px flex-1 ${
                    done ? "bg-green-300 dark:bg-green-700" : "bg-gray-200 dark:bg-gray-700"
                  }`}
                />
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}