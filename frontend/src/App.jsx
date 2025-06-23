import AdminDashboard from "./pages/AdminDashboard";
import { useAuth } from "./context/AuthContext";

const AppRoutes = () => {
  const { user } = useAuth();

  return (
    <Routes>
      {/* other routes */}
      {user?.is_admin && <Route path="/admin" element={<AdminDashboard />} />}
    </Routes>
  );
};
