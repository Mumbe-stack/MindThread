import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import toast from "react-hot-toast";


const VITE_API_URL = import.meta.env.VITE_API_URL || "https://mindthread-1.onrender.com";

const Users = () => {
  const { user, token, isAuthenticated, isAdmin } = useAuth();
  const navigate = useNavigate();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [filteredUsers, setFilteredUsers] = useState([]);
  const [actionLoading, setActionLoading] = useState({});


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
    if (!isAuthenticated) {
      toast.error("Please log in to view users");
      navigate("/login");
      return;
    }

    if (!isAdmin) {
      toast.error("Admin access required");
      navigate("/");
      return;
    }

    fetchUsers();
  }, [isAuthenticated, isAdmin, navigate, token]);


  useEffect(() => {
    if (!searchTerm.trim()) {
      setFilteredUsers(users);
    } else {
      const filtered = users.filter(user =>
        user.username?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        user.email?.toLowerCase().includes(searchTerm.toLowerCase())
      );
      setFilteredUsers(filtered);
    }
  }, [users, searchTerm]);

  const fetchUsers = async () => {
    if (!token) return;
    
    setLoading(true);
    try {
      console.log("Fetching users from:", `${VITE_API_URL}/api/users`);
      
      const response = await makeAuthenticatedRequest(`${VITE_API_URL}/api/users`);
      
      if (!response.ok) {
        if (response.status === 401) {
          toast.error("Authentication failed. Please log in again.");
          navigate("/login");
          return;
        } else if (response.status === 403) {
          toast.error("Admin access required");
          navigate("/");
          return;
        }
        throw new Error(`Failed to fetch users (${response.status})`);
      }

      const data = await response.json();
      console.log("Users data received:", data);
      
 
      const usersArray = Array.isArray(data) ? data : (data.users || []);
      setUsers(usersArray);
      toast.success(`Loaded ${usersArray.length} users`);
      
    } catch (error) {
      console.error("Failed to load users:", error);
      toast.error(`Failed to load users: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const toggleBlock = async (userId, shouldBlock) => {
    if (!token || !isAdmin) {
      toast.error("Admin access required");
      return;
    }

    
    if (userId === user?.id) {
      toast.error("You cannot block/unblock yourself");
      return;
    }

    const action = shouldBlock ? "block" : "unblock";
    setActionLoading(prev => ({ ...prev, [userId]: action }));

    try {
      const endpoint = `${VITE_API_URL}/api/users/${userId}/block`;
      console.log(`${action}ing user:`, endpoint);

      const response = await makeAuthenticatedRequest(endpoint, {
        method: "PATCH",
        body: JSON.stringify({ is_blocked: shouldBlock })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `Failed to ${action} user`);
      }

     
      const updatedUsers = users.map((u) =>
        u.id === userId ? { ...u, is_blocked: shouldBlock } : u
      );
      setUsers(updatedUsers);
      
      toast.success(`User ${action}ed successfully`);
      
    } catch (error) {
      console.error(`Failed to ${action} user:`, error);
      toast.error(`Failed to ${action} user: ${error.message}`);
    } finally {
      setActionLoading(prev => ({ ...prev, [userId]: false }));
    }
  };

  const deleteUser = async (userId, username) => {
    if (!token || !isAdmin) {
      toast.error("Admin access required");
      return;
    }

   
    if (userId === user?.id) {
      toast.error("You cannot delete yourself");
      return;
    }

    if (!window.confirm(`Are you sure you want to delete user "${username}"? This action cannot be undone.`)) {
      return;
    }

    setActionLoading(prev => ({ ...prev, [userId]: "delete" }));

    try {
      const endpoint = `${VITE_API_URL}/api/users/${userId}`;
      console.log("Deleting user:", endpoint);

      const response = await makeAuthenticatedRequest(endpoint, {
        method: "DELETE"
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || "Failed to delete user");
      }

     
      const updatedUsers = users.filter(u => u.id !== userId);
      setUsers(updatedUsers);
      
      toast.success(`User "${username}" deleted successfully`);
      
    } catch (error) {
      console.error("Failed to delete user:", error);
      toast.error(`Failed to delete user: ${error.message}`);
    } finally {
      setActionLoading(prev => ({ ...prev, [userId]: false }));
    }
  };

  const toggleAdmin = async (userId, shouldMakeAdmin) => {
    if (!token || !isAdmin) {
      toast.error("Admin access required");
      return;
    }

    const action = shouldMakeAdmin ? "make admin" : "remove admin";
    setActionLoading(prev => ({ ...prev, [userId]: action }));

    try {
      const endpoint = `${VITE_API_URL}/api/users/${userId}`;
      console.log(`${action} for user:`, endpoint);

      const response = await makeAuthenticatedRequest(endpoint, {
        method: "PATCH",
        body: JSON.stringify({ is_admin: shouldMakeAdmin })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `Failed to ${action}`);
      }

    
      const updatedUsers = users.map((u) =>
        u.id === userId ? { ...u, is_admin: shouldMakeAdmin } : u
      );
      setUsers(updatedUsers);
      
      toast.success(`User ${action} successful`);
      
    } catch (error) {
      console.error(`Failed to ${action}:`, error);
      toast.error(`Failed to ${action}: ${error.message}`);
    } finally {
      setActionLoading(prev => ({ ...prev, [userId]: false }));
    }
  };


  if (loading) {
    return (
      <div className="max-w-5xl mx-auto p-6">
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mr-4"></div>
          <span className="text-gray-600">Loading users...</span>
        </div>
      </div>
    );
  }

 
  if (!isAuthenticated || !isAdmin) {
    return (
      <div className="max-w-5xl mx-auto p-6">
        <div className="text-center py-12">
          <h1 className="text-2xl font-bold text-red-600 mb-4">Access Denied</h1>
          <p className="text-gray-600">You need admin privileges to view this page.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2 text-indigo-800">👥 All Users</h1>
        <p className="text-gray-600">Manage user accounts and permissions</p>
        <div className="text-xs text-gray-400 mt-2">
          Total users: {users.length} | Showing: {filteredUsers.length}
        </div>
      </div>

      {/* Search and Actions */}
      <div className="mb-6 flex flex-col sm:flex-row gap-4 items-center justify-between">
        <div className="relative flex-1 max-w-md">
          <input
            type="text"
            placeholder="Search users by username or email..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
          {searchTerm && (
            <button
              onClick={() => setSearchTerm("")}
              className="absolute right-3 top-3 text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          )}
        </div>
        <button
          onClick={fetchUsers}
          disabled={loading}
          className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 flex items-center gap-2"
        >
          🔄 Refresh Users
        </button>
      </div>

      {/* Users List */}
      {filteredUsers.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-6xl mb-4">👥</div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            {searchTerm ? "No users found" : "No users available"}
          </h3>
          <p className="text-gray-500">
            {searchTerm 
              ? `No users match "${searchTerm}"`
              : "No users have been registered yet."
            }
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="divide-y divide-gray-200">
            {filteredUsers.map((userItem) => (
              <div key={userItem.id} className="p-6 hover:bg-gray-50 transition-colors">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                  {/* User Info */}
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center">
                        <span className="text-indigo-600 font-medium">
                          {userItem.username?.charAt(0).toUpperCase() || "U"}
                        </span>
                      </div>
                      <div>
                        <h3 className="font-medium text-gray-900">{userItem.username}</h3>
                        <p className="text-sm text-gray-500">{userItem.email}</p>
                      </div>
                    </div>
                    
                    {/* User Status Badges */}
                    <div className="flex gap-2 mt-3">
                      {userItem.is_admin && (
                        <span className="px-2 py-1 text-xs bg-purple-100 text-purple-800 rounded-full">
                          🛡️ Admin
                        </span>
                      )}
                      {userItem.is_blocked && (
                        <span className="px-2 py-1 text-xs bg-red-100 text-red-800 rounded-full">
                          🚫 Blocked
                        </span>
                      )}
                      {userItem.id === user?.id && (
                        <span className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full">
                          👤 You
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex flex-wrap gap-2">
                    {/* Block/Unblock Button */}
                    <button
                      onClick={() => toggleBlock(userItem.id, !userItem.is_blocked)}
                      disabled={actionLoading[userItem.id] || userItem.id === user?.id}
                      className={`px-3 py-1 text-xs rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                        userItem.is_blocked
                          ? "bg-green-100 text-green-800 hover:bg-green-200"
                          : "bg-red-100 text-red-800 hover:bg-red-200"
                      }`}
                    >
                      {actionLoading[userItem.id] === (userItem.is_blocked ? "unblock" : "block") ? (
                        <span className="flex items-center gap-1">
                          <div className="w-3 h-3 border border-current border-t-transparent rounded-full animate-spin"></div>
                          {userItem.is_blocked ? "Unblocking..." : "Blocking..."}
                        </span>
                      ) : (
                        userItem.is_blocked ? "🔓 Unblock" : "🚫 Block"
                      )}
                    </button>

                    {/* Admin Toggle Button */}
                    <button
                      onClick={() => toggleAdmin(userItem.id, !userItem.is_admin)}
                      disabled={actionLoading[userItem.id] || userItem.id === user?.id}
                      className={`px-3 py-1 text-xs rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                        userItem.is_admin
                          ? "bg-orange-100 text-orange-800 hover:bg-orange-200"
                          : "bg-purple-100 text-purple-800 hover:bg-purple-200"
                      }`}
                    >
                      {actionLoading[userItem.id] === (userItem.is_admin ? "remove admin" : "make admin") ? (
                        <span className="flex items-center gap-1">
                          <div className="w-3 h-3 border border-current border-t-transparent rounded-full animate-spin"></div>
                          {userItem.is_admin ? "Removing..." : "Adding..."}
                        </span>
                      ) : (
                        userItem.is_admin ? "👤 Remove Admin" : "🛡️ Make Admin"
                      )}
                    </button>

                    {/* Delete Button */}
                    <button
                      onClick={() => deleteUser(userItem.id, userItem.username)}
                      disabled={actionLoading[userItem.id] || userItem.id === user?.id}
                      className="px-3 py-1 text-xs bg-red-100 text-red-800 rounded-full hover:bg-red-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {actionLoading[userItem.id] === "delete" ? (
                        <span className="flex items-center gap-1">
                          <div className="w-3 h-3 border border-current border-t-transparent rounded-full animate-spin"></div>
                          Deleting...
                        </span>
                      ) : (
                        "🗑️ Delete"
                      )}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

    
      {import.meta.env.DEV && (
        <div className="mt-8 p-4 bg-gray-100 rounded-lg text-xs text-gray-600">
          <h4 className="font-bold mb-2">🔍 Debug Info</h4>
          <div>API: {VITE_API_URL}</div>
          <div>Current User: {user?.username} (ID: {user?.id})</div>
          <div>Is Admin: {isAdmin ? "Yes" : "No"}</div>
          <div>Token: {token ? "Present" : "Missing"}</div>
          <div>Total Users: {users.length}</div>
          <div>Filtered Users: {filteredUsers.length}</div>
        </div>
      )}
    </div>
  );
};

export default Users;