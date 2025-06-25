import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import AvatarUploader from "../components/AvatarUploader";
import toast from "react-hot-toast";

const Profile = () => {
  const { user, deleteUser, token, loading } = useAuth(); 
  const navigate = useNavigate();
  const [isDeleting, setIsDeleting] = useState(false);
  const [userStats, setUserStats] = useState({ posts: 0, comments: 0 });

  useEffect(() => {
    if (!loading && !token) {
      navigate("/login");
    }
  }, [token, loading, navigate]);

  useEffect(() => {
    if (user) {
      fetchUserStats();
    }
  }, [user]);

const fetchUserStats = async () => {
  try {
    const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/users/${user.id}/stats/`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (response.ok) {
      const userData = await response.json();
      setUserStats({
        posts: userData.posts || 0,
        comments: userData.comments || 0,
      });
    } else {
      const errorText = await response.text();
      console.error("Fetch failed:", errorText);
    }
  } catch (error) {
    console.error("Failed to fetch user stats:", error);
  }
};


  const handleDelete = async () => {
    const confirmMessage = `Are you sure you want to delete your account? This action cannot be undone.

This will permanently delete:
- Your profile
- All your posts (${userStats.posts})
- All your comments (${userStats.comments})`;

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
      console.error("Delete error:", error);
      toast.error("Failed to delete account. Please try again.");
    } finally {
      setIsDeleting(false);
    }
  };

 
  if (loading) {
    return (
      <div className="max-w-lg mx-auto p-6 bg-white shadow rounded mt-10">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded mb-4"></div>
          <div className="h-4 bg-gray-200 rounded mb-2"></div>
          <div className="h-4 bg-gray-200 rounded mb-2"></div>
          <div className="h-4 bg-gray-200 rounded mb-4"></div>
        </div>
      </div>
    );
  }

 
  if (!user) {
    return <p className="text-center p-6">Redirecting to login...</p>;
  }

  return (
    <div className="max-w-lg mx-auto p-6 bg-white shadow rounded mt-10">
      <h2 className="text-2xl font-bold mb-6 text-center">Your Profile</h2>
      
      {/* Profile Information */}
      <div className="bg-gray-50 p-4 rounded mb-6">
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label className="text-sm font-medium text-gray-500">Username</label>
            <p className="text-gray-900">{user.username}</p>
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
              {new Date(user.created_at).toLocaleDateString()}
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

        {/* User Statistics */}
        <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-200">
          <div className="text-center">
            <p className="text-2xl font-bold text-indigo-600">{userStats.posts}</p>
            <p className="text-sm text-gray-500">Posts</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-green-600">{userStats.comments}</p>
            <p className="text-sm text-gray-500">Comments</p>
          </div>
        </div>
      </div>

      {/* Avatar Upload Section */}
      <div className="mb-6">
        <h3 className="text-lg font-medium mb-3">Profile Picture</h3>
        <AvatarUploader />
      </div>

      {/* Quick Actions */}
      <div className="mb-6">
        <h3 className="text-lg font-medium mb-3">Quick Actions</h3>
        <div className="space-y-2">
          <button
            onClick={() => navigate("/posts/new")}
            className="w-full bg-indigo-600 text-white py-2 px-4 rounded hover:bg-indigo-700"
          >
            Create New Post
          </button>
          
          {user.is_admin && (
            <button
              onClick={() => navigate("/admin")}
              className="w-full bg-purple-600 text-white py-2 px-4 rounded hover:bg-purple-700"
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
          Once you delete your account, this action cannot be undone! Please be sure.
        </p>
        <button
          onClick={handleDelete}
          disabled={isDeleting}
          className="w-full bg-red-600 text-white py-2 px-4 rounded hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          {isDeleting ? "Deleting Account..." : "Delete Account"}
        </button>
      </div>
    </div>
  );
};

export default Profile;