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

const API = import.meta.env.VITE_API_URL || "https://mindthread-1.onrender.com";

const AdminDashboard = () => {
  const { user, token } = useAuth();
  const [activeTab, setActiveTab] = useState("overview");
  const [loading, setLoading] = useState(false);

  const [stats, setStats] = useState({});
  const [chartData, setChartData] = useState(null);

  const [users, setUsers] = useState([]);
  const [userSearchTerm, setUserSearchTerm] = useState("");
  const [userSearchResults, setUserSearchResults] = useState([]);
  const [searchingUsers, setSearchingUsers] = useState(false);

  const [allPosts, setAllPosts] = useState([]);
  const [allComments, setAllComments] = useState([]);
  const [contentSearchTerm, setContentSearchTerm] = useState("");

  const [flaggedPosts, setFlaggedPosts] = useState([]);
  const [flaggedComments, setFlaggedComments] = useState([]);

  const [showUserForm, setShowUserForm] = useState(false);
  const [showPostForm, setShowPostForm] = useState(false);

  // generic fetch wrapper
  const fetchJson = async (url, options = {}) => {
    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
        ...options.headers
      },
      credentials: "include"
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || err.message || `Error ${res.status}`);
    }
    return res.json();
  };

  useEffect(() => {
    if (user?.is_admin) {
      loadOverview();
    } else if (user) {
      toast.error("Admin access required");
    }
  }, [user, token]);

  useEffect(() => {
    if (!user?.is_admin) return;
    if (activeTab === "users") fetchUsers();
    if (activeTab === "content") fetchContent();
    if (activeTab === "flagged") fetchFlagged();
  }, [activeTab, user]);

  // Overview
  const loadOverview = async () => {
    setLoading(true);
    try {
      const s = await fetchJson(`${API}/api/admin/stats`);
      setStats(s);

      const t = await fetchJson(`${API}/api/admin/activity-trends`);
      setChartData({
        labels: t.labels,
        datasets: [
          {
            label: "Posts",
            data: t.posts,
            backgroundColor: "#34d399"
          },
          {
            label: "Users",
            data: t.users,
            backgroundColor: "#60a5fa"
          }
        ]
      });
      toast.success("Overview loaded");
    } catch (err) {
      console.error(err);
      toast.error(`Overview load failed: ${err.message}`);
      // fallback empty
      setChartData(null);
    } finally {
      setLoading(false);
    }
  };

  // Users
  const fetchUsers = async () => {
    setLoading(true);
    try {
      const data = await fetchJson(`${API}/api/admin/users`);
      setUsers(data.users || data);
    } catch (err) {
      console.error(err);
      toast.error(`Users load failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const handler = setTimeout(() => {
      if (userSearchTerm.trim()) searchUsers();
      else setUserSearchResults([]);
    }, 500);
    return () => clearTimeout(handler);
  }, [userSearchTerm]);

  const searchUsers = async () => {
    setSearchingUsers(true);
    try {
      const data = await fetchJson(
        `${API}/api/admin/users/search?q=${encodeURIComponent(userSearchTerm)}`
      );
      setUserSearchResults(data.users || data);
    } catch {
      // fallback client
      setUserSearchResults(
        users.filter(u =>
          u.username?.toLowerCase().includes(userSearchTerm.toLowerCase()) ||
          u.email?.toLowerCase().includes(userSearchTerm.toLowerCase())
        )
      );
    } finally {
      setSearchingUsers(false);
    }
  };

  // Content
  const fetchContent = async () => {
    setLoading(true);
    try {
      const posts = await fetchJson(`${API}/api/posts`);
      const comments = await fetchJson(`${API}/api/comments`);
      setAllPosts(posts);
      setAllComments(comments);
    } catch (err) {
      console.error(err);
      toast.error(`Content load failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Flagged
  const fetchFlagged = async () => {
    setLoading(true);
    try {
      const fp = await fetchJson(`${API}/api/admin/flagged/posts`);
      const fc = await fetchJson(`${API}/api/admin/flagged/comments`);
      setFlaggedPosts(fp.flagged_posts || fp);
      setFlaggedComments(fc.flagged_comments || fc);
    } catch (err) {
      console.error(err);
      toast.error(`Flagged load failed: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Actions
  const handleUserAction = async (id, action) => {
    try {
      if (action === "delete" && !confirm("Delete user?")) return;
      const url = `${API}/api/admin/users/${id}${action==="delete"?"":`/${action}`}`;
      const method = action === "delete" ? "DELETE" : "PATCH";
      await fetchJson(url, { method });
      toast.success(`User ${action} successful`);
      fetchUsers();
      loadOverview();
    } catch (err) {
      toast.error(err.message);
    }
  };

  const handleContentAction = async (type, id, action) => {
    try {
      if (action === "delete" && !confirm(`Delete ${type}?`)) return;
      const base = type === "post" ? "posts" : "comments";
      const url =
        action === "approve" || action === "reject"
          ? `${API}/api/admin/${base}/${id}`
          : `${API}/api/${base}/${id}`;
      const method = action === "delete" ? "DELETE" : "PATCH";
      const body =
        action === "approve" || action === "reject"
          ? JSON.stringify({ is_approved: action === "approve" })
          : undefined;
      await fetchJson(url, { method, body });
      toast.success(`${type} ${action} successful`);
      fetchContent();
      fetchFlagged();
      loadOverview();
    } catch (err) {
      toast.error(err.message);
    }
  };

  // Filters
  const displayedUsers = userSearchTerm.trim() ? userSearchResults : users;
  const displayedPosts = allPosts.filter(p =>
    p.title.toLowerCase().includes(contentSearchTerm.toLowerCase()) ||
    p.content.toLowerCase().includes(contentSearchTerm.toLowerCase())
  );
  const displayedComments = allComments.filter(c =>
    c.content.toLowerCase().includes(contentSearchTerm.toLowerCase())
  );

  if (!user) return <div>Loading...</div>;
  if (!user.is_admin)
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-red-600">Access Denied</h1>
          <p>You need admin privileges.</p>
        </div>
      </div>
    );

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      <header>
        <h1 className="text-4xl font-bold">Admin Dashboard</h1>
      </header>

      {/* Tabs */}
      <nav className="flex space-x-4 border-b">
        {["overview", "users", "content", "flagged"].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`pb-2 ${
              activeTab === tab
                ? "border-b-2 border-indigo-600 text-indigo-600"
                : "text-gray-600 hover:text-gray-800"
            }`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </nav>

      {/* Loading */}
      {loading && <div>Loading...</div>}

      {/* Overview */}
      {activeTab === "overview" && (
        <section className="space-y-6">
          <div className="flex flex-wrap gap-4">
            <button
              onClick={() => setShowUserForm(true)}
              className="bg-indigo-600 text-white px-4 py-2 rounded"
            >
              Create User
            </button>
            <button
              onClick={() => setShowPostForm(true)}
              className="bg-blue-600 text-white px-4 py-2 rounded"
            >
              Create Post
            </button>
            <ExportCSV data={users} filename="users.csv" />
            <button onClick={loadOverview} className="bg-gray-600 text-white px-4 py-2 rounded">
              Refresh
            </button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {[
              { label: "Users", value: stats.users },
              { label: "Posts", value: stats.posts },
              { label: "Comments", value: stats.comments },
              { label: "Flagged", value: stats.flagged }
            ].map((s) => (
              <div key={s.label} className="bg-gray-50 p-4 rounded shadow">
                <p className="text-sm text-gray-500">{s.label}</p>
                <p className="text-xl font-bold">{s.value || 0}</p>
              </div>
            ))}
          </div>
          {chartData && (
            <div className="h-80 bg-white p-4 rounded shadow">
              <Bar data={chartData} options={{
                responsive: true,
                plugins: {
                  legend: { position: "top" },
                  title: { display: true, text: "Last 7 Days" }
                }
              }} />
            </div>
          )}
        </section>
      )}

      {/* Users */}
      {activeTab === "users" && (
        <section className="space-y-4">
          <div className="flex items-center space-x-2">
            <input
              value={userSearchTerm}
              onChange={(e) => setUserSearchTerm(e.target.value)}
              placeholder="Search users..."
              className="border p-2 rounded flex-1"
            />
            {searchingUsers && <span>🔄</span>}
            <button onClick={fetchUsers} className="bg-indigo-600 text-white px-3 py-1 rounded">
              Refresh
            </button>
          </div>
          <div className="space-y-2">
            {displayedUsers.map(u => (
              <div key={u.id} className="flex justify-between p-4 bg-white rounded shadow">
                <div>
                  <p className="font-medium">{u.username}</p>
                  <p className="text-sm text-gray-500">{u.email}</p>
                </div>
                <div className="flex space-x-2">
                  <button
                    onClick={() => handleUserAction(u.id, u.is_blocked ? "unblock" : "block")}
                    className={`px-3 py-1 rounded ${
                      u.is_blocked ? "bg-green-100" : "bg-red-100"
                    }`}
                  >
                    {u.is_blocked ? "Unblock" : "Block"}
                  </button>
                  <button
                    onClick={() => handleUserAction(u.id, "delete")}
                    className="px-3 py-1 bg-red-100 rounded"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Content */}
      {activeTab === "content" && (
        <section className="space-y-6">
          <div className="flex items-center space-x-2">
            <input
              value={contentSearchTerm}
              onChange={e => setContentSearchTerm(e.target.value)}
              placeholder="Search content..."
              className="border p-2 rounded flex-1"
            />
            <button onClick={fetchContent} className="bg-indigo-600 text-white px-3 py-1 rounded">
              Refresh
            </button>
          </div>
          <div className="space-y-4">
            <div>
              <h3 className="font-semibold">Posts ({displayedPosts.length})</h3>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {displayedPosts.map(p => (
                  <div key={p.id} className="flex justify-between bg-white p-3 rounded shadow">
                    <div>
                      <p className="font-medium">{p.title}</p>
                      <p className="text-xs text-gray-500">{p.author.username}</p>
                    </div>
                    <div className="flex space-x-2">
                      <button
                        onClick={() => handleContentAction("post", p.id, "flag")}
                        className="px-2 py-1 bg-yellow-100 rounded"
                      >
                        Flag
                      </button>
                      <button
                        onClick={() => handleContentAction("post", p.id, "delete")}
                        className="px-2 py-1 bg-red-100 rounded"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <h3 className="font-semibold">Comments ({displayedComments.length})</h3>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {displayedComments.map(c => (
                  <div key={c.id} className="flex justify-between bg-white p-3 rounded shadow">
                    <div>
                      <p>{c.content}</p>
                      <p className="text-xs text-gray-500">{c.author.username}</p>
                    </div>
                    <div className="flex space-x-2">
                      <button
                        onClick={() => handleContentAction("comment", c.id, "flag")}
                        className="px-2 py-1 bg-yellow-100 rounded"
                      >
                        Flag
                      </button>
                      <button
                        onClick={() => handleContentAction("comment", c.id, "delete")}
                        className="px-2 py-1 bg-red-100 rounded"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Flagged */}
      {activeTab === "flagged" && (
        <section className="space-y-6">
          <button onClick={fetchFlagged} className="bg-indigo-600 text-white px-4 py-2 rounded">
            Refresh Flagged
          </button>
          <div>
            <h3 className="font-semibold">Flagged Posts ({flaggedPosts.length})</h3>
            <div className="space-y-2">
              {flaggedPosts.map(p => (
                <div key={p.id} className="flex justify-between bg-white p-3 rounded shadow">
                  <div>
                    <p className="font-medium">{p.title}</p>
                    <p className="text-xs text-gray-500">Flagged on {new Date(p.flagged_at).toLocaleDateString()}</p>
                  </div>
                  <div className="flex space-x-2">
                    <button
                      onClick={() => handleContentAction("post", p.id, "approve")}
                      className="px-2 py-1 bg-green-100 rounded"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => handleContentAction("post", p.id, "delete")}
                      className="px-2 py-1 bg-red-100 rounded"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div>
            <h3 className="font-semibold">Flagged Comments ({flaggedComments.length})</h3>
            <div className="space-y-2">
              {flaggedComments.map(c => (
                <div key={c.id} className="flex justify-between bg-white p-3 rounded shadow">
                  <div>
                    <p>{c.content}</p>
                    <p className="text-xs text-gray-500">Flagged on {new Date(c.flagged_at).toLocaleDateString()}</p>
                  </div>
                  <div className="flex space-x-2">
                    <button
                      onClick={() => handleContentAction("comment", c.id, "approve")}
                      className="px-2 py-1 bg-green-100 rounded"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => handleContentAction("comment", c.id, "delete")}
                      className="px-2 py-1 bg-red-100 rounded"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Modals */}
      {showUserForm && (
        <Modal title="Create User" onClose={() => setShowUserForm(false)}>
          <CreateUserForm
            onClose={() => {
              setShowUserForm(false);
              fetchUsers();
              loadOverview();
            }}
          />
        </Modal>
      )}
      {showPostForm && (
        <Modal title="Create Post" onClose={() => setShowPostForm(false)}>
          <CreatePostForm
            onClose={() => {
              setShowPostForm(false);
              fetchContent();
              loadOverview();
            }}
          />
        </Modal>
      )}
    </div>
  );
};

export default AdminDashboard;