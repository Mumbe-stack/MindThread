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

const API_URL = import.meta.env.VITE_API_URL || "https://mindthread-1.onrender.com";

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
  
  const [showUserForm, setShowUserForm] = useState(false);
  const [showPostForm, setShowPostForm] = useState(false);

  // Enhanced API response handler
  const handleApiResponse = async (response, errorMessage = "API request failed") => {
    if (!response.ok) {
      let errorText = errorMessage;
      try {
        const errorData = await response.json();
        errorText = errorData.error || errorData.message || errorMessage;
      } catch {
        if (response.status === 404) {
          errorText = `Endpoint not found: ${response.url}`;
        } else if (response.status === 403) {
          errorText = "Admin access required";
        } else if (response.status === 401) {
          errorText = "Authentication required";
        } else {
          errorText = `${errorMessage} (${response.status})`;
        }
      }
      throw new Error(errorText);
    }

    const contentType = response.headers.get("content-type");
    if (!contentType || !contentType.includes("application/json")) {
      throw new Error("Server returned non-JSON response");
    }

    return response.json();
  };

  // Enhanced authenticated fetch function
  const makeAuthenticatedRequest = async (url, options = {}) => {
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
          ...options.headers,
        },
        credentials: "include",
      });
      return response;
    } catch (error) {
      console.error("Network error:", error);
      throw new Error("Network error. Please check your connection.");
    }
  };

  useEffect(() => {
    if (!user?.is_admin) {
      if (user) {
        toast.error("Admin access required");
      }
      return;
    }
    fetchOverviewData();
  }, [user, token]);

  useEffect(() => {
    if (!user?.is_admin) return;
    
    if (activeTab === "users") {
      fetchAllUsers();
    } else if (activeTab === "content") {
      fetchAllContent();
    } else if (activeTab === "flagged") {
      fetchFlaggedContent();
    }
  }, [activeTab, user, token]);

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
    if (!token || !user?.is_admin) return;
    
    setLoading(true);
    try {
      console.log("Fetching admin stats from:", `${API_URL}/api/admin/stats`);
      
      const statsResponse = await makeAuthenticatedRequest(`${API_URL}/api/admin/stats`);
      const statsData = await handleApiResponse(statsResponse, "Failed to fetch stats");
      
      console.log("Stats data received:", statsData);
      setStats(statsData);

      // Fetch activity trends
      try {
        const trendsResponse = await makeAuthenticatedRequest(`${API_URL}/api/admin/activity-trends`);
        
        if (trendsResponse.ok) {
          const trendsData = await handleApiResponse(trendsResponse, "Failed to fetch trends");
          setChartData({
            labels: trendsData.labels || ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            datasets: [
              {
                label: "New Posts",
                data: trendsData.posts || [1, 2, 0, 3, 1, 2, 1],
                backgroundColor: "#34d399",
                borderColor: "#10b981",
                borderWidth: 1
              },
              {
                label: "New Users",
                data: trendsData.users || [0, 1, 0, 1, 0, 0, 1],
                backgroundColor: "#60a5fa",
                borderColor: "#3b82f6",
                borderWidth: 1
              },
              {
                label: "New Comments",
                data: trendsData.comments || [2, 3, 1, 4, 2, 3, 2],
                backgroundColor: "#f472b6",
                borderColor: "#ec4899",
                borderWidth: 1
              }
            ]
          });
        } else {
          // Fallback chart data
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
        console.log("Activity trends not available, using fallback data");
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

      toast.success("Dashboard data loaded successfully");

    } catch (err) {
      console.error("Dashboard data fetch error:", err);
      toast.error(`Failed to load dashboard data: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const fetchAllUsers = async () => {
    if (!token || !user?.is_admin) return;
    
    setLoading(true);
    try {
      // Use admin-specific endpoint for getting all users
      const response = await makeAuthenticatedRequest(`${API_URL}/api/admin/users`);
      const data = await handleApiResponse(response, "Failed to fetch users");
      
      const usersArray = Array.isArray(data) ? data : (data.users || []);
      setUsers(usersArray);
      
    } catch (err) {
      console.error("Users fetch error:", err);
      // Fallback to regular users endpoint
      try {
        const fallbackResponse = await makeAuthenticatedRequest(`${API_URL}/api/users`);
        const fallbackData = await handleApiResponse(fallbackResponse, "Failed to fetch users");
        const usersArray = Array.isArray(fallbackData) ? fallbackData : (fallbackData.users || []);
        setUsers(usersArray);
      } catch (fallbackErr) {
        toast.error(`Failed to load users: ${err.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  const searchUsers = async () => {
    if (!userSearchTerm.trim() || !token) return;
    
    setSearchingUsers(true);
    try {
      const response = await makeAuthenticatedRequest(
        `${API_URL}/api/admin/users/search?q=${encodeURIComponent(userSearchTerm)}`
      );
      
      if (response.ok) {
        const data = await handleApiResponse(response, "User search failed");
        setUserSearchResults(Array.isArray(data) ? data : (data.users || []));
      } else {
        // Fallback to client-side search
        const filtered = users.filter(u => 
          u.username?.toLowerCase().includes(userSearchTerm.toLowerCase()) ||
          u.email?.toLowerCase().includes(userSearchTerm.toLowerCase())
        );
        setUserSearchResults(filtered);
      }
    } catch (err) {
      console.error("User search error:", err);
      // Fallback to client-side search
      const filtered = users.filter(u => 
        u.username?.toLowerCase().includes(userSearchTerm.toLowerCase()) ||
        u.email?.toLowerCase().includes(userSearchTerm.toLowerCase())
      );
      setUserSearchResults(filtered);
    } finally {
      setSearchingUsers(false);
    }
  };

  const fetchAllContent = async () => {
    if (!token || !user?.is_admin) return;
    
    setLoading(true);
    try {
      // Try admin-specific endpoints first
      let postsData = [];
      let commentsData = [];

      try {
        const postsRes = await makeAuthenticatedRequest(`${API_URL}/api/admin/posts`);
        if (postsRes.ok) {
          const data = await handleApiResponse(postsRes, "Failed to fetch posts");
          postsData = Array.isArray(data) ? data : (data.posts || []);
        }
      } catch (err) {
        console.log("Admin posts endpoint not available, trying regular endpoint");
        try {
          const postsRes = await makeAuthenticatedRequest(`${API_URL}/api/posts`);
          const data = await handleApiResponse(postsRes, "Failed to fetch posts");
          postsData = Array.isArray(data) ? data : (data.posts || []);
        } catch (fallbackErr) {
          console.error("Failed to fetch posts from both endpoints:", fallbackErr);
        }
      }

      try {
        const commentsRes = await makeAuthenticatedRequest(`${API_URL}/api/admin/comments`);
        if (commentsRes.ok) {
          const data = await handleApiResponse(commentsRes, "Failed to fetch comments");
          commentsData = Array.isArray(data) ? data : (data.comments || []);
        }
      } catch (err) {
        console.log("Admin comments endpoint not available");
        // Don't try regular comments endpoint as it requires post_id parameter
        commentsData = [];
      }

      setAllPosts(postsData);
      setAllComments(commentsData);
      
    } catch (err) {
      console.error("Content fetch error:", err);
      toast.error(`Failed to load content: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const fetchFlaggedContent = async () => {
    if (!token || !user?.is_admin) return;
    
    setLoading(true);
    try {
      let flaggedPostsData = [];
      let flaggedCommentsData = [];

      // Try to fetch flagged posts
      try {
        const postsRes = await makeAuthenticatedRequest(`${API_URL}/api/admin/flagged/posts`);
        if (postsRes.ok) {
          const data = await handleApiResponse(postsRes, "Failed to fetch flagged posts");
          flaggedPostsData = Array.isArray(data) ? data : (data.posts || []);
        }
      } catch (err) {
        console.log("Flagged posts endpoint not available");
      }

      // Try to fetch flagged comments
      try {
        const commentsRes = await makeAuthenticatedRequest(`${API_URL}/api/admin/flagged/comments`);
        if (commentsRes.ok) {
          const data = await handleApiResponse(commentsRes, "Failed to fetch flagged comments");
          flaggedCommentsData = Array.isArray(data) ? data : (data.comments || []);
        }
      } catch (err) {
        console.log("Flagged comments endpoint not available");
      }

      setFlaggedPosts(flaggedPostsData);
      setFlaggedComments(flaggedCommentsData);
      
    } catch (err) {
      console.error("Flagged content fetch error:", err);
      toast.error(`Failed to load flagged content: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleUserAction = async (userId, action) => {
    if (!token || !user?.is_admin) return;
    
    try {
      let endpoint = "";
      let method = "POST"; // Changed default method
      let body = null;

      switch (action) {
        case "block":
          endpoint = `${API_URL}/api/users/${userId}/block`;
          method = "POST";
          break;
        case "unblock":
          endpoint = `${API_URL}/api/users/${userId}/unblock`;
          method = "POST";
          break;
        case "delete":
          if (!window.confirm("Are you sure you want to delete this user? This action cannot be undone.")) {
            return;
          }
          endpoint = `${API_URL}/api/users/${userId}`;
          method = "DELETE";
          break;
        case "make_admin":
          endpoint = `${API_URL}/api/users/${userId}`;
          method = "PATCH";
          body = JSON.stringify({ is_admin: true });
          break;
        case "remove_admin":
          endpoint = `${API_URL}/api/users/${userId}`;
          method = "PATCH";
          body = JSON.stringify({ is_admin: false });
          break;
      }

      const response = await makeAuthenticatedRequest(endpoint, {
        method,
        body
      });

      await handleApiResponse(response, `Failed to ${action} user`);
      toast.success(`User ${action} successful`);
      
      // Refresh data
      await fetchAllUsers();
      await fetchOverviewData();
      
    } catch (err) {
      console.error(`User ${action} error:`, err);
      toast.error(err.message);
    }
  };

  const handleContentAction = async (type, id, action) => {
    if (!token || !user?.is_admin) return;
    
    try {
      let endpoint = "";
      let method = "PATCH";
      let body = null;

      switch (action) {
        case "approve":
          endpoint = `${API_URL}/api/${type}s/${id}/approve`;
          body = JSON.stringify({ is_approved: true });
          break;
        case "reject":
          endpoint = `${API_URL}/api/${type}s/${id}/approve`;
          body = JSON.stringify({ is_approved: false });
          break;
        case "flag":
          endpoint = `${API_URL}/api/${type}s/${id}/flag`;
          method = "POST";
          break;
        case "delete":
          if (!window.confirm(`Are you sure you want to delete this ${type}? This action cannot be undone.`)) {
            return;
          }
          endpoint = `${API_URL}/api/${type}s/${id}`;
          method = "DELETE";
          break;
      }

      const response = await makeAuthenticatedRequest(endpoint, {
        method,
        body
      });

      await handleApiResponse(response, `Failed to ${action} ${type}`);
      toast.success(`${type} ${action} successful`);
      
      // Refresh data
      await fetchFlaggedContent();
      await fetchAllContent();
      await fetchOverviewData();
      
    } catch (err) {
      console.error(`Content ${action} error:`, err);
      toast.error(err.message);
    }
  };

  // Filter functions with null checks
  const filteredUsers = userSearchTerm.trim() 
    ? userSearchResults 
    : users.filter(u => 
        u?.username?.toLowerCase().includes(userSearchTerm.toLowerCase()) ||
        u?.email?.toLowerCase().includes(userSearchTerm.toLowerCase())
      );

  const filteredPosts = allPosts.filter(p =>
    p?.title?.toLowerCase().includes(contentSearchTerm.toLowerCase()) ||
    p?.content?.toLowerCase().includes(contentSearchTerm.toLowerCase())
  );

  const filteredComments = allComments.filter(c =>
    c?.content?.toLowerCase().includes(contentSearchTerm.toLowerCase())
  );

  // Loading state
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

  // Access denied state
  if (!user?.is_admin) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-red-600 mb-4">Access Denied</h1>
          <p className="text-gray-600">You need admin privileges to access this page.</p>
          <p className="text-sm text-gray-500 mt-2">Current user: {user?.username || "Not logged in"}</p>
          <p className="text-sm text-gray-500">Admin status: {user?.is_admin ? "Yes" : "No"}</p>
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
          API: {API_URL} | User: {user.username} | Admin: {user.is_admin ? "Yes" : "No"}
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
              className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
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

      {/* Loading indicator */}
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
              className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors flex items-center gap-2"
            >
              ➕ Create User
            </button>
            <button
              onClick={() => setShowPostForm(true)}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
            >
              ➕ Create Post
            </button>
            <ExportCSV data={users} filename="users_report.csv" />
            <button
              onClick={fetchOverviewData}
              disabled={loading}
              className="bg-gray-600 text-white px-4 py-2 rounded-lg hover:bg-gray-700 transition-colors flex items-center gap-2 disabled:opacity-50"
            >
              🔄 Refresh Data
            </button>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="bg-blue-50 p-6 rounded-lg border border-blue-200 hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-blue-600 text-sm font-medium">Total Users</p>
                  <p className="text-2xl font-bold text-blue-900">{stats.users || stats.total_users || 0}</p>
                  {stats.blocked_users > 0 && (
                    <p className="text-xs text-red-600">{stats.blocked_users} blocked</p>
                  )}
                </div>
                <div className="text-blue-500 text-2xl">👥</div>
              </div>
            </div>

            <div className="bg-green-50 p-6 rounded-lg border border-green-200 hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-green-600 text-sm font-medium">Total Posts</p>
                  <p className="text-2xl font-bold text-green-900">{stats.posts || stats.total_posts || 0}</p>
                  {stats.recent_posts > 0 && (
                    <p className="text-xs text-green-600">{stats.recent_posts} this month</p>
                  )}
                </div>
                <div className="text-green-500 text-2xl">📝</div>
              </div>
            </div>

            <div className="bg-purple-50 p-6 rounded-lg border border-purple-200 hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-purple-600 text-sm font-medium">Total Comments</p>
                  <p className="text-2xl font-bold text-purple-900">{stats.comments || stats.total_comments || 0}</p>
                  {stats.recent_comments > 0 && (
                    <p className="text-xs text-purple-600">{stats.recent_comments} this month</p>
                  )}
                </div>
                <div className="text-purple-500 text-2xl">💬</div>
              </div>
            </div>

            <div className="bg-red-50 p-6 rounded-lg border border-red-200 hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-red-600 text-sm font-medium">Flagged Content</p>
                  <p className="text-2xl font-bold text-red-900">{stats.flagged || 0}</p>
                  <div className="text-xs text-gray-600">
                    Posts: {stats.flagged_posts || 0} | Comments: {stats.flagged_comments || 0}
                  </div>
                </div>
                <div className="text-red-500 text-2xl">🚩</div>
              </div>
            </div>
          </div>

          {/* Activity Chart */}
          {chartData && (
            <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
              <h3 className="text-lg font-semibold mb-4">📊 Weekly Activity Trends</h3>
              <div className="h-80">
                <Bar 
                  data={chartData} 
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
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
                        beginAtZero: true,
                        ticks: {
                          stepSize: 1
                        }
                      }
                    }
                  }}
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Users Tab */}
      {activeTab === "users" && (
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold">👥 User Management</h3>
            <button
              onClick={fetchAllUsers}
              disabled={loading}
              className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700 disabled:opacity-50"
            >
              🔄 Refresh Users
            </button>
          </div>

          {/* User Search */}
          <div className="relative">
            <input
              type="text"
              placeholder="Search users by username or email..."
              value={userSearchTerm}
              onChange={(e) => setUserSearchTerm(e.target.value)}
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
            {searchingUsers && (
              <div className="absolute right-3 top-3">
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-indigo-600"></div>
              </div>
            )}
          </div>

          {/* Users List */}
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="px-6 py-3 bg-gray-50 border-b">
              <h4 className="font-medium text-gray-900">
                Users ({filteredUsers.length})
              </h4>
            </div>
            <div className="divide-y divide-gray-200">
              {filteredUsers.length === 0 ? (
                <div className="px-6 py-8 text-center text-gray-500">
                  {loading ? "Loading users..." : "No users found"}
                </div>
              ) : (
                filteredUsers.map((userItem) => (
                  <div key={userItem.id} className="px-6 py-4 hover:bg-gray-50">
                    <div className="flex items-center justify-between">
                      <div>
                        <h5 className="font-medium text-gray-900">{userItem.username}</h5>
                        <p className="text-sm text-gray-600">{userItem.email}</p>
                        <div className="flex gap-2 mt-1">
                          {userItem.is_admin && (
                            <span className="px-2 py-1 text-xs bg-purple-100 text-purple-800 rounded">
                              Admin
                            </span>
                          )}
                          {userItem.is_blocked && (
                            <span className="px-2 py-1 text-xs bg-red-100 text-red-800 rounded">
                              Blocked
                            </span>
                          )}
                          <span className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded">
                            Posts: {userItem.post_count || 0}
                          </span>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleUserAction(userItem.id, userItem.is_blocked ? "unblock" : "block")}
                          className={`px-3 py-1 text-xs rounded ${
                            userItem.is_blocked
                              ? "bg-green-100 text-green-800 hover:bg-green-200"
                              : "bg-red-100 text-red-800 hover:bg-red-200"
                          }`}
                        >
                          {userItem.is_blocked ? "Unblock" : "Block"}
                        </button>
                        <button
                          onClick={() => handleUserAction(userItem.id, "delete")}
                          className="px-3 py-1 text-xs bg-red-100 text-red-800 rounded hover:bg-red-200"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* Content Tab */}
      {activeTab === "content" && (
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold">📝 Content Management</h3>
            <button
              onClick={fetchAllContent}
              disabled={loading}
              className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700 disabled:opacity-50"
            >
              🔄 Refresh Content
            </button>
          </div>

          {/* Content Search */}
          <div className="relative">
            <input
              type="text"
              placeholder="Search posts and comments..."
              value={contentSearchTerm}
              onChange={(e) => setContentSearchTerm(e.target.value)}
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>

          {/* Posts Section */}
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="px-6 py-3 bg-gray-50 border-b">
              <h4 className="font-medium text-gray-900">
                Posts ({filteredPosts.length})
              </h4>
            </div>
            <div className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
              {filteredPosts.length === 0 ? (
                <div className="px-6 py-8 text-center text-gray-500">
                  {loading ? "Loading posts..." : "No posts found"}
                </div>
              ) : (
                filteredPosts.slice(0, 10).map((post) => (
                  <div key={post.id} className="px-6 py-4 hover:bg-gray-50">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h5 className="font-medium text-gray-900 truncate">{post.title}</h5>
                        <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                          {post.content?.substring(0, 100)}...
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                          By {post.author?.username || "Unknown"} • {new Date(post.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      <div className="flex gap-2 ml-4">
                        <button
                          onClick={() => handleContentAction("post", post.id, "flag")}
                          className="px-3 py-1 text-xs bg-yellow-100 text-yellow-800 rounded hover:bg-yellow-200"
                        >
                          Flag
                        </button>
                        <button
                          onClick={() => handleContentAction("post", post.id, "delete")}
                          className="px-3 py-1 text-xs bg-red-100 text-red-800 rounded hover:bg-red-200"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Comments Section */}
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="px-6 py-3 bg-gray-50 border-b">
              <h4 className="font-medium text-gray-900">
                Comments ({filteredComments.length})
              </h4>
            </div>
            <div className="divide-y divide-gray-200 max-h-96 overflow-y-auto">
              {filteredComments.length === 0 ? (
                <div className="px-6 py-8 text-center text-gray-500">
                  {loading ? "Loading comments..." : "No comments found"}
                </div>
              ) : (
                filteredComments.slice(0, 10).map((comment) => (
                  <div key={comment.id} className="px-6 py-4 hover:bg-gray-50">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <p className="text-sm text-gray-900 line-clamp-3">
                          {comment.content}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                          By {comment.author?.username || "Unknown"} • {new Date(comment.created_at).toLocaleDateString()}
                          {comment.post_title && ` • On "${comment.post_title}"`}
                        </p>
                      </div>
                      <div className="flex gap-2 ml-4">
                        <button
                          onClick={() => handleContentAction("comment", comment.id, "flag")}
                          className="px-3 py-1 text-xs bg-yellow-100 text-yellow-800 rounded hover:bg-yellow-200"
                        >
                          Flag
                        </button>
                        <button
                          onClick={() => handleContentAction("comment", comment.id, "delete")}
                          className="px-3 py-1 text-xs bg-red-100 text-red-800 rounded hover:bg-red-200"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* Flagged Tab */}
      {activeTab === "flagged" && (
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold">🚩 Flagged Content</h3>
            <button
              onClick={fetchFlaggedContent}
              disabled={loading}
              className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700 disabled:opacity-50"
            >
              🔄 Refresh Flagged Content
            </button>
          </div>

          {/* Flagged Posts */}
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="px-6 py-3 bg-red-50 border-b border-red-200">
              <h4 className="font-medium text-red-900">
                🚩 Flagged Posts ({flaggedPosts.length})
              </h4>
            </div>
            <div className="divide-y divide-gray-200">
              {flaggedPosts.length === 0 ? (
                <div className="px-6 py-8 text-center text-gray-500">
                  No flagged posts found
                </div>
              ) : (
                flaggedPosts.map((post) => (
                  <div key={post.id} className="px-6 py-4 hover:bg-gray-50">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h5 className="font-medium text-gray-900">{post.title}</h5>
                        <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                          {post.content?.substring(0, 150)}...
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                          By {post.author?.username || "Unknown"} • Flagged on {new Date(post.flagged_at || post.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      <div className="flex gap-2 ml-4">
                        <button
                          onClick={() => handleContentAction("post", post.id, "approve")}
                          className="px-3 py-1 text-xs bg-green-100 text-green-800 rounded hover:bg-green-200"
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => handleContentAction("post", post.id, "delete")}
                          className="px-3 py-1 text-xs bg-red-100 text-red-800 rounded hover:bg-red-200"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Flagged Comments */}
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="px-6 py-3 bg-red-50 border-b border-red-200">
              <h4 className="font-medium text-red-900">
                🚩 Flagged Comments ({flaggedComments.length})
              </h4>
            </div>
            <div className="divide-y divide-gray-200">
              {flaggedComments.length === 0 ? (
                <div className="px-6 py-8 text-center text-gray-500">
                  No flagged comments found
                </div>
              ) : (
                flaggedComments.map((comment) => (
                  <div key={comment.id} className="px-6 py-4 hover:bg-gray-50">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <p className="text-sm text-gray-900">{comment.content}</p>
                        <p className="text-xs text-gray-500 mt-1">
                          By {comment.author?.username || "Unknown"} • Flagged on {new Date(comment.flagged_at || comment.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      <div className="flex gap-2 ml-4">
                        <button
                          onClick={() => handleContentAction("comment", comment.id, "approve")}
                          className="px-3 py-1 text-xs bg-green-100 text-green-800 rounded hover:bg-green-200"
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => handleContentAction("comment", comment.id, "delete")}
                          className="px-3 py-1 text-xs bg-red-100 text-red-800 rounded hover:bg-red-200"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
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

      {/* Debug Panel (Development Only) */}
      {import.meta.env.DEV && (
        <div className="fixed bottom-4 right-4 bg-gray-800 text-white p-4 rounded-lg text-xs max-w-sm z-50">
          <h4 className="font-bold mb-2">🔍 Debug Info</h4>
          <div className="space-y-1">
            <div>API: {API_URL}</div>
            <div>User: {user?.username}</div>
            <div>Admin: {user?.is_admin ? "✅" : "❌"}</div>
            <div>Token: {token ? "✅ Present" : "❌ Missing"}</div>
            <div>Active Tab: {activeTab}</div>
            <div>Loading: {loading ? "🔄" : "✅"}</div>
            <div>Stats: U:{stats.users} P:{stats.posts} C:{stats.comments}</div>
          </div>
          <button
            onClick={() => console.log({ user, token, stats, API_URL })}
            className="mt-2 text-xs bg-gray-700 px-2 py-1 rounded hover:bg-gray-600"
          >
            Log Debug Data
          </button>
        </div>
      )}
    </div>
  );
};

export default AdminDashboard;