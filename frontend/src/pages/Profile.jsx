import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import AvatarUploader from "../components/AvatarUploader";
import toast from "react-hot-toast";

const API_URL = import.meta.env.VITE_API_URL || "https://mindthread-1.onrender.com";

const Profile = () => {
  const { user, deleteUser, token, loading, updateUser } = useAuth(); 
  const navigate = useNavigate();
  const [isDeleting, setIsDeleting] = useState(false);
  const [userStats, setUserStats] = useState({ posts: 0, comments: 0, votes: 0 });
  const [isLoadingStats, setIsLoadingStats] = useState(false);
  const [fullUserData, setFullUserData] = useState(null);

  useEffect(() => {
    if (!loading && !token) {
      navigate("/login");
    }
  }, [token, loading, navigate]);

  useEffect(() => {
    if (user && token) {
      fetchFullUserProfile();
    }
  }, [user, token]);

  // Fetch complete user profile including stats from /api/users/me
  const fetchFullUserProfile = async () => {
    if (!token) return;
    
    try {
      setIsLoadingStats(true);
      
      const response = await fetch(`${API_URL}/api/users/me`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        credentials: "include",
      });

      if (response.ok) {
        const userData = await response.json();
        setFullUserData(userData);
        
        // Extract stats - handle both possible response formats
        if (userData.stats) {
          // New format with stats object
          setUserStats({
            posts: userData.stats.posts_count || 0,
            comments: userData.stats.comments_count || 0,
            votes: userData.stats.votes_count || 0, 
          });
        } else {
          // Fallback to direct properties or zero
          setUserStats({
            posts: userData.post_count || 0,
            comments: userData.comment_count || 0,
            votes: userData.vote_count || 0, 
          });
        }
      } else {
        const errorText = await response.text();
        console.error("Failed to fetch user profile:", response.status, errorText);
        toast.error("Failed to load profile data");
        setUserStats({ posts: 0, comments: 0, votes: 0 });
      }
    } catch (error) {
      console.error("Error fetching user profile:", error);
      toast.error("Network error loading profile");
      setUserStats({ posts: 0, comments: 0, votes: 0 });
    } finally {
      setIsLoadingStats(false);
    }
  };

  const handleDelete = async () => {
    const confirmMessage = `Are you sure you want to delete your account? This action cannot be undone.

This will permanently delete:
- Your profile
- All your posts (${userStats.posts})
- All your comments (${userStats.comments})
- All your votes (${userStats.votes})`;

    const confirmed = window.confirm(confirmMessage);
    if (!confirmed) return;

    const doubleConfirm = window.confirm("Are you absolutely sure? Type 'DELETE' in the next prompt to confirm.");
    if (!doubleConfirm) return;

    const finalConfirm = prompt("Type 'DELETE' to confirm account deletion:");
    if (finalConfirm !== "DELETE") {
      toast.error("Account deletion cancelled - confirmation text didn't match");
      return;
    }

    setIsDeleting(true);

    try {
      await deleteUser();
      toast.success("Account deleted successfully");
      navigate("/login");
    } catch (error) {
      console.error("Error deleting account:", error);
      toast.error("Failed to delete account. Please try again.");
    } finally {
      setIsDeleting(false);
    }
  };

  // Handle account settings/edit profile
  const handleEditProfile = () => {
    navigate("/profile/edit");
  };

  // Refresh profile data
  const handleRefreshProfile = () => {
    fetchFullUserProfile();
    toast.success("Profile refreshed");
  };

  if (loading) {
    return (
      <div className="max-w-lg mx-auto p-6 bg-white shadow rounded mt-10">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded mb-4"></div>
          <div className="h-4 bg-gray-200 rounded mb-2"></div>
          <div className="h-4 bg-gray-200 rounded mb-2"></div>
          <div className="h-4 bg-gray-200 rounded mb-4"></div>
          <div className="grid grid-cols-3 gap-4">
            <div className="h-16 bg-gray-200 rounded"></div>
            <div className="h-16 bg-gray-200 rounded"></div>
            <div className="h-16 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!user) {
    return <p className="text-center p-6">Redirecting to login...</p>;
  }

  return (
    <div className="max-w-lg mx-auto p-6 bg-white shadow rounded mt-10">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">Your Profile</h2>
        <button
          onClick={handleRefreshProfile}
          className="text-indigo-600 hover:text-indigo-800 text-sm font-medium"
          disabled={isLoadingStats}
        >
          {isLoadingStats ? "Refreshing..." : "Refresh"}
        </button>
      </div>
      
      {/* Profile Information */}
      <div className="bg-gray-50 p-4 rounded mb-6">
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label className="text-sm font-medium text-gray-500">Username</label>
            <p className="text-gray-900 font-medium">{user.username}</p>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-500">Email</label>
            <p className="text-gray-900">{user.email}</p>
          </div>
        </div>
        
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label className="text-sm font-medium text-gray-500">Member Since</label>
            <p className="text-gray-900">
              {user.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}
            </p>
          </div>
          <div>
            <label className="text-sm font-medium text-gray-500">Account Type</label>
            <p className="text-gray-900">
              {user.is_admin ? (
                <span className="bg-purple-100 text-purple-800 px-2 py-1 rounded text-xs font-medium">
                  Administrator
                </span>
              ) : (
                <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs font-medium">
                  Member
                </span>
              )}
            </p>
          </div>
        </div>

        {/* Account Status */}
        <div className="pt-2 border-t border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <label className="text-sm font-medium text-gray-500">Account Status</label>
              <div className="flex items-center space-x-2">
                {user.is_blocked ? (
                  <span className="bg-red-100 text-red-800 px-2 py-1 rounded text-xs font-medium">
                    Blocked
                  </span>
                ) : (
                  <span className="bg-green-100 text-green-800 px-2 py-1 rounded text-xs font-medium">
                    Active
                  </span>
                )}
                {user.is_active !== false && (
                  <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs font-medium">
                    Verified
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* User Statistics */}
        <div className="grid grid-cols-3 gap-4 pt-4 border-t border-gray-200 mt-4">
          <div className="text-center">
            {isLoadingStats ? (
              <div className="animate-pulse">
                <div className="h-8 bg-gray-200 rounded mb-2"></div>
                <div className="h-4 bg-gray-200 rounded"></div>
              </div>
            ) : (
              <>
                <p className="text-2xl font-bold text-indigo-600">{userStats.posts}</p>
                <p className="text-sm text-gray-500">Posts</p>
              </>
            )}
          </div>
          <div className="text-center">
            {isLoadingStats ? (
              <div className="animate-pulse">
                <div className="h-8 bg-gray-200 rounded mb-2"></div>
                <div className="h-4 bg-gray-200 rounded"></div>
              </div>
            ) : (
              <>
                <p className="text-2xl font-bold text-green-600">{userStats.comments}</p>
                <p className="text-sm text-gray-500">Comments</p>
              </>
            )}
          </div>
          <div className="text-center">
            {isLoadingStats ? (
              <div className="animate-pulse">
                <div className="h-8 bg-gray-200 rounded mb-2"></div>
                <div className="h-4 bg-gray-200 rounded"></div>
              </div>
            ) : (
              <>
                <p className="text-2xl font-bold text-orange-600">{userStats.votes}</p>
                <p className="text-sm text-gray-500">Votes</p>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Avatar Upload Section */}
      <div className="mb-6">
        <h3 className="text-lg font-medium mb-3">Profile Picture</h3>
        <AvatarUploader onUploadSuccess={fetchFullUserProfile} />
      </div>

      {/* Recent Activity Preview */}
      {fullUserData && (fullUserData.recent_posts || fullUserData.recent_comments) && (
        <div className="mb-6">
          <h3 className="text-lg font-medium mb-3">Recent Activity</h3>
          <div className="bg-gray-50 p-4 rounded space-y-3">
            {fullUserData.recent_posts && fullUserData.recent_posts.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-600 mb-2">Recent Posts</h4>
                <div className="space-y-1">
                  {fullUserData.recent_posts.slice(0, 3).map((post) => (
                    <div key={post.id} className="text-sm">
                      <span className="text-indigo-600 hover:text-indigo-800 cursor-pointer">
                        {post.title}
                      </span>
                      <span className="text-gray-500 ml-2">
                        {new Date(post.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {fullUserData.recent_comments && fullUserData.recent_comments.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-600 mb-2">Recent Comments</h4>
                <div className="space-y-1">
                  {fullUserData.recent_comments.slice(0, 2).map((comment) => (
                    <div key={comment.id} className="text-sm">
                      <span className="text-gray-700">{comment.content}</span>
                      <span className="text-gray-500 ml-2">
                        {new Date(comment.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="mb-6">
        <h3 className="text-lg font-medium mb-3">Quick Actions</h3>
        <div className="space-y-2">
          <button
            onClick={() => navigate("/posts/new")}
            className="w-full bg-indigo-600 text-white py-2 px-4 rounded hover:bg-indigo-700 transition-colors"
          >
            Create New Post
          </button>
          
          <button
            onClick={handleEditProfile}
            className="w-full bg-gray-600 text-white py-2 px-4 rounded hover:bg-gray-700 transition-colors"
          >
            Edit Profile
          </button>
          
          {user.is_admin && (
            <button
              onClick={() => navigate("/admin")}
              className="w-full bg-purple-600 text-white py-2 px-4 rounded hover:bg-purple-700 transition-colors"
            >
              Admin Dashboard
            </button>
          )}
        </div>
      </div>

      {/* Danger Zone */}
      <div className="border-t border-red-200 pt-6">
        <h3 className="text-lg font-medium text-red-600 mb-3">Danger Zone</h3>
        <p className="text-sm text-gray-600 mb-4">
          Once you delete your account, this action cannot be undone! This will permanently delete all your posts, comments, and votes.
        </p>
        <button
          onClick={handleDelete}
          disabled={isDeleting}
          className="w-full bg-red-600 text-white py-2 px-4 rounded hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
        >
          {isDeleting ? "Deleting Account..." : "Delete Account"}
        </button>
      </div>
    </div>
  );
};

export default Profile;