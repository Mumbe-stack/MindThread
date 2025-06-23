import { Routes, Route } from "react-router-dom";
import { Toaster } from "react-hot-toast"; 
import Home from "./pages/Home";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Profile from "./pages/Profile";
import SinglePost from "./pages/SinglePost";
import AddPost from "./pages/AddPost";
import EditPost from "./pages/EditPost";
import Users from "./pages/Users";
import AdminDashboard from "./pages/AdminDashboard";
import Layout from "./components/Layout";

const App = () => {
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
          <Route path="/profile" element={<Profile />} />
          <Route path="/posts/new" element={<AddPost />} />
          <Route path="/posts/:id" element={<SinglePost />} />
          <Route path="/posts/:id/edit" element={<EditPost />} />
          <Route path="/users" element={<Users />} />
          <Route path="/admin" element={<AdminDashboard />} />
        </Routes>
      </Layout>
    </>
  );
};

export default App;
