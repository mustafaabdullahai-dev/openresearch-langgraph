import { useState } from "react";

interface Props {
  onSubmit: (question: string) => void;
  disabled?: boolean;
}

const DEMO_QUESTIONS = [
  "What are the environmental impacts of deep-sea mining?",
  "How does CRISPR-Cas9 compare to base editing for treating genetic diseases?",
  "What is the current state of solid-state battery commercialization?",
];

export function ResearchForm({ onSubmit, disabled }: Props) {
  const [question, setQuestion] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = question.trim();
    if (trimmed.length >= 3 && !disabled) {
      onSubmit(trimmed);
    }
  };

  return (
    <section>
      <div className="rounded-2xl border border-gray-200 bg-white p-8 shadow-sm dark:border-gray-800 dark:bg-gray-900">
        <h2 className="text-xl font-semibold">Research Question</h2>
        <form onSubmit={handleSubmit}>
          <textarea
            className="mt-3 w-full rounded-lg border border-gray-300 bg-white p-3 text-sm placeholder:text-gray-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 dark:border-gray-700 dark:bg-gray-950 dark:text-gray-100 dark:placeholder:text-gray-500"
            rows={4}
            placeholder="Enter your research question..."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={disabled}
          />
          <button
            type="submit"
            disabled={disabled || question.trim().length < 3}
            className="mt-4 rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {disabled ? "Researching..." : "Start Research"}
          </button>
        </form>

        <div className="mt-6">
          <p className="mb-2 text-xs font-medium text-gray-500 dark:text-gray-400">
            Try a demo question:
          </p>
          <div className="flex flex-wrap gap-2">
            {DEMO_QUESTIONS.map((q) => (
              <button
                key={q}
                type="button"
                onClick={() => {
                  setQuestion(q);
                }}
                disabled={disabled}
                className="rounded-full border border-gray-200 bg-gray-50 px-3 py-1 text-xs text-gray-600 transition hover:bg-gray-100 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700 disabled:opacity-40"
              >
                {q.length > 50 ? q.slice(0, 50) + "..." : q}
              </button>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
