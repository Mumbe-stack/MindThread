import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import toast from "react-hot-toast";

const VITE_API_URL = import.meta.env.VITE_API_URL || "https://mindthread-1.onrender.com";

const EditPost = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, token, authenticatedRequest, isAdmin } = useAuth();
  const [post, setPost] = useState({ title: "", content: "", tags: "" });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const fetchPost = async () => {
      if (!user || !token) {
        toast.error("You must be logged in.");
        navigate("/login");
        return;
      }

      try {
        setLoading(true);
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
    
    if (!user || !token) {
      toast.error("You must be logged in.");
      navigate("/login");
      return;
    }

    if (!post.title.trim() || !post.content.trim()) {
      toast.error("Title and content cannot be empty.");
      return;
    }

    setSaving(true);

    try {
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

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8 lg:py-12">
          <div className="flex items-center justify-center min-h-[60vh]">
            <div className="text-center space-y-6">
              <div className="relative">
                <div className="w-16 h-16 mx-auto">
                  <div className="absolute inset-0 rounded-full border-4 border-blue-200 animate-pulse"></div>
                  <div className="absolute inset-0 rounded-full border-4 border-blue-600 border-t-transparent animate-spin"></div>
                </div>
              </div>
              <div className="space-y-2">
                <h3 className="text-xl font-semibold text-gray-800">Loading Post</h3>
                <p className="text-gray-600">Please wait while we fetch your content...</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-6 lg:py-10">
        {/* Navigation */}
        <div className="mb-6 lg:mb-10">
          <button 
            onClick={() => navigate(`/posts/${id}`)}
            className="group inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-600 hover:text-blue-600 transition-colors duration-200 rounded-lg hover:bg-white/60 backdrop-blur-sm"
          >
            <svg className="w-4 h-4 transition-transform group-hover:-translate-x-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Post
          </button>
        </div>

        {/* Main Content */}
        <div className="max-w-4xl mx-auto">
          <div className="bg-white/70 backdrop-blur-xl rounded-2xl lg:rounded-3xl shadow-xl border border-white/20 overflow-hidden">
            
            {/* Header */}
            <div className="bg-gradient-to-r from-blue-600 to-indigo-600 px-6 sm:px-8 lg:px-10 py-6 lg:py-8">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 lg:w-12 lg:h-12 bg-white/20 rounded-xl flex items-center justify-center">
                  <svg className="w-5 h-5 lg:w-6 lg:h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                </div>
                <div>
                  <h1 className="text-2xl lg:text-3xl font-bold text-white">Edit Post</h1>
                  <p className="text-blue-100 text-sm lg:text-base">Update your content and share your thoughts</p>
                </div>
              </div>
            </div>

            {/* Form */}
            <form onSubmit={handleUpdate} className="p-6 sm:p-8 lg:p-10 space-y-8">
              
              {/* Title Input */}
              <div className="space-y-3">
                <label htmlFor="title" className="flex items-center gap-2 text-sm lg:text-base font-semibold text-gray-800">
                  <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                  </svg>
                  Post Title *
                </label>
                <div className="relative">
                  <input
                    id="title"
                    type="text"
                    className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 lg:py-4 text-base lg:text-lg bg-white/70 backdrop-blur-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 placeholder-gray-400 disabled:opacity-60 disabled:cursor-not-allowed"
                    placeholder="Enter an engaging title for your post..."
                    value={post.title}
                    onChange={(e) => setPost({ ...post, title: e.target.value })}
                    required
                    disabled={saving}
                    maxLength="200"
                  />
                  <div className="absolute bottom-2 right-3 text-xs text-gray-400">
                    {post.title.length}/200
                  </div>
                </div>
              </div>

              {/* Content Textarea */}
              <div className="space-y-3">
                <label htmlFor="content" className="flex items-center gap-2 text-sm lg:text-base font-semibold text-gray-800">
                  <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Post Content *
                </label>
                <div className="relative">
                  <textarea
                    id="content"
                    className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 lg:py-4 text-base lg:text-lg bg-white/70 backdrop-blur-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 placeholder-gray-400 resize-vertical min-h-[200px] lg:min-h-[300px] disabled:opacity-60 disabled:cursor-not-allowed"
                    placeholder="Share your thoughts, ideas, and insights here..."
                    value={post.content}
                    onChange={(e) => setPost({ ...post, content: e.target.value })}
                    required
                    disabled={saving}
                    rows={12}
                  />
                  <div className="absolute bottom-3 right-3 text-xs text-gray-400 bg-white/80 rounded px-2 py-1">
                    {post.content.length} characters
                  </div>
                </div>
              </div>

              {/* Tags Input */}
              <div className="space-y-3">
                <label htmlFor="tags" className="flex items-center gap-2 text-sm lg:text-base font-semibold text-gray-800">
                  <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                  </svg>
                  Tags <span className="text-gray-500 font-normal">(optional)</span>
                </label>
                <div className="space-y-2">
                  <input
                    id="tags"
                    type="text"
                    className="w-full border-2 border-gray-200 rounded-xl px-4 py-3 lg:py-4 text-base lg:text-lg bg-white/70 backdrop-blur-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all duration-200 placeholder-gray-400 disabled:opacity-60 disabled:cursor-not-allowed"
                    placeholder="technology, programming, webdev, react..."
                    value={post.tags}
                    onChange={(e) => setPost({ ...post, tags: e.target.value })}
                    disabled={saving}
                  />
                  <div className="flex items-center gap-2 text-xs lg:text-sm text-gray-500">
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Separate tags with commas. Tags help others discover your content.
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row gap-4 pt-8 border-t border-gray-200">
                <button
                  type="button"
                  onClick={() => navigate(`/posts/${id}`)}
                  className="flex-1 sm:flex-none inline-flex items-center justify-center gap-2 px-6 lg:px-8 py-3 lg:py-4 bg-gray-500 hover:bg-gray-600 text-white font-semibold rounded-xl transition-all duration-200 transform hover:scale-105 active:scale-95 shadow-lg hover:shadow-xl disabled:opacity-60 disabled:cursor-not-allowed disabled:transform-none"
                  disabled={saving}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                  <span className="text-sm lg:text-base">Cancel</span>
                </button>
                
                <button
                  type="submit"
                  className="flex-1 sm:flex-auto inline-flex items-center justify-center gap-2 px-6 lg:px-8 py-3 lg:py-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold rounded-xl transition-all duration-200 transform hover:scale-105 active:scale-95 shadow-lg hover:shadow-xl disabled:opacity-60 disabled:cursor-not-allowed disabled:transform-none"
                  disabled={saving || !post.title.trim() || !post.content.trim()}
                >
                  {saving ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      <span className="text-sm lg:text-base">Saving...</span>
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      <span className="text-sm lg:text-base">Update Post</span>
                    </>
                  )}
                </button>
              </div>

              {/* Tips Section */}
              <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 lg:p-6">
                <div className="flex items-start gap-3">
                  <div className="w-5 h-5 bg-blue-600 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                    <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div className="space-y-2">
                    <h4 className="font-semibold text-blue-900 text-sm lg:text-base">Writing Tips</h4>
                    <ul className="text-sm text-blue-800 space-y-1">
                      <li>• Use a clear, descriptive title that captures your main idea</li>
                      <li>• Structure your content with paragraphs for better readability</li>
                      <li>• Add relevant tags to help others discover your post</li>
                      {!isAdmin() && <li>• Your changes will need admin approval before being published</li>}
                    </ul>
                  </div>
                </div>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EditPost;