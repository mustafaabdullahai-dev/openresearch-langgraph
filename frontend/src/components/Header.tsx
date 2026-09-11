import { Link } from "react-router-dom";
import { useDarkMode } from "../hooks/useDarkMode";

export function Header() {
  const { dark, toggle } = useDarkMode();

  return (
    <header className="border-b border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
        <div className="flex items-center gap-2">
          <span className="text-xl">🔬</span>
          <Link to="/" className="text-lg font-semibold">
            OpenResearch
          </Link>
        </div>
        <div className="flex items-center gap-3">
          <Link
            to="/dashboard"
            className="text-sm text-gray-500 transition hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
          >
            History
          </Link>
          <span className="hidden rounded-full bg-brand-100 px-3 py-1 text-xs font-medium text-brand-700 dark:bg-brand-700/20 dark:text-brand-500 sm:inline">
            local · open-source
          </span>
          <button
            type="button"
            onClick={toggle}
            aria-label="Toggle dark mode"
            className="rounded-lg border border-gray-200 px-2.5 py-1.5 text-sm transition hover:bg-gray-100 dark:border-gray-700 dark:hover:bg-gray-800"
          >
            {dark ? "☀️" : "🌙"}
          </button>
        </div>
      </div>
    </header>
  );
}