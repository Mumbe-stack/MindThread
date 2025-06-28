import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const API_URL = import.meta.env.VITE_API_URL || "https://mindthread-1.onrender.com";

// Avatar Uploader Component (for Quick Actions section)
const AvatarUploader = ({ onUploadSuccess }) => {
  const [isUploading, setIsUploading] = useState(false);
  const { token } = useAuth();

  const handleFileSelect = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      console.error('Please select an image file');
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      console.error('File size must be less than 5MB');
      return;
    }

    await uploadAvatar(file);
  };

  const uploadAvatar = async (file) => {
    setIsUploading(true);
    
    try {
      const formData = new FormData();
      formData.append('avatar', file);

      console.log("Uploading avatar to:", `${API_URL}/api/users/me/avatar`);

      const response = await fetch(`${API_URL}/api/users/me/avatar`, {
        method: 'POST',
        headers: {
          "Authorization": `Bearer ${token}`,
        },
        credentials: "include",
        body: formData,
      });

      if (response.ok) {
        const result = await response.json();
        console.log("Avatar upload success:", result);
        
        // Don't trigger refresh - just let user refresh manually if needed
        
      } else {
        const errorData = await response.json().catch(() => ({}));
        console.error("Avatar upload failed:", errorData);
      }

    } catch (error) {
      console.error("Avatar upload error:", error);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <label className="block">
      <input
        type="file"
        accept="image/*"
        onChange={handleFileSelect}
        disabled={isUploading}
        className="sr-only"
      />
      <div className="cursor-pointer inline-flex items-center justify-center w-full px-3 sm:px-6 py-3 border border-gray-300 text-sm sm:text-base font-medium rounded-lg text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm">
        <svg className="w-4 h-4 sm:w-5 sm:h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
        <span className="hidden sm:inline">{isUploading ? 'Uploading...' : 'Update Avatar'}</span>
        <span className="sm:hidden">{isUploading ? 'Uploading...' : 'Avatar'}</span>
      </div>
    </label>
  );
};

const Profile = () => {
  const { user, deleteUser, token, loading } = useAuth(); 
  const navigate = useNavigate();
  const [isDeleting, setIsDeleting] = useState(false);
  const [userStats, setUserStats] = useState({ posts: 0, comments: 0, votes: 0 });
  const [isLoadingStats, setIsLoadingStats] = useState(false);
  const [fullUserData, setFullUserData] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Redirect if not authenticated
  useEffect(() => {
    if (!loading && !token && !user) {
      navigate("/login");
    }
  }, [token, loading, user, navigate]);

  // Fetch profile data when component mounts (only once)
  useEffect(() => {
    if (user && token && !fullUserData) {
      fetchFullUserProfile();
    }
  }, [user?.id, token]); // Only depend on user.id and token to prevent loops

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

  const fetchFullUserProfile = async () => {
    if (!token) return;
    
    try {
      setIsLoadingStats(true);
      
      console.log("Fetching user profile from:", `${API_URL}/api/users/me`);
      
      const response = await makeAuthenticatedRequest(`${API_URL}/api/users/me`);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch profile: ${response.status}`);
      }

      const userData = await response.json();
      console.log("User data received:", userData);
      
      setFullUserData(userData);
      
      // Enhanced stats extraction with multiple fallback methods
      let posts = 0, comments = 0, votes = 0;
      
      // Method 1: Check nested stats object (preferred format)
      if (userData.stats) {
        posts = userData.stats.posts_count || userData.stats.post_count || 0;
        comments = userData.stats.comments_count || userData.stats.comment_count || 0;
        votes = userData.stats.votes_count || userData.stats.vote_count || 0;
        console.log("Stats from nested object:", { posts, comments, votes });
      }
      
      // Method 2: Fallback to direct properties
      if (posts === 0 && comments === 0 && votes === 0) {
        posts = userData.post_count || userData.posts_count || 0;
        comments = userData.comment_count || userData.comments_count || 0;
        votes = userData.vote_count || userData.votes_count || 0;
        console.log("Stats from direct properties:", { posts, comments, votes });
      }

      setUserStats({ posts, comments, votes });
      
      console.log("Final stats set:", { posts, comments, votes });

    } catch (error) {
      console.error("Profile data fetch error:", error);
      
      if (error.message.includes("401") || error.message.includes("Authentication")) {
        navigate("/login");
      }
      
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
      return;
    }

    setIsDeleting(true);

    try {
      await deleteUser();
      navigate("/login");
    } catch (error) {
      console.error("Failed to delete account:", error);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleEditProfile = () => {
    navigate("/profile/edit");
  };

  const handleRefreshProfile = async () => {
    setIsRefreshing(true);
    await fetchFullUserProfile();
    setIsRefreshing(false);
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto p-3 sm:p-6 bg-white shadow-lg rounded-lg mt-6 sm:mt-10">
        <div className="animate-pulse">
          <div className="h-6 sm:h-8 bg-gray-200 rounded mb-4 sm:mb-6"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6 mb-4 sm:mb-6">
            <div className="h-4 bg-gray-200 rounded"></div>
            <div className="h-4 bg-gray-200 rounded"></div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4 mb-4 sm:mb-6">
            <div className="h-16 sm:h-20 bg-gray-200 rounded"></div>
            <div className="h-16 sm:h-20 bg-gray-200 rounded"></div>
            <div className="h-16 sm:h-20 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!user && !loading && !token) {
    return (
      <div className="max-w-4xl mx-auto p-3 sm:p-6 text-center">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-yellow-800 text-sm sm:text-base">Redirecting to login...</p>
        </div>
      </div>
    );
  }

  if (!user && token) {
    return (
      <div className="max-w-4xl mx-auto p-3 sm:p-6 bg-white shadow-lg rounded-lg mt-6 sm:mt-10">
        <div className="animate-pulse">
          <div className="h-6 sm:h-8 bg-gray-200 rounded mb-4 sm:mb-6"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6 mb-4 sm:mb-6">
            <div className="h-4 bg-gray-200 rounded"></div>
            <div className="h-4 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  // Get the avatar URL from either fullUserData or user
  const avatarUrl = fullUserData?.avatar_url || user?.avatar_url;

  return (
    <div className="max-w-4xl mx-auto p-3 sm:p-6 bg-white shadow-lg rounded-lg mt-6 sm:mt-10">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 sm:mb-8 gap-4">
        <h2 className="text-2xl sm:text-3xl font-bold text-gray-900">Your Profile</h2>
        <button
          onClick={handleRefreshProfile}
          className="inline-flex items-center px-3 sm:px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
          disabled={isLoadingStats || isRefreshing}
        >
          <svg className={`w-4 h-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          <span className="hidden sm:inline">{isRefreshing ? "Refreshing..." : "Refresh"}</span>
          <span className="sm:hidden">{isRefreshing ? "..." : "↻"}</span>
        </button>
      </div>
      
      {/* Profile Information with Avatar Display Only */}
      <div className="bg-gradient-to-br from-gray-50 to-gray-100 p-4 sm:p-6 rounded-lg mb-6 sm:mb-8 border border-gray-200">
        <div className="flex flex-col sm:flex-row items-center sm:items-start space-y-4 sm:space-y-0 sm:space-x-6 mb-4 sm:mb-6 pb-4 sm:pb-6 border-b border-gray-200">
          {/* Avatar Display (no upload functionality here) */}
          <div className="relative flex-shrink-0">
            <div className="w-20 h-20 sm:w-24 sm:h-24 rounded-full overflow-hidden bg-gray-200 border-3 sm:border-4 border-white shadow-lg">
              {avatarUrl ? (
                <img 
                  src={avatarUrl.startsWith('http') ? avatarUrl : `${API_URL}${avatarUrl}`}
                  alt="Profile" 
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    console.log("Avatar image failed to load:", avatarUrl);
                    e.target.style.display = 'none';
                    e.target.nextElementSibling.style.display = 'flex';
                  }}
                />
              ) : null}
              <div 
                className="w-full h-full flex items-center justify-center text-gray-400" 
                style={{ display: avatarUrl ? 'none' : 'flex' }}
              >
                <svg className="w-8 h-8 sm:w-10 sm:h-10" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                </svg>
              </div>
            </div>
          </div>
          
          <div className="flex-1 text-center sm:text-left">
            <h3 className="text-xl sm:text-2xl font-bold text-gray-900 mb-1">{user.username}</h3>
            <p className="text-gray-600 mb-2 text-sm sm:text-base break-all sm:break-normal">{user.email}</p>
            <div className="flex flex-wrap justify-center sm:justify-start items-center space-x-2 gap-y-2">
              {user.is_admin ? (
                <span className="inline-flex items-center px-2 sm:px-3 py-1 rounded-full text-xs sm:text-sm font-medium bg-purple-100 text-purple-800 border border-purple-200">
                  <svg className="w-3 h-3 sm:w-4 sm:h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M9.504 1.132a1 1 0 01.992 0l1.75 1a1 1 0 11-.992 1.736L10 3.152l-1.254.716a1 1 0 11-.992-1.736l1.75-1zM5.618 4.504a1 1 0 01-.372 1.364L5.016 6l.23.132a1 1 0 11-.992 1.736L3 7.723V8a1 1 0 01-2 0V6a.996.996 0 01.52-.878l1.734-.99a1 1 0 011.364.372zm8.764 0a1 1 0 011.364-.372l1.734.99A.996.996 0 0118 6v2a1 1 0 11-2 0v-.277l-1.254.145a1 1 0 11-.992-1.736L14.984 6l-.23-.132a1 1 0 01-.372-1.364zm-7 4a1 1 0 011.364-.372L10 8.848l1.254-.716a1 1 0 11.992 1.736L11 10.723V12a1 1 0 11-2 0v-1.277l-1.246-.855a1 1 0 01-.372-1.364zM3 11a1 1 0 011 1v1.277l1.254.145a1 1 0 11-.992 1.736l-1.736-.992A.996.996 0 012 14v-2a1 1 0 011-1zm14 0a1 1 0 011 1v2a.996.996 0 01-.518.878l-1.734.99a1 1 0 11-1.364-.372l.23-.132L15.016 15l-.23-.132a1 1 0 11.992-1.736L17 13.277V12a1 1 0 011-1zm-9.618 5.504a1 1 0 011.364-.372l.254.145V16a1 1 0 112 0v.277l.254-.145a1 1 0 11.992 1.736l-1.735.992a.995.995 0 01-1.022 0l-1.735-.992a1 1 0 01-.372-1.364z" clipRule="evenodd" />
                  </svg>
                  <span className="hidden sm:inline">Administrator</span>
                  <span className="sm:hidden">Admin</span>
                </span>
              ) : (
                <span className="inline-flex items-center px-2 sm:px-3 py-1 rounded-full text-xs sm:text-sm font-medium bg-blue-100 text-blue-800 border border-blue-200">
                  <svg className="w-3 h-3 sm:w-4 sm:h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                  </svg>
                  Member
                </span>
              )}
              {user.is_blocked ? (
                <span className="inline-flex items-center px-2 sm:px-3 py-1 rounded-full text-xs sm:text-sm font-medium bg-red-100 text-red-800 border border-red-200">
                  <svg className="w-3 h-3 sm:w-4 sm:h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M13.477 14.89A6 6 0 015.11 6.524l8.367 8.368zm1.414-1.414L6.524 5.11a6 6 0 018.367 8.367zM18 10a8 8 0 11-16 0 8 8 0 0116 0z" clipRule="evenodd" />
                  </svg>
                  Blocked
                </span>
              ) : (
                <span className="inline-flex items-center px-2 sm:px-3 py-1 rounded-full text-xs sm:text-sm font-medium bg-green-100 text-green-800 border border-green-200">
                  <svg className="w-3 h-3 sm:w-4 sm:h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  Active
                </span>
              )}
            </div>
          </div>
        </div>

        {/* User Details */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
          <div className="space-y-1 text-center sm:text-left">
            <label className="text-xs sm:text-sm font-semibold text-gray-600 uppercase tracking-wide">Member Since</label>
            <p className="text-base sm:text-lg text-gray-900">
              {(() => {
                const rawDate = user.created_at || new Date().toISOString();
                const date = new Date(rawDate);
                const day = String(date.getDate()).padStart(2, '0');
                const month = String(date.getMonth() + 1).padStart(2, '0');
                const year = date.getFullYear();
                return `${day}/${month}/${year}`;
                })()}
            </p>
            <p className="text-xs sm:text-sm text-gray-500">
              {user.created_at ? `${Math.floor((new Date() - new Date(user.created_at)) / (1000 * 60 * 60 * 24))} days ago` : ''}
            </p>
          </div>
          <div className="space-y-1 text-center sm:text-left">
            <label className="text-xs sm:text-sm font-semibold text-gray-600 uppercase tracking-wide">Account ID</label>
            <p className="text-base sm:text-lg font-mono text-gray-900">#{user.id}</p>
            <p className="text-xs sm:text-sm text-gray-500">Your unique identifier</p>
          </div>
        </div>
      </div>

      {/* User Statistics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6 mb-6 sm:mb-8">
        <div className="bg-white border border-gray-200 rounded-lg p-4 sm:p-6 text-center shadow-sm hover:shadow-md transition-shadow">
          {isLoadingStats ? (
            <div className="animate-pulse">
              <div className="h-6 sm:h-8 bg-gray-200 rounded mb-2"></div>
              <div className="h-3 sm:h-4 bg-gray-200 rounded"></div>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-center w-10 h-10 sm:w-12 sm:h-12 mx-auto mb-3 bg-indigo-100 rounded-lg">
                <svg className="w-5 h-5 sm:w-6 sm:h-6 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <p className="text-2xl sm:text-3xl font-bold text-indigo-600 mb-1">{userStats.posts}</p>
              <p className="text-xs sm:text-sm font-medium text-gray-500">Posts</p>
            </>
          )}
        </div>
        
        <div className="bg-white border border-gray-200 rounded-lg p-4 sm:p-6 text-center shadow-sm hover:shadow-md transition-shadow">
          {isLoadingStats ? (
            <div className="animate-pulse">
              <div className="h-6 sm:h-8 bg-gray-200 rounded mb-2"></div>
              <div className="h-3 sm:h-4 bg-gray-200 rounded"></div>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-center w-10 h-10 sm:w-12 sm:h-12 mx-auto mb-3 bg-green-100 rounded-lg">
                <svg className="w-5 h-5 sm:w-6 sm:h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
              </div>
              <p className="text-2xl sm:text-3xl font-bold text-green-600 mb-1">{userStats.comments}</p>
              <p className="text-xs sm:text-sm font-medium text-gray-500">Comments</p>
            </>
          )}
        </div>
        
        <div className="bg-white border border-gray-200 rounded-lg p-4 sm:p-6 text-center shadow-sm hover:shadow-md transition-shadow">
          {isLoadingStats ? (
            <div className="animate-pulse">
              <div className="h-6 sm:h-8 bg-gray-200 rounded mb-2"></div>
              <div className="h-3 sm:h-4 bg-gray-200 rounded"></div>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-center w-10 h-10 sm:w-12 sm:h-12 mx-auto mb-3 bg-orange-100 rounded-lg">
                <svg className="w-5 h-5 sm:w-6 sm:h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
                </svg>
              </div>
              <p className="text-2xl sm:text-3xl font-bold text-orange-600 mb-1">{userStats.votes}</p>
              <p className="text-xs sm:text-sm font-medium text-gray-500">Votes</p>
            </>
          )}
        </div>
      </div>

      {/* Quick Actions - Including Avatar Upload */}
      <div className="bg-white border border-gray-200 rounded-lg p-4 sm:p-6 mb-6 sm:mb-8 shadow-sm">
        <h3 className="text-lg sm:text-xl font-semibold text-gray-900 mb-4">Quick Actions</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          <button
            onClick={() => navigate("/posts/new")}
            className="inline-flex items-center justify-center px-3 sm:px-6 py-3 border border-transparent text-sm sm:text-base font-medium rounded-lg text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors shadow-sm"
          >
            <svg className="w-4 h-4 sm:w-5 sm:h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            <span className="hidden sm:inline">Create New Post</span>
            <span className="sm:hidden">New Post</span>
          </button>
          
          <button
            onClick={handleEditProfile}
            className="inline-flex items-center justify-center px-3 sm:px-6 py-3 border border-gray-300 text-sm sm:text-base font-medium rounded-lg text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors shadow-sm"
          >
            <svg className="w-4 h-4 sm:w-5 sm:h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
            <span className="hidden sm:inline">Edit Profile</span>
            <span className="sm:hidden">Edit</span>
          </button>
          
          {/* Avatar Upload Button */}
          <AvatarUploader onUploadSuccess={fetchFullUserProfile} />
          
          {user.is_admin && (
            <button
              onClick={() => navigate("/admin")}
              className="inline-flex items-center justify-center px-3 sm:px-6 py-3 border border-transparent text-sm sm:text-base font-medium rounded-lg text-white bg-purple-600 hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-purple-500 transition-colors shadow-sm"
            >
              <svg className="w-4 h-4 sm:w-5 sm:h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
              </svg>
              <span className="hidden sm:inline">Admin Dashboard</span>
              <span className="sm:hidden">Admin</span>
            </button>
          )}
        </div>
      </div>

      {/* Danger Zone */}
      <div className="bg-white border border-red-200 rounded-lg p-4 sm:p-6 shadow-sm mb-6 sm:mb-8">
        <h3 className="text-lg sm:text-xl font-semibold text-red-600 mb-4 flex items-center">
          <svg className="w-5 h-5 sm:w-6 sm:h-6 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.232 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
          Danger Zone
        </h3>
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 sm:p-4 mb-4">
          <p className="text-xs sm:text-sm text-red-800">
            <strong>Warning:</strong> Once you delete your account, this action cannot be undone! This will permanently delete all your posts, comments, and votes.
          </p>
        </div>
        <button
          onClick={handleDelete}
          disabled={isDeleting}
          className="inline-flex items-center justify-center w-full sm:w-auto px-4 sm:px-6 py-3 border border-transparent text-sm sm:text-base font-medium rounded-lg text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors shadow-sm"
        >
          {isDeleting ? (
            <>
              <svg className="animate-spin -ml-1 mr-3 h-4 w-4 sm:h-5 sm:w-5 text-white" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <span className="hidden sm:inline">Deleting Account...</span>
              <span className="sm:hidden">Deleting...</span>
            </>
          ) : (
            <>
              <svg className="w-4 h-4 sm:w-5 sm:h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              Delete Account
            </>
          )}
        </button>
      </div>

      {/* Recent Activity Preview - MOVED AFTER DELETE BUTTON AS REQUESTED */}
      {fullUserData && (fullUserData.recent_posts || fullUserData.recent_comments) && (
        <div className="bg-white border border-gray-200 rounded-lg p-4 sm:p-6 shadow-sm">
          <h3 className="text-lg sm:text-xl font-semibold text-gray-900 mb-4">Recent Activity</h3>
          <div className="space-y-6">
            {fullUserData.recent_posts && fullUserData.recent_posts.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-gray-600 uppercase tracking-wide mb-3">Recent Posts</h4>
                <div className="space-y-2">
                  {fullUserData.recent_posts.slice(0, 3).map((post) => (
                    <div key={post.id} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 p-3 bg-gray-50 rounded-lg">
                      <span className="text-indigo-600 hover:text-indigo-800 cursor-pointer font-medium text-sm sm:text-base">
                        {post.title}
                      </span>
                      <span className="text-gray-500 text-xs sm:text-sm flex-shrink-0">
                        {new Date(post.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {fullUserData.recent_comments && fullUserData.recent_comments.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-gray-600 uppercase tracking-wide mb-3">Recent Comments</h4>
                <div className="space-y-2">
                  {fullUserData.recent_comments.slice(0, 2).map((comment) => (
                    <div key={comment.id} className="p-3 bg-gray-50 rounded-lg">
                      <p className="text-gray-700 text-xs sm:text-sm mb-1">{comment.content}</p>
                      <span className="text-gray-500 text-xs">
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
    </div>
  );
};

export default Profile;