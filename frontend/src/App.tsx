import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Overview from "./pages/Overview";
import Settings from "./pages/Settings";
import StockDetail from "./pages/StockDetail";
import WatchlistPage from "./pages/WatchlistPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Overview />} />
        <Route path="/watchlist" element={<WatchlistPage />} />
        <Route path="/stock/:code" element={<StockDetail />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
