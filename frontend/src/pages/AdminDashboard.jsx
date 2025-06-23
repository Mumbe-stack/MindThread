import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import toast from "react-hot-toast";
import Modal from "../components/Modal";
import CreateUserForm from "../components/CreateUserForm";
import CreatePostForm from "../components/CreatePostForm";
import ExportCSV from "../components/ExportCSV";
import { Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
} from "chart.js";

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const AdminDashboard = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState({ users: 0, posts: 0, flagged: 0 });
  const [flaggedComments, setFlaggedComments] = useState([]);
  const [flaggedPosts, setFlaggedPosts] = useState([]);
  const [users, setUsers] = useState([]);
  const [chartData, setChartData] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedPost, setSelectedPost] = useState(null);
  const [selectedComment, setSelectedComment] = useState(null);
  const [showUserForm, setShowUserForm] = useState(false);
  const [showPostForm, setShowPostForm] = useState(false);
  const [exportData, setExportData] = useState([]);

  useEffect(() => {
    if (!user?.is_admin) return;
    fetchData();
  }, [user]);

  const fetchData = async () => {
    const token = localStorage.getItem("token");
    try {
      const [s, c, p, u, trends] = await Promise.all([
        fetch("/api/admin/stats", { headers: { Authorization: `Bearer ${token}` } }).then(res => res.json()),
        fetch("/api/admin/flagged/comments", { headers: { Authorization: `Bearer ${token}` } }).then(res => res.json()),
        fetch("/api/admin/flagged/posts", { headers: { Authorization: `Bearer ${token}` } }).then(res => res.json()),
        fetch("/api/users", { headers: { Authorization: `Bearer ${token}` } }).then(res => res.json()),
        fetch("/api/admin/activity-trends", { headers: { Authorization: `Bearer ${token}` } }).then(res => res.json())
      ]);

      setStats(s);
      setFlaggedComments(c);
      setFlaggedPosts(p);
      setUsers(u);
      setExportData(u);
      setChartData({
        labels: trends.labels,
        datasets: [
          {
            label: "New Posts",
            data: trends.posts,
            backgroundColor: "#34d399"
          },
          {
            label: "New Users",
            data: trends.users,
            backgroundColor: "#60a5fa"
          }
        ]
      });
    } catch (err) {
      console.error("Failed to load admin data", err);
    }
  };

  const handleUserBlockToggle = async (id, block) => {
    const token = localStorage.getItem("token");
    await fetch(`/api/users/${id}/${block ? "block" : "unblock"}`, {
      method: "PATCH",
      headers: { Authorization: `Bearer ${token}` }
    });
    toast.success(`User ${block ? "blocked" : "unblocked"}`);
    fetchData();
  };

  const handleApproveComment = async (id) => {
    const token = localStorage.getItem("token");
    await fetch(`/api/comments/${id}/approve`, {
      method: "PATCH",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ is_approved: true })
    });
    toast.success("Comment approved");
    fetchData();
  };

  const handleApprovePost = async (id) => {
    const token = localStorage.getItem("token");
    await fetch(`/api/posts/${id}/approve`, {
      method: "PATCH",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ is_approved: true })
    });
    toast.success("Post approved");
    fetchData();
  };

  const filteredUsers = users.filter((u) =>
    u.username.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="max-w-6xl mx-auto p-6 text-gray-800">
      <h1 className="text-4xl font-extrabold mb-6 text-blue-800">🛡️ Admin Dashboard</h1>

      <div className="flex gap-4 mb-4">
        <button onClick={() => setShowUserForm(true)} className="bg-indigo-600 text-white px-4 py-2 rounded shadow">
          ➕ Create User
        </button>
        <button onClick={() => setShowPostForm(true)} className="bg-blue-600 text-white px-4 py-2 rounded shadow">
          ➕ Create Post
        </button>
        <ExportCSV data={exportData} filename="users_report.csv" />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-10">
        <div className="bg-blue-200 p-4 rounded shadow font-medium">👤 Users: {stats.users}</div>
        <div className="bg-green-200 p-4 rounded shadow font-medium">📝 Posts: {stats.posts}</div>
        <div className="bg-red-200 p-4 rounded shadow font-medium">🚩 Flagged: {stats.flagged}</div>
      </div>

      {chartData && (
        <div className="bg-white p-4 rounded shadow mb-10">
          <h3 className="text-lg font-semibold mb-4"> Weekly Activity Trends</h3>
          <Bar data={chartData} />
        </div>
      )}

      <section className="mb-8">
        <h2 className="text-xl font-bold mb-3">🚩 Flagged Comments</h2>
        {flaggedComments.map((c) => (
          <div key={c.id} className="border border-gray-200 p-3 rounded mb-2 bg-gray-50 shadow-sm">
            <p className="mb-2 cursor-pointer underline" onClick={() => setSelectedComment(c)}>{c.content}</p>
            <button
              onClick={() => handleApproveComment(c.id)}
              className="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded"
            >✅ Approve</button>
          </div>
        ))}
      </section>

      <section className="mb-8">
        <h2 className="text-xl font-bold mb-3">🚩 Flagged Posts</h2>
        {flaggedPosts.map((p) => (
          <div key={p.id} className="border border-gray-200 p-3 rounded mb-2 bg-gray-50 shadow-sm">
            <p className="font-semibold text-lg cursor-pointer underline" onClick={() => setSelectedPost(p)}>{p.title}</p>
            <p className="text-sm text-gray-600 mb-2">{p.content.slice(0, 150)}...</p>
            <button
              onClick={() => handleApprovePost(p.id)}
              className="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded"
            >✅ Approve</button>
          </div>
        ))}
      </section>

      <section>
        <h2 className="text-xl font-bold mb-3">Manage Users</h2>
        <input
          type="text"
          placeholder="Search users..."
          className="mb-4 w-full p-2 border rounded"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
        {filteredUsers.map((u) => (
          <div key={u.id} className="flex justify-between items-center border-b py-2">
            <p>{u.username} ({u.email})</p>
            <button
              onClick={() => handleUserBlockToggle(u.id, !u.is_blocked)}
              className={`px-3 py-1 rounded text-white ${u.is_blocked ? "bg-yellow-500 hover:bg-yellow-600" : "bg-red-600 hover:bg-red-700"}`}
            >
              {u.is_blocked ? "Unblock" : "Block"}
            </button>
          </div>
        ))}
      </section>

      {/* Modals */}
      {selectedPost && (
        <Modal title={selectedPost.title} onClose={() => setSelectedPost(null)}>
          <p>{selectedPost.content}</p>
        </Modal>
      )}

      {selectedComment && (
        <Modal title={`Comment ID: ${selectedComment.id}`} onClose={() => setSelectedComment(null)}>
          <p>{selectedComment.content}</p>
        </Modal>
      )}

      {showUserForm && (
        <Modal title="Create New User" onClose={() => setShowUserForm(false)}>
          <CreateUserForm onClose={() => { setShowUserForm(false); fetchData(); }} />
        </Modal>
      )}

      {showPostForm && (
        <Modal title="Create New Post" onClose={() => setShowPostForm(false)}>
          <CreatePostForm onClose={() => { setShowPostForm(false); fetchData(); }} />
        </Modal>
      )}
    </div>
  );
};

export default AdminDashboard;
