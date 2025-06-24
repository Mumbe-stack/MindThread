import { Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "react-hot-toast"; 
import { useAuth } from "./context/AuthContext";

import Home from "./pages/Home";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Profile from "./pages/Profile";
import SinglePost from "./pages/SinglePost";
import AddPost from "./pages/AddPost";
import EditPost from "./pages/EditPost";
import Users from "./pages/Users";
import AdminDashboard from "./pages/AdminDashboard";
import NotFound from "./pages/NotFound"; 
import Layout from "./components/Layout";

const App = () => {
  const { user } = useAuth();

  return (
    <>
      {/* Toast Notifications */}
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: "#1f2937",
            color: "#fff",
            fontSize: "14px"
          },
        }}
      />

      <Layout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />

          <Route
            path="/profile"
            element={user ? <Profile /> : <Navigate to="/login" />}
          />
          <Route
            path="/admin"
            element={user && user.is_admin ? <AdminDashboard /> : <Navigate to="/" />}
          />

          <Route path="/posts/new" element={<AddPost />} />
          <Route path="/posts/:id" element={<SinglePost />} />
          <Route path="/posts/:id/edit" element={<EditPost />} />
          <Route path="/users" element={<Users />} />

          <Route path="*" element={<NotFound />} />
        </Routes>
      </Layout>
    </>
  );
};

export default App;
