import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext"; // Add this import
import toast from "react-hot-toast";

const VITE_API_URL = import.meta.env.VITE_API_URL || "https://mindthread-1.onrender.com";

const EditPost = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, token, loading: authLoading, authenticatedRequest, isAdmin } = useAuth(); // Add isAdmin
  const [post, setPost] = useState({ title: "", content: "", tags: "" });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const fetchPost = async () => {
      try {
        setLoading(true);
        // Use AuthContext's authenticatedRequest function
        const res = await authenticatedRequest(`${VITE_API_URL}/api/posts/${id}`);

        if (!res.ok) {
          if (res.status === 403) {
            toast.error("You are not authorized to edit this post.");
            navigate("/posts");
            return;
          }
          if (res.status === 401) {
            toast.error("Session expired. Please log in again.");
            navigate("/login");
            return;
          }
          if (res.status === 404) {
            toast.error("Post not found.");
            navigate("/posts");
            return;
          }
          throw new Error("Failed to fetch post.");
        }

        const data = await res.json();
        
        // Check if user owns the post or is admin
        if (data.user_id !== user.id && !isAdmin()) {
          toast.error("You can only edit your own posts.");
          navigate("/posts");
          return;
        }

        setPost({ 
          title: data.title, 
          content: data.content,
          tags: data.tags || ""
        });
      } catch (err) {
        console.error("Error fetching post:", err);
        toast.error("Could not load the post.");
        navigate("/posts");
      } finally {
        setLoading(false);
      }
    };

    if (id) {
      fetchPost();
    }
  }, [id, navigate, user, token]);

  const handleUpdate = async (e) => {
    e.preventDefault();
    
    if (!post.title.trim() || !post.content.trim()) {
      toast.error("Title and content cannot be empty.");
      return;
    }

    setSaving(true);

    try {
      // Use AuthContext's authenticatedRequest function
      const res = await authenticatedRequest(`${VITE_API_URL}/api/posts/${id}`, {
        method: "PATCH",
        body: JSON.stringify({
          title: post.title.trim(),
          content: post.content.trim(),
          tags: post.tags.trim()
        }),
      });

      if (res.ok) {
        const data = await res.json();
        toast.success(data.message || "Post updated successfully.");
        navigate(`/posts/${id}`);
      } else {
        const error = await res.json();
        toast.error(error.error || error.message || "Failed to update post.");
      }
    } catch (err) {
      console.error("Error updating post:", err);
      toast.error("Something went wrong while updating.");
    } finally {
      setSaving(false);
    }
  };

  if (loading || authLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <div className="text-center py-16">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent mx-auto mb-6"></div>
            <p className="text-gray-600 text-lg font-medium">Loading...</p>
          </div>
        </div>
      </div>
    );
  }

  // Show unauthorized message if user is not authenticated
  if (!user || !token) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <div className="text-center py-16">
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Authentication Required</h2>
            <p className="text-gray-600 mb-6">You must be logged in to edit posts.</p>
            <button 
              onClick={() => navigate("/login")}
              className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-medium rounded-xl hover:from-blue-700 hover:to-indigo-700 transition-all duration-200 transform hover:scale-105 shadow-lg"
            >
              Go to Login
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-blue-50 to-indigo-50">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Navigation */}
        <div className="mb-8">
          <button 
            onClick={() => navigate(`/posts/${id}`)}
            className="inline-flex items-center text-blue-600 hover:text-blue-800 font-medium transition-colors duration-200 group"
          >
            <svg className="w-4 h-4 mr-2 transition-transform group-hover:-translate-x-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Post
          </button>
        </div>

        {/* Edit Form */}
        <div className="bg-white/80 backdrop-blur-sm rounded-3xl shadow-xl border border-gray-200 p-6 sm:p-8 lg:p-10">
          <h2 className="text-3xl font-bold mb-8 text-gray-900 flex items-center">
            <svg className="w-8 h-8 mr-3 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
            Edit Post
          </h2>

          <form onSubmit={handleUpdate} className="space-y-6">
            {/* Title Input */}
            <div>
              <label htmlFor="title" className="block text-sm font-semibold text-gray-700 mb-2">
                Post Title
              </label>
              <input
                id="title"
                type="text"
                className="w-full border border-gray-300 rounded-xl px-4 py-3 text-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200"
                placeholder="Enter your post title..."
                value={post.title}
                onChange={(e) => setPost({ ...post, title: e.target.value })}
                required
                disabled={saving}
              />
            </div>

            {/* Content Textarea */}
            <div>
              <label htmlFor="content" className="block text-sm font-semibold text-gray-700 mb-2">
                Post Content
              </label>
              <textarea
                id="content"
                className="w-full border border-gray-300 rounded-xl px-4 py-3 text-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 resize-vertical"
                placeholder="Write your post content..."
                value={post.content}
                onChange={(e) => setPost({ ...post, content: e.target.value })}
                required
                disabled={saving}
                rows={12}
              />
            </div>

            {/* Tags Input */}
            <div>
              <label htmlFor="tags" className="block text-sm font-semibold text-gray-700 mb-2">
                Tags (optional)
              </label>
              <input
                id="tags"
                type="text"
                className="w-full border border-gray-300 rounded-xl px-4 py-3 text-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200"
                placeholder="Enter tags separated by commas..."
                value={post.tags}
                onChange={(e) => setPost({ ...post, tags: e.target.value })}
                disabled={saving}
              />
              <p className="text-sm text-gray-500 mt-1">
                Example: technology, programming, web development
              </p>
            </div>

            {/* Action Buttons */}
            <div className="flex flex-col sm:flex-row justify-between space-y-3 sm:space-y-0 sm:space-x-4 pt-6 border-t border-gray-200">
              <button
                type="button"
                onClick={() => navigate(`/posts/${id}`)}
                className="inline-flex items-center justify-center px-6 py-3 bg-gray-500 text-white font-medium rounded-xl hover:bg-gray-600 transition-all duration-200 transform hover:scale-105 shadow-lg"
                disabled={saving}
              >
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                Cancel
              </button>
              
              <button
                type="submit"
                className="inline-flex items-center justify-center px-6 py-3 bg-gradient-to-r from-green-600 to-emerald-600 text-white font-medium rounded-xl hover:from-green-700 hover:to-emerald-700 transition-all duration-200 transform hover:scale-105 shadow-lg disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
                disabled={saving || !post.title.trim() || !post.content.trim()}
              >
                {saving ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2"></div>
                    Saving...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    Save Changes
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default EditPost;