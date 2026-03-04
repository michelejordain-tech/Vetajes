import "./App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "./components/ui/sonner";
import HomePage from "./pages/HomePage";
import ResultsPage from "./pages/ResultsPage";
import AdminPage from "./pages/AdminPage";

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-50">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/resultados" element={<ResultsPage />} />
          <Route path="/admin" element={<AdminPage />} />
        </Routes>
        <Toaster position="top-right" richColors closeButton />
      </div>
    </BrowserRouter>
  );
}

export default App;
