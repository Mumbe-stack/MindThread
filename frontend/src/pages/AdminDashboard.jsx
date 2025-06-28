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

const VITE_API_URL = import.meta.env.VITE_API_URL || "https://mindthread-1.onrender.com";

const AdminDashboard = () => {
  const { user, token, authenticatedRequest } = useAuth();
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
      const statsResponse = await makeAuthenticatedRequest(`${VITE_API_URL}/api/admin/stats`);
      const statsData = await handleApiResponse(statsResponse, "Failed to fetch stats");
      
      setStats(statsData);

      try {
        const trendsResponse = await makeAuthenticatedRequest(`${VITE_API_URL}/api/admin/activity-trends`);
        
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
      toast.error(`Failed to load dashboard data: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const fetchAllUsers = async () => {
    if (!token || !user?.is_admin) return;
    
    setLoading(true);
    try {
      const response = await makeAuthenticatedRequest(`${VITE_API_URL}/api/users`);
      const data = await handleApiResponse(response, "Failed to fetch users");
      
      const usersArray = Array.isArray(data) ? data : (data.users || []);
      setUsers(usersArray);
      
    } catch (err) {
      toast.error(`Failed to load users: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const searchUsers = async () => {
    if (!userSearchTerm.trim() || !token) return;
    
    setSearchingUsers(true);
    try {
      const response = await makeAuthenticatedRequest(
        `${VITE_API_URL}/api/admin/users/search?q=${encodeURIComponent(userSearchTerm)}`
      );
      
      if (response.ok) {
        const data = await handleApiResponse(response, "User search failed");
        setUserSearchResults(Array.isArray(data) ? data : (data.users || []));
      } else {
        const filtered = users.filter(u => 
          u.username?.toLowerCase().includes(userSearchTerm.toLowerCase()) ||
          u.email?.toLowerCase().includes(userSearchTerm.toLowerCase())
        );
        setUserSearchResults(filtered);
      }
    } catch (err) {
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
      let postsData = [];
      try {
        const adminPostsRes = await makeAuthenticatedRequest(`${VITE_API_URL}/api/admin/posts`);
        if (adminPostsRes.ok) {
          const data = await handleApiResponse(adminPostsRes, "Failed to fetch admin posts");
          postsData = Array.isArray(data) ? data : (data.posts || []);
        } else {
          const postsRes = await makeAuthenticatedRequest(`${VITE_API_URL}/api/posts`);
          const data = await handleApiResponse(postsRes, "Failed to fetch posts");
          postsData = Array.isArray(data) ? data : (data.posts || []);
        }
      } catch (err) {
        toast.error(`Failed to load posts: ${err.message}`);
      }

      let commentsData = [];
      try {
        const adminCommentsEndpoints = [
          `${VITE_API_URL}/api/admin/comments`,
          `${VITE_API_URL}/api/admin/all-comments`,
          `${VITE_API_URL}/api/comments/all`
        ];

        let commentsFound = false;
        for (const endpoint of adminCommentsEndpoints) {
          try {
            const res = await makeAuthenticatedRequest(endpoint);
            if (res.ok) {
              const data = await handleApiResponse(res, "Failed to fetch comments");
              commentsData = Array.isArray(data) ? data : (data.comments || []);
              commentsFound = true;
              break;
            }
          } catch (err) {
            continue;
          }
        }

        if (!commentsFound && postsData.length > 0) {
          const allComments = [];
          const postsToCheck = postsData.slice(0, 20);
          
          for (const post of postsToCheck) {
            try {
              const postCommentsRes = await makeAuthenticatedRequest(
                `${VITE_API_URL}/api/posts/${post.id}/comments`
              );
              if (postCommentsRes.ok) {
                const postComments = await handleApiResponse(postCommentsRes, "Failed to fetch post comments");
                const comments = Array.isArray(postComments) ? postComments : (postComments.comments || []);
                allComments.push(...comments);
              }
            } catch (err) {
              continue;
            }
          }
          
          commentsData = allComments;
        }

        if (!commentsFound && commentsData.length === 0) {
          const queryEndpoints = [
            `${VITE_API_URL}/api/comments?all=true`,
            `${VITE_API_URL}/api/comments?admin=true`,
            `${VITE_API_URL}/api/comments?limit=100`
          ];

          for (const endpoint of queryEndpoints) {
            try {
              const res = await makeAuthenticatedRequest(endpoint);
              if (res.ok) {
                const data = await handleApiResponse(res, "Failed to fetch comments");
                commentsData = Array.isArray(data) ? data : (data.comments || []);
                break;
              }
            } catch (err) {
              continue;
            }
          }
        }

      } catch (err) {
        toast.error(`Failed to load comments: ${err.message}`);
      }

      setAllPosts(postsData);
      setAllComments(commentsData);

      const message = `Loaded ${postsData.length} posts and ${commentsData.length} comments`;
      toast.success(message);
      
    } catch (err) {
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

      try {
        const postsRes = await makeAuthenticatedRequest(`${VITE_API_URL}/api/admin/flagged/posts`);
        if (postsRes.ok) {
          const data = await handleApiResponse(postsRes, "Failed to fetch flagged posts");
          flaggedPostsData = Array.isArray(data) ? data : (data.posts || []);
        }
      } catch (err) {
        // Endpoint not available
      }

      try {
        const commentsRes = await makeAuthenticatedRequest(`${VITE_API_URL}/api/admin/flagged/comments`);
        if (commentsRes.ok) {
          const data = await handleApiResponse(commentsRes, "Failed to fetch flagged comments");
          flaggedCommentsData = Array.isArray(data) ? data : (data.comments || []);
        }
      } catch (err) {
        // Endpoint not available
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
    if (!token || !user?.is_admin) return;
    
    try {
      let endpoint = "";
      let method = "PATCH";
      let body = null;

      switch (action) {
        case "block":
          endpoint = `${VITE_API_URL}/api/admin/users/${userId}/block`;
          body = JSON.stringify({ is_blocked: true });
          break;
        case "unblock":
          endpoint = `${VITE_API_URL}/api/admin/users/${userId}/block`;
          body = JSON.stringify({ is_blocked: false });
          break;
        case "delete":
          if (!window.confirm("Are you sure you want to delete this user? This action cannot be undone.")) {
            return;
          }
          endpoint = `${VITE_API_URL}/api/admin/users/${userId}`;
          method = "DELETE";
          break;
        case "make_admin":
          endpoint = `${VITE_API_URL}/api/admin/users/${userId}/admin`;
          body = JSON.stringify({});
          break;
        case "remove_admin":
          endpoint = `${VITE_API_URL}/api/admin/users/${userId}/admin`;
          body = JSON.stringify({});
          break;
      }

      const response = await makeAuthenticatedRequest(endpoint, {
        method,
        body
      });

      await handleApiResponse(response, `Failed to ${action} user`);
      toast.success(`User ${action} successful`);
      
      await fetchAllUsers();
      await fetchOverviewData();
      
    } catch (err) {
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
          endpoint = `${VITE_API_URL}/api/admin/${type}s/${id}/approve`;
          body = JSON.stringify({ is_approved: true });
          break;
        case "reject":
          endpoint = `${VITE_API_URL}/api/admin/${type}s/${id}/approve`;
          body = JSON.stringify({ is_approved: false });
          break;
        case "flag":
        case "unflag":
          endpoint = `${VITE_API_URL}/api/admin/${type}s/${id}/flag`;
          body = JSON.stringify({});
          break;
        case "delete":
          if (!window.confirm(`Are you sure you want to delete this ${type}? This action cannot be undone.`)) {
            return;
          }
          endpoint = `${VITE_API_URL}/api/admin/${type}s/${id}`;
          method = "DELETE";
          break;
      }

      const response = await makeAuthenticatedRequest(endpoint, {
        method,
        body
      });

      await handleApiResponse(response, `Failed to ${action} ${type}`);
      toast.success(`${type} ${action} successful`);
      
      await fetchFlaggedContent();
      await fetchAllContent();
      await fetchOverviewData();
      
    } catch (err) {
      toast.error(err.message);
    }
  };

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

  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-screen px-4">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (!user?.is_admin) {
    return (
      <div className="flex items-center justify-center min-h-screen px-4">
        <div className="text-center">
          <h1 className="text-xl sm:text-2xl font-bold text-red-600 mb-4">Access Denied</h1>
          <p className="text-gray-600 text-sm sm:text-base">You need admin privileges to access this page.</p>
          <p className="text-xs sm:text-sm text-gray-500 mt-2">Current user: {user?.username || "Not logged in"}</p>
          <p className="text-xs sm:text-sm text-gray-500">Admin status: {user?.is_admin ? "Yes" : "No"}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto p-3 sm:p-4 lg:p-6">
      {/* Header - Responsive text sizes */}
      <div className="mb-6 sm:mb-8">
        <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-gray-900 mb-2">🛡️ Admin Dashboard</h1>
        <p className="text-sm sm:text-base text-gray-600">Manage users, content, and monitor platform activity</p>
      </div>

      {/* Navigation Tabs - Responsive with horizontal scroll on mobile */}
      <div className="border-b border-gray-200 mb-4 sm:mb-6">
        <nav className="-mb-px flex space-x-4 sm:space-x-8 overflow-x-auto scrollbar-hide">
          {[
            { id: "overview", label: "📊 Overview", shortLabel: "Overview" },
            { id: "users", label: "👥 Users", shortLabel: "Users" },
            { id: "content", label: "📝 Content", shortLabel: "Content" },
            { id: "flagged", label: "🚩 Flagged", shortLabel: "Flagged" }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-2 px-1 border-b-2 font-medium text-sm whitespace-nowrap transition-colors ${
                activeTab === tab.id
                  ? "border-indigo-500 text-indigo-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
            >
              <span className="hidden sm:inline">{tab.label}</span>
              <span className="sm:hidden">{tab.shortLabel}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Loading Indicator */}
      {loading && (
        <div className="flex justify-center items-center py-6 sm:py-8">
          <div className="animate-spin rounded-full h-6 w-6 sm:h-8 sm:w-8 border-b-2 border-indigo-600"></div>
          <span className="ml-2 text-sm sm:text-base text-gray-600">Loading...</span>
        </div>
      )}

      {/* Overview Tab */}
      {activeTab === "overview" && (
        <div className="space-y-4 sm:space-y-6">
          {/* Action Buttons - Responsive grid */}
          <div className="grid grid-cols-2 sm:flex sm:flex-wrap gap-2 sm:gap-4">
            <button
              onClick={() => setShowUserForm(true)}
              className="bg-indigo-600 text-white px-3 sm:px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors flex items-center justify-center gap-1 sm:gap-2 text-sm sm:text-base"
            >
              <span className="hidden sm:inline">➕</span>
              <span className="sm:hidden">+</span>
              Create User
            </button>
            <button
              onClick={() => setShowPostForm(true)}
              className="bg-blue-600 text-white px-3 sm:px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors flex items-center justify-center gap-1 sm:gap-2 text-sm sm:text-base"
            >
              <span className="hidden sm:inline">➕</span>
              <span className="sm:hidden">+</span>
              Create Post
            </button>
            <div className="col-span-2 sm:col-span-1">
              <ExportCSV data={users} filename="users_report.csv" />
            </div>
            <button
              onClick={fetchOverviewData}
              disabled={loading}
              className="bg-gray-600 text-white px-3 sm:px-4 py-2 rounded-lg hover:bg-gray-700 transition-colors flex items-center justify-center gap-1 sm:gap-2 disabled:opacity-50 text-sm sm:text-base"
            >
              🔄 Refresh
            </button>
          </div>

          {/* Stats Grid - Fully responsive */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 lg:gap-6">
            <div className="bg-blue-50 p-4 sm:p-6 rounded-lg border border-blue-200 hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-blue-600 text-xs sm:text-sm font-medium">Total Users</p>
                  <p className="text-xl sm:text-2xl font-bold text-blue-900">{stats.users || 0}</p>
                </div>
                <div className="text-blue-500 text-xl sm:text-2xl">👥</div>
              </div>
            </div>

            <div className="bg-green-50 p-4 sm:p-6 rounded-lg border border-green-200 hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-green-600 text-xs sm:text-sm font-medium">Total Posts</p>
                  <p className="text-xl sm:text-2xl font-bold text-green-900">{stats.posts || 0}</p>
                </div>
                <div className="text-green-500 text-xl sm:text-2xl">📝</div>
              </div>
            </div>

            <div className="bg-purple-50 p-4 sm:p-6 rounded-lg border border-purple-200 hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-purple-600 text-xs sm:text-sm font-medium">Total Comments</p>
                  <p className="text-xl sm:text-2xl font-bold text-purple-900">{stats.comments || 0}</p>
                </div>
                <div className="text-purple-500 text-xl sm:text-2xl">💬</div>
              </div>
            </div>

            <div className="bg-red-50 p-4 sm:p-6 rounded-lg border border-red-200 hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-red-600 text-xs sm:text-sm font-medium">Flagged Content</p>
                  <p className="text-xl sm:text-2xl font-bold text-red-900">{stats.flagged || 0}</p>
                </div>
                <div className="text-red-500 text-xl sm:text-2xl">🚩</div>
              </div>
            </div>
          </div>

          {/* Chart - Responsive height */}
          {chartData && (
            <div className="bg-white p-4 sm:p-6 rounded-lg shadow border border-gray-200">
              <h3 className="text-base sm:text-lg font-semibold mb-4">📊 Weekly Activity Trends</h3>
              <div className="h-60 sm:h-80">
                <Bar 
                  data={chartData} 
                  options={{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                      legend: {
                        position: 'top',
                        labels: {
                          boxWidth: 12,
                          font: {
                            size: window.innerWidth < 640 ? 10 : 12
                          }
                        }
                      },
                      title: {
                        display: true,
                        text: 'Platform Activity (Last 7 Days)',
                        font: {
                          size: window.innerWidth < 640 ? 12 : 16
                        }
                      }
                    },
                    scales: {
                      y: {
                        beginAtZero: true,
                        ticks: {
                          stepSize: 1,
                          font: {
                            size: window.innerWidth < 640 ? 10 : 12
                          }
                        }
                      },
                      x: {
                        ticks: {
                          font: {
                            size: window.innerWidth < 640 ? 10 : 12
                          }
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
        <div className="space-y-4 sm:space-y-6">
          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
            <h3 className="text-base sm:text-lg font-semibold">👥 User Management</h3>
            <button
              onClick={fetchAllUsers}
              disabled={loading}
              className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700 disabled:opacity-50 text-sm sm:text-base"
            >
              🔄 Refresh Users
            </button>
          </div>

          {/* Search Input */}
          <div className="relative">
            <input
              type="text"
              placeholder="Search users by username or email..."
              value={userSearchTerm}
              onChange={(e) => setUserSearchTerm(e.target.value)}
              className="w-full p-3 text-sm sm:text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
            {searchingUsers && (
              <div className="absolute right-3 top-3">
                <div className="animate-spin rounded-full h-4 w-4 sm:h-5 sm:w-5 border-b-2 border-indigo-600"></div>
              </div>
            )}
          </div>

          {/* Users List - Responsive cards */}
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="px-4 sm:px-6 py-3 bg-gray-50 border-b">
              <h4 className="font-medium text-gray-900 text-sm sm:text-base">
                Users ({filteredUsers.length})
              </h4>
            </div>
            <div className="divide-y divide-gray-200">
              {filteredUsers.length === 0 ? (
                <div className="px-4 sm:px-6 py-6 sm:py-8 text-center text-gray-500 text-sm sm:text-base">
                  {loading ? "Loading users..." : "No users found"}
                </div>
              ) : (
                filteredUsers.map((userItem) => (
                  <div key={userItem.id} className="px-4 sm:px-6 py-4 hover:bg-gray-50">
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <h5 className="font-medium text-gray-900 text-sm sm:text-base truncate">{userItem.username}</h5>
                        <p className="text-xs sm:text-sm text-gray-600 truncate">{userItem.email}</p>
                        <div className="flex gap-2 mt-2">
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
                        </div>
                      </div>
                      <div className="flex gap-2 flex-shrink-0">
                        <button
                          onClick={() => handleUserAction(userItem.id, userItem.is_blocked ? "unblock" : "block")}
                          className={`px-2 sm:px-3 py-1 text-xs rounded transition-colors ${
                            userItem.is_blocked
                              ? "bg-green-100 text-green-800 hover:bg-green-200"
                              : "bg-red-100 text-red-800 hover:bg-red-200"
                          }`}
                        >
                          {userItem.is_blocked ? "Unblock" : "Block"}
                        </button>
                        <button
                          onClick={() => handleUserAction(userItem.id, "delete")}
                          className="px-2 sm:px-3 py-1 text-xs bg-red-100 text-red-800 rounded hover:bg-red-200 transition-colors"
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
        <div className="space-y-4 sm:space-y-6">
          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
            <h3 className="text-base sm:text-lg font-semibold">📝 Content Management</h3>
            <button
              onClick={fetchAllContent}
              disabled={loading}
              className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700 disabled:opacity-50 text-sm sm:text-base"
            >
              🔄 Refresh Content
            </button>
          </div>

          {/* Search Input */}
          <div className="relative">
            <input
              type="text"
              placeholder="Search posts and comments..."
              value={contentSearchTerm}
              onChange={(e) => setContentSearchTerm(e.target.value)}
              className="w-full p-3 text-sm sm:text-base border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>

          {/* Posts List */}
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="px-4 sm:px-6 py-3 bg-gray-50 border-b">
              <h4 className="font-medium text-gray-900 text-sm sm:text-base">
                Posts ({filteredPosts.length})
              </h4>
            </div>
            <div className="divide-y divide-gray-200 max-h-80 sm:max-h-96 overflow-y-auto">
              {filteredPosts.length === 0 ? (
                <div className="px-4 sm:px-6 py-6 sm:py-8 text-center text-gray-500 text-sm sm:text-base">
                  {loading ? "Loading posts..." : "No posts found"}
                </div>
              ) : (
                filteredPosts.slice(0, 10).map((post) => (
                  <div key={post.id} className="px-4 sm:px-6 py-4 hover:bg-gray-50">
                    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <h5 className="font-medium text-gray-900 text-sm sm:text-base line-clamp-1">{post.title}</h5>
                        <p className="text-xs sm:text-sm text-gray-600 mt-1 line-clamp-2">
                          {post.content?.substring(0, 100)}...
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                          By {post.author?.username || "Unknown"} • {new Date(post.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      <div className="flex gap-2 flex-shrink-0">
                        <button
                          onClick={() => handleContentAction("post", post.id, post.is_flagged ? "unflag" : "flag")}
                          className={`px-2 sm:px-3 py-1 text-xs rounded transition-colors ${
                            post.is_flagged 
                              ? "bg-red-100 text-red-800 hover:bg-red-200" 
                              : "bg-yellow-100 text-yellow-800 hover:bg-yellow-200"
                          }`}
                        >
                          {post.is_flagged ? "Unflag" : "Flag"}
                        </button>
                        <button
                          onClick={() => handleContentAction("post", post.id, "delete")}
                          className="px-2 sm:px-3 py-1 text-xs bg-red-100 text-red-800 rounded hover:bg-red-200 transition-colors"
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

          {/* Comments List */}
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="px-4 sm:px-6 py-3 bg-gray-50 border-b">
              <h4 className="font-medium text-gray-900 text-sm sm:text-base">
                Comments ({filteredComments.length})
              </h4>
            </div>
            <div className="divide-y divide-gray-200 max-h-80 sm:max-h-96 overflow-y-auto">
              {filteredComments.length === 0 ? (
                <div className="px-4 sm:px-6 py-6 sm:py-8 text-center text-gray-500 text-sm sm:text-base">
                  {loading ? "Loading comments..." : "No comments found"}
                </div>
              ) : (
                filteredComments.slice(0, 10).map((comment) => (
                  <div key={comment.id} className="px-4 sm:px-6 py-4 hover:bg-gray-50">
                    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <p className="text-xs sm:text-sm text-gray-900 line-clamp-3">
                          {comment.content}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                          By {comment.author?.username || "Unknown"} • {new Date(comment.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      <div className="flex gap-2 flex-shrink-0">
                        <button
                          onClick={() => handleContentAction("comment", comment.id, comment.is_flagged ? "unflag" : "flag")}
                          className={`px-2 sm:px-3 py-1 text-xs rounded transition-colors ${
                            comment.is_flagged 
                              ? "bg-red-100 text-red-800 hover:bg-red-200" 
                              : "bg-yellow-100 text-yellow-800 hover:bg-yellow-200"
                          }`}
                        >
                          {comment.is_flagged ? "Unflag" : "Flag"}
                        </button>
                        <button
                          onClick={() => handleContentAction("comment", comment.id, "delete")}
                          className="px-2 sm:px-3 py-1 text-xs bg-red-100 text-red-800 rounded hover:bg-red-200 transition-colors"
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
        <div className="space-y-4 sm:space-y-6">
          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">
            <h3 className="text-base sm:text-lg font-semibold">🚩 Flagged Content</h3>
            <button
              onClick={fetchFlaggedContent}
              disabled={loading}
              className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700 disabled:opacity-50 text-sm sm:text-base"
            >
              🔄 Refresh Flagged Content
            </button>
          </div>

          {/* Flagged Posts */}
          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="px-4 sm:px-6 py-3 bg-red-50 border-b border-red-200">
              <h4 className="font-medium text-red-900 text-sm sm:text-base">
                🚩 Flagged Posts ({flaggedPosts.length})
              </h4>
            </div>
            <div className="divide-y divide-gray-200">
              {flaggedPosts.length === 0 ? (
                <div className="px-4 sm:px-6 py-6 sm:py-8 text-center text-gray-500 text-sm sm:text-base">
                  No flagged posts found
                </div>
              ) : (
                flaggedPosts.map((post) => (
                  <div key={post.id} className="px-4 sm:px-6 py-4 hover:bg-gray-50">
                    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <h5 className="font-medium text-gray-900 text-sm sm:text-base line-clamp-1">{post.title}</h5>
                        <p className="text-xs sm:text-sm text-gray-600 mt-1 line-clamp-2">
                          {post.content?.substring(0, 150)}...
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                          By {post.author?.username || "Unknown"} • Flagged on {new Date(post.flagged_at || post.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      <div className="flex gap-2 flex-shrink-0">
                        <button
                          onClick={() => handleContentAction("post", post.id, "approve")}
                          className="px-2 sm:px-3 py-1 text-xs bg-green-100 text-green-800 rounded hover:bg-green-200 transition-colors"
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => handleContentAction("post", post.id, "delete")}
                          className="px-2 sm:px-3 py-1 text-xs bg-red-100 text-red-800 rounded hover:bg-red-200 transition-colors"
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
            <div className="px-4 sm:px-6 py-3 bg-red-50 border-b border-red-200">
              <h4 className="font-medium text-red-900 text-sm sm:text-base">
                🚩 Flagged Comments ({flaggedComments.length})
              </h4>
            </div>
            <div className="divide-y divide-gray-200">
              {flaggedComments.length === 0 ? (
                <div className="px-4 sm:px-6 py-6 sm:py-8 text-center text-gray-500 text-sm sm:text-base">
                  No flagged comments found
                </div>
              ) : (
                flaggedComments.map((comment) => (
                  <div key={comment.id} className="px-4 sm:px-6 py-4 hover:bg-gray-50">
                    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <p className="text-xs sm:text-sm text-gray-900 line-clamp-3">{comment.content}</p>
                        <p className="text-xs text-gray-500 mt-1">
                          By {comment.author?.username || "Unknown"} • Flagged on {new Date(comment.flagged_at || comment.created_at).toLocaleDateString()}
                        </p>
                      </div>
                      <div className="flex gap-2 flex-shrink-0">
                        <button
                          onClick={() => handleContentAction("comment", comment.id, "approve")}
                          className="px-2 sm:px-3 py-1 text-xs bg-green-100 text-green-800 rounded hover:bg-green-200 transition-colors"
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => handleContentAction("comment", comment.id, "delete")}
                          className="px-2 sm:px-3 py-1 text-xs bg-red-100 text-red-800 rounded hover:bg-red-200 transition-colors"
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
    </div>
  );
};

export default AdminDashboard;