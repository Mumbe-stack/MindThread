import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import CommentBox from "../components/CommentBox";
import toast from "react-hot-toast";


const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";

const SinglePost = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, token } = useAuth();
  
  const [post, setPost] = useState(null);
  const [comments, setComments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [commentsLoading, setCommentsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (id) {
      fetchPost();
      fetchComments();
    }
  }, [id]);

  const fetchPost = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch(`${API_BASE_URL}/api/posts/${id}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      });

      if (response.status === 404) {
        setError("Post not found");
        return;
      }

      if (!response.ok) {
        throw new Error(`Failed to fetch post: ${response.status}`);
      }

      const data = await response.json();
      setPost(data);
      
    } catch (err) {
      console.error("Failed to load post:", err);
      setError(err.message);
      toast.error("Failed to load post");
    } finally {
      setLoading(false);
    }
  };

  const fetchComments = async () => {
    try {
      setCommentsLoading(true);
      
      const response = await fetch(`${API_BASE_URL}/api/comments?post_id=${id}`);
      
      if (response.ok) {
        const data = await response.json();
        setComments(Array.isArray(data) ? data : []);
      } else {
        console.warn("Failed to fetch comments");
        setComments([]);
      }
    } catch (err) {
      console.error("Failed to load comments:", err);
      setComments([]);
    } finally {
      setCommentsLoading(false);
    }
  };

  const refreshComments = () => {
    fetchComments();
  };

  const handleDeletePost = async () => {
    if (!user || post.user_id !== user.id) {
      toast.error("You can only delete your own posts");
      return;
    }

    const confirmed = window.confirm("Are you sure you want to delete this post?");
    if (!confirmed) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/posts/${id}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`
        }
      });

      if (response.ok) {
        toast.success("Post deleted successfully");
        navigate("/");
      } else {
        const data = await response.json();
        toast.error(data.error || "Failed to delete post");
      }
    } catch (error) {
      console.error("Delete error:", error);
      toast.error("Failed to delete post");
    }
  };

  const formatDate = (dateString) => {
    try {
      return new Date(dateString).toLocaleString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return 'Unknown date';
    }
  };

  const renderTags = (tags) => {
    if (!tags) return null;
    
    const tagArray = tags.split(',').map(tag => tag.trim()).filter(Boolean);
    if (tagArray.length === 0) return null;
    
    return (
      <div className="flex flex-wrap gap-2 mb-4">
        {tagArray.map((tag, index) => (
          <span
            key={index}
            className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm"
          >
            #{tag}
          </span>
        ))}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded mb-4"></div>
          <div className="h-4 bg-gray-200 rounded mb-2"></div>
          <div className="h-4 bg-gray-200 rounded mb-2"></div>
          <div className="h-4 bg-gray-200 rounded w-3/4 mb-6"></div>
          <div className="h-20 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="text-center py-12">
          <div className="text-red-600 mb-4">
            <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            {error === "Post not found" ? "Post Not Found" : "Error Loading Post"}
          </h3>
          <p className="text-gray-600 mb-4">{error}</p>
          <div className="space-x-4">
            <button
              onClick={() => navigate("/")}
              className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700"
            >
              Back to Home
            </button>
            {error !== "Post not found" && (
              <button
                onClick={fetchPost}
                className="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700"
              >
                Try Again
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (!post) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <p className="text-center p-4">Post not found.</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      {/* Back Navigation */}
      <div className="mb-6">
        <Link
          to="/"
          className="inline-flex items-center text-indigo-600 hover:text-indigo-800"
        >
          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to Posts
        </Link>
      </div>

      {/* Post Content */}
      <article className="bg-white rounded-lg shadow-sm border border-gray-200 p-8 mb-8">
        <header className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">
            {post.title}
          </h1>
          
          {renderTags(post.tags)}
          
          <div className="flex items-center justify-between text-sm text-gray-500 pb-4 border-b border-gray-200">
            <span>By User #{post.user_id}</span>
            <time dateTime={post.created_at}>
              {formatDate(post.created_at)}
            </time>
          </div>
        </header>

        <div className="prose max-w-none mb-6">
          <div className="text-gray-700 leading-relaxed whitespace-pre-wrap">
            {post.content}
          </div>
        </div>

        {/* Post Actions */}
        {user && user.id === post.user_id && (
          <div className="flex gap-4 pt-4 border-t border-gray-200">
            <Link
              to={`/posts/${post.id}/edit`}
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
            >
              Edit Post
            </Link>
            <button
              onClick={handleDeletePost}
              className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
            >
              Delete Post
            </button>
          </div>
        )}
      </article>

      {/* Comments Section */}
      <section className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-xl font-semibold mb-6">
          Comments ({comments.length})
        </h2>

        {/* Comment Form */}
        {user ? (
          <div className="mb-6">
            <CommentBox postId={post.id} onCommentSubmit={refreshComments} />
          </div>
        ) : (
          <div className="mb-6 p-4 bg-gray-50 rounded-lg text-center">
            <p className="text-gray-600 mb-2">Please log in to leave a comment</p>
            <Link
              to="/login"
              className="text-indigo-600 hover:text-indigo-800 font-medium"
            >
              Sign In
            </Link>
          </div>
        )}

        {/* Comments List */}
        <div className="space-y-4">
          {commentsLoading ? (
            <div className="animate-pulse space-y-4">
              {[...Array(3)].map((_, index) => (
                <div key={index} className="border p-4 rounded bg-gray-50">
                  <div className="h-4 bg-gray-200 rounded mb-2"></div>
                  <div className="h-3 bg-gray-200 rounded w-1/4"></div>
                </div>
              ))}
            </div>
          ) : comments.length === 0 ? (
            <div className="text-center py-8">
              <div className="text-gray-400 mb-2">
                <svg className="mx-auto h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
              </div>
              <p className="text-gray-500">No comments yet. Be the first to comment!</p>
            </div>
          ) : (
            comments.map((comment) => (
              <div
                key={comment.id}
                className="border border-gray-200 p-4 rounded-lg bg-gray-50"
              >
                <p className="text-gray-800 mb-2 whitespace-pre-wrap">
                  {comment.content}
                </p>
                <div className="flex items-center justify-between text-xs text-gray-500">
                  <span>By User #{comment.user_id}</span>
                  <time dateTime={comment.created_at}>
                    {formatDate(comment.created_at)}
                  </time>
                </div>
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  );
};

export default SinglePost;