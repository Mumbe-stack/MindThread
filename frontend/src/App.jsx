import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import { Toaster } from "react-hot-toast";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import Posts from "./pages/Posts";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Profile from "./pages/Profile";
import Users from "./pages/Users";
import AddPost from "./pages/AddPost";
import EditPost from "./pages/EditPost";
import SinglePost from "./pages/SinglePost";
import AdminDashboard from "./pages/AdminDashboard";
import Comment from "./pages/Comments";

function App() {
  const { user } = useAuth();
  
  if (user === undefined) {
    return <div className="p-10 text-center">Loading...</div>;
  }
  
  const isAdmin = user?.is_admin;
  
  return (
    <>
      <Toaster position="top-right" reverseOrder={false} />
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Home />} />
          <Route path="/posts" element={<Posts />} />
          <Route path="/login" element={!user ? <Login /> : <Navigate to="/" />} />
          <Route path="/register" element={!user ? <Register /> : <Navigate to="/" />} />
          <Route path="/profile" element={user ? <Profile /> : <Navigate to="/login" />} />
          <Route path="/users" element={isAdmin ? <Users /> : <Navigate to="/" />} />
          <Route path="/admin" element={isAdmin ? <AdminDashboard /> : <Navigate to="/" />} />
          <Route path="/posts/new" element={user ? <AddPost /> : <Navigate to="/login" />} />
          <Route path="/posts/:id" element={<SinglePost />} />
          <Route path="/posts/:id/edit" element={user ? <EditPost /> : <Navigate to="/login" />} />

         
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </>
  );
}

export default App;