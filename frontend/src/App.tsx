import {
  BrowserRouter as Router,
  Navigate,
  Route,
  Routes,
} from "react-router-dom";

import { Header } from "./components/Header";
import { DashboardPage } from "./pages/DashboardPage";
import { ResearchPage } from "./pages/ResearchPage";

export default function App() {
  return (
    <Router>
      <div className="min-h-screen bg-white dark:bg-gray-950">
        <Header />
        <main className="mx-auto max-w-5xl px-4 py-8">
          <Routes>
            <Route path="/" element={<ResearchPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}