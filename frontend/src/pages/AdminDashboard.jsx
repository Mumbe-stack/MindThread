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


const VITE_API_URL = import.meta.env.VITE_API_URL || "https://mindthread.onrender.com";

const AdminDashboard = () => {
  const { user, token } = useAuth();
  const [activeTab, setActiveTab] = useState("overview");
  const [loading, setLoading] = useState(false);
  
  
  const [stats, setStats] = useState({ 
    users: 0, 
    posts: 0, 
    comments: 0, 
    flagged: 0,
    flagged_posts: 0,
    flagged_comments: 0,
    blocked_users: 0
  });
  const [chartData, setChartData] = useState(null);
  
  
  const [users, setUsers] = useState([]);
  const [userSearchTerm, setUserSearchTerm] = useState("");
  const [userSearchResults, setUserSearchResults] = useState([]);
  const [searchingUsers, setSearchingUsers] = useState(false);
  
  
  const [flaggedComments, setFlaggedComments] = useState([]);
  const [flaggedPosts, setFlaggedPosts] = useState([]);
  const [allPosts, setAllPosts] = useState([]);
  const [allComments, setAllComments] = useState([]);
  const [contentSearchTerm, setContentSearchTerm] = useState("");
  
  
  const [selectedPost, setSelectedPost] = useState(null);
  const [selectedComment, setSelectedComment] = useState(null);
  const [selectedUser, setSelectedUser] = useState(null);
  const [showUserForm, setShowUserForm] = useState(false);
  const [showPostForm, setShowPostForm] = useState(false);

  
  const handleApiResponse = async (response, errorMessage = "API request failed") => {
    if (!response.ok) {
      if (response.status === 404) {
        
        throw new Error(`Endpoint not found: ${response.url}`);
      }
      if (response.status === 403) {
        throw new Error("Admin access required");
      }
      throw new Error(`${errorMessage} (${response.status})`);
    }

    const contentType = response.headers.get("content-type");
    if (!contentType || !contentType.includes("application/json")) {
    
      throw new Error("Server returned non-JSON response");
    }

    return response.json();
  };

  useEffect(() => {
  
    if (!user?.is_admin) {
      if (user) {
        toast.error("Admin access required");
      }
      return;
    }
    fetchOverviewData();
  }, [user]);

  useEffect(() => {
    if (activeTab === "users") {
      fetchAllUsers();
    } else if (activeTab === "content") {
      fetchAllContent();
    } else if (activeTab === "flagged") {
      fetchFlaggedContent();
    }
  }, [activeTab]);

  
  useEffect(() => {
    const delayedSearch = setTimeout(() => {
      if (userSearchTerm.trim().length > 0) {
        searchUsers();
      } else {
        setUserSearchResults([]);
      }
    }, 500);

    return () => clearTimeout(delayedSearch);
  }, [userSearchTerm]);

  const fetchOverviewData = async () => {
    setLoading(true);
    try {
      

      const statsResponse = await fetch(`${VITE_API_URL}/api/admin/stats`, { 
        headers: { 
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json"
        } 
      });


      const statsData = await handleApiResponse(statsResponse, "Failed to fetch stats");
      setStats(statsData);

      
      try {
        const trendsResponse = await fetch(`${VITE_API_URL}/api/admin/activity-trends`, { 
          headers: { 
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json"
          } 
        });

        if (trendsResponse.ok) {
          const trendsData = await handleApiResponse(trendsResponse, "Failed to fetch trends");
          setChartData({
            labels: trendsData.labels,
            datasets: [
              {
                label: "New Posts",
                data: trendsData.posts,
                backgroundColor: "#34d399",
                borderColor: "#10b981",
                borderWidth: 1
              },
              {
                label: "New Users",
                data: trendsData.users,
                backgroundColor: "#60a5fa",
                borderColor: "#3b82f6",
                borderWidth: 1
              }
            ]
          });
        } else {
        
         
          setChartData({
            labels: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            datasets: [
              {
                label: "New Posts",
                data: [1, 2, 0, 3, 1, 2, 1],
                backgroundColor: "#34d399",
                borderColor: "#10b981",
                borderWidth: 1
              },
              {
                label: "New Users",
                data: [0, 1, 0, 1, 0, 0, 1],
                backgroundColor: "#60a5fa",
                borderColor: "#3b82f6",
                borderWidth: 1
              }
            ]
          });
        }
      } catch (trendsError) {
        
      }

      toast.success("Dashboard data loaded");

    } catch (err) {
      
      toast.error(`Failed to load dashboard data: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const fetchAllUsers = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${VITE_API_URL}/api/users`, { 
        headers: { 
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json"
        } 
      });
      
      const data = await handleApiResponse(response, "Failed to fetch users");
      setUsers(data);
    } catch (err) {
      
      toast.error(`Failed to load users: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const searchUsers = async () => {
    if (!userSearchTerm.trim()) return;
    
    setSearchingUsers(true);
    try {
      const response = await fetch(`${VITE_API_URL}/api/admin/users/search?q=${encodeURIComponent(userSearchTerm)}`, {
        headers: { 
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json"
        }
      });
      
      const data = await handleApiResponse(response, "User search failed");
      setUserSearchResults(data);
    } catch (err) {
      
      
      const filtered = users.filter(u => 
        u.username.toLowerCase().includes(userSearchTerm.toLowerCase()) ||
        u.email.toLowerCase().includes(userSearchTerm.toLowerCase())
      );
      setUserSearchResults(filtered);
    } finally {
      setSearchingUsers(false);
    }
  };

  const fetchAllContent = async () => {
    setLoading(true);
    try {
      const [postsRes, commentsRes] = await Promise.all([
        fetch(`${VITE_API_URL}/api/posts`, { 
          headers: { 
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json"
          } 
        }),
        fetch(`${VITE_API_URL}/api/comments`, { 
          headers: { 
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json"
          } 
        })
      ]);

      const [posts, comments] = await Promise.all([
        handleApiResponse(postsRes, "Failed to fetch posts"),
        handleApiResponse(commentsRes, "Failed to fetch comments")
      ]);

      setAllPosts(posts);
      setAllComments(comments);
    } catch (err) {
      
      toast.error(`Failed to load content: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const fetchFlaggedContent = async () => {
    setLoading(true);
    try {
      
      let flaggedPostsData = [];
      let flaggedCommentsData = [];

      try {
        const postsRes = await fetch(`${VITE_API_URL}/api/admin/flagged/posts`, { 
          headers: { 
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json"
          } 
        });
        if (postsRes.ok) {
          flaggedPostsData = await handleApiResponse(postsRes, "Failed to fetch flagged posts");
        }
      } catch (err) {
        
      }

      try {
        const commentsRes = await fetch(`${VITE_API_URL}/api/admin/flagged/comments`, { 
          headers: { 
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json"
          } 
        });
        if (commentsRes.ok) {
          flaggedCommentsData = await handleApiResponse(commentsRes, "Failed to fetch flagged comments");
        }
      } catch (err) {
    
      }

      setFlaggedPosts(flaggedPostsData);
      setFlaggedComments(flaggedCommentsData);
    } catch (err) {
     
      toast.error(`Failed to load flagged content: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleUserAction = async (userId, action) => {
    try {
      let endpoint = "";
      let method = "PATCH";
      let body = null;

      switch (action) {
        case "block":
        case "unblock":
          endpoint = `${VITE_API_URL}/api/users/${userId}/block`;
          break;
        case "delete":
          if (!window.confirm("Are you sure you want to delete this user? This action cannot be undone.")) {
            return;
          }
          endpoint = `${VITE_API_URL}/api/users/${userId}`;
          method = "DELETE";
          break;
        case "make_admin":
          endpoint = `${VITE_API_URL}/api/users/${userId}`;
          body = JSON.stringify({ is_admin: true });
          break;
        case "remove_admin":
          endpoint = `${VITE_API_URL}/api/users/${userId}`;
          body = JSON.stringify({ is_admin: false });
          break;
      }

      const response = await fetch(endpoint, {
        method,
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body
      });

      await handleApiResponse(response, `Failed to ${action} user`);
      toast.success(`User ${action} successful`);
      fetchAllUsers();
      fetchOverviewData();
    } catch (err) {
     
      toast.error(err.message);
    }
  };

  const handleContentAction = async (type, id, action) => {
    try {
      let endpoint = "";
      let method = "PATCH";
      let body = null;

      switch (action) {
        case "approve":
          endpoint = `${VITE_API_URL}/api/${type}s/${id}/approve`;
          body = JSON.stringify({ is_approved: true });
          break;
        case "reject":
          endpoint = `${VITE_API_URL}/api/${type}s/${id}/approve`;
          body = JSON.stringify({ is_approved: false });
          break;
        case "flag":
          endpoint = `${VITE_API_URL}/api/${type}s/${id}/flag`;
          break;
        case "delete":
          if (!window.confirm(`Are you sure you want to delete this ${type}? This action cannot be undone.`)) {
            return;
          }
          endpoint = `${VITE_API_URL}/api/${type}s/${id}`;
          method = "DELETE";
          break;
      }

      const response = await fetch(endpoint, {
        method,
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json"
        },
        body
      });

      await handleApiResponse(response, `Failed to ${action} ${type}`);
      toast.success(`${type} ${action} successful`);
      fetchFlaggedContent();
      fetchAllContent();
      fetchOverviewData();
    } catch (err) {
      ;
      toast.error(err.message);
    }
  };

  const filteredUsers = userSearchTerm.trim() 
    ? userSearchResults 
    : users.filter(u => 
        u.username.toLowerCase().includes(userSearchTerm.toLowerCase()) ||
        u.email.toLowerCase().includes(userSearchTerm.toLowerCase())
      );

  const filteredPosts = allPosts.filter(p =>
    p.title.toLowerCase().includes(contentSearchTerm.toLowerCase()) ||
    p.content.toLowerCase().includes(contentSearchTerm.toLowerCase())
  );

  const filteredComments = allComments.filter(c =>
    c.content.toLowerCase().includes(contentSearchTerm.toLowerCase())
  );

  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (!user?.is_admin) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-red-600 mb-4">Access Denied</h1>
          <p className="text-gray-600">You need admin privileges to access this page.</p>
          <p className="text-sm text-gray-500 mt-2">Current user: {user?.username || "Not logged in"}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">🛡️ Admin Dashboard</h1>
        <p className="text-gray-600">Manage users, content, and monitor platform activity</p>
        {/* Debug info */}
        <div className="text-xs text-gray-400 mt-2">
          API: {VITE_API_URL} | User: {user.username} | Admin: {user.is_admin ? "Yes" : "No"}
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: "overview", label: "📊 Overview", icon: "📊" },
            { id: "users", label: "👥 Users", icon: "👥" },
            { id: "content", label: "📝 Content", icon: "📝" },
            { id: "flagged", label: "🚩 Flagged", icon: "🚩" }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab.id
                  ? "border-indigo-500 text-indigo-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {loading && (
        <div className="flex justify-center items-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
          <span className="ml-2 text-gray-600">Loading...</span>
        </div>
      )}

      {/* Overview Tab */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          {/* Quick Actions */}
          <div className="flex flex-wrap gap-4">
            <button
              onClick={() => setShowUserForm(true)}
              className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 flex items-center gap-2"
            >
              ➕ Create User
            </button>
            <button
              onClick={() => setShowPostForm(true)}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center gap-2"
            >
              ➕ Create Post
            </button>
            <ExportCSV data={users} filename="users_report.csv" />
            <button
              onClick={fetchOverviewData}
              className="bg-gray-600 text-white px-4 py-2 rounded-lg hover:bg-gray-700 flex items-center gap-2"
            >
              🔄 Refresh Data
            </button>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="bg-blue-50 p-6 rounded-lg border border-blue-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-blue-600 text-sm font-medium">Total Users</p>
                  <p className="text-2xl font-bold text-blue-900">{stats.users}</p>
                </div>
                <div className="text-blue-500">👥</div>
              </div>
            </div>

            <div className="bg-green-50 p-6 rounded-lg border border-green-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-green-600 text-sm font-medium">Total Posts</p>
                  <p className="text-2xl font-bold text-green-900">{stats.posts}</p>
                </div>
                <div className="text-green-500">📝</div>
              </div>
            </div>

            <div className="bg-purple-50 p-6 rounded-lg border border-purple-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-purple-600 text-sm font-medium">Total Comments</p>
                  <p className="text-2xl font-bold text-purple-900">{stats.comments}</p>
                </div>
                <div className="text-purple-500">💬</div>
              </div>
            </div>

            <div className="bg-red-50 p-6 rounded-lg border border-red-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-red-600 text-sm font-medium">Flagged Content</p>
                  <p className="text-2xl font-bold text-red-900">{stats.flagged}</p>
                </div>
                <div className="text-red-500">🚩</div>
              </div>
            </div>
          </div>

          {/* Activity Chart */}
          {chartData && (
            <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
              <h3 className="text-lg font-semibold mb-4">📊 Weekly Activity Trends</h3>
              <Bar 
                data={chartData} 
                options={{
                  responsive: true,
                  plugins: {
                    legend: {
                      position: 'top',
                    },
                    title: {
                      display: true,
                      text: 'Platform Activity (Last 7 Days)'
                    }
                  },
                  scales: {
                    y: {
                      beginAtZero: true
                    }
                  }
                }}
              />
            </div>
          )}
        </div>
      )}

      
      {activeTab !== "overview" && (
        <div className="text-center py-12">
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            {activeTab.charAt(0).toUpperCase() + activeTab.slice(1)} Management
          </h3>
          <p className="text-gray-600">This section is being loaded...</p>
          <button
            onClick={() => {
              if (activeTab === "users") fetchAllUsers();
              else if (activeTab === "content") fetchAllContent();
              else if (activeTab === "flagged") fetchFlaggedContent();
            }}
            className="mt-4 bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700"
          >
            Load {activeTab.charAt(0).toUpperCase() + activeTab.slice(1)} Data
          </button>
        </div>
      )}

      {/* Modals */}
      {showUserForm && (
        <Modal title="Create New User" onClose={() => setShowUserForm(false)}>
          <CreateUserForm 
            onClose={() => { 
              setShowUserForm(false); 
              fetchAllUsers(); 
              fetchOverviewData(); 
            }} 
          />
        </Modal>
      )}

      {showPostForm && (
        <Modal title="Create New Post" onClose={() => setShowPostForm(false)}>
          <CreatePostForm 
            onClose={() => { 
              setShowPostForm(false); 
              fetchAllContent(); 
              fetchOverviewData(); 
            }} 
          />
        </Modal>
      )}

    
      {process.env.NODE_ENV === 'development' && (
        <div className="fixed bottom-4 right-4 bg-gray-800 text-white p-4 rounded-lg text-xs max-w-sm">
          <h4 className="font-bold mb-2">Debug Info</h4>
          <div>API Base URL: {VITE_API_URL}</div>
          <div>User: {user?.username}</div>
          <div>Is Admin: {user?.is_admin ? "Yes" : "No"}</div>
          <div>Token: {token ? "Present" : "Missing"}</div>
          <div>Active Tab: {activeTab}</div>
          <div>Loading: {loading ? "Yes" : "No"}</div>
        </div>
      )}
    </div>
  );
};

export default AdminDashboard;