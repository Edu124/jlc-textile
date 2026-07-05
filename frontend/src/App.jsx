import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./auth.jsx";
import Layout from "./components/Layout.jsx";
import Login from "./pages/Login.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Sales from "./pages/Sales.jsx";
import Purchases from "./pages/Purchases.jsx";
import Inventory from "./pages/Inventory.jsx";
import AIStudio from "./pages/AIStudio.jsx";
import VisitingCards from "./pages/VisitingCards.jsx";
import Reports from "./pages/Reports.jsx";
import Settings from "./pages/Settings.jsx";
import ImportCustomers from "./pages/ImportCustomers.jsx";
import {
  Suppliers, Customers, Units,
} from "./pages/Masters.jsx";

function Protected({ children }) {
  const { isAuthed } = useAuth();
  return isAuthed ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<Protected><Layout /></Protected>}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/sales" element={<Sales />} />
        <Route path="/purchases" element={<Purchases />} />
        <Route path="/inventory" element={<Inventory />} />
        <Route path="/raw-materials" element={<Navigate to="/inventory?tab=raw" replace />} />
        <Route path="/production" element={<Navigate to="/inventory?tab=production" replace />} />
        <Route path="/finished-goods" element={<Navigate to="/inventory?tab=finished" replace />} />
        <Route path="/suppliers" element={<Suppliers />} />
        <Route path="/customers" element={<Customers />} />
        <Route path="/visiting-cards" element={<VisitingCards />} />
        <Route path="/units" element={<Units />} />
        <Route path="/ai" element={<AIStudio />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/import-customers" element={<ImportCustomers />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
