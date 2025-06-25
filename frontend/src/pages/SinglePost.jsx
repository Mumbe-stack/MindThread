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

  const fetchPost = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE_URL}/api/posts/${id}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });

      if (response.status === 404) {
        setError("Post not found");
        return;
      }

      if (!response.ok) throw new Error("Failed to fetch post");

      const data = await response.json();
      setPost(data);
    } catch (err) {
      toast.error("Failed to load post");
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchComments = async () => {
    try {
      setCommentsLoading(true);

      const res = await fetch(`${API_BASE_URL}/api/comments?post_id=${id}`);
      const data = await res.json();
      setComments(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error(err);
      setComments([]);
    } finally {
      setCommentsLoading(false);
    }
  };

  const refreshComments = () => fetchComments();

  useEffect(() => {
    if (id) {
      fetchPost();
      fetchComments();
    }
  }, [id]);

  const handleDeletePost = async () => {
    if (!user || post.user_id !== user.id) {
      toast.error("You can only delete your own posts");
      return;
    }
    if (!window.confirm("Are you sure you want to delete this post?")) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/posts/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      if (response.ok) {
        toast.success("Post deleted");
        navigate("/");
      } else {
        const data = await response.json();
        toast.error(data.error || "Failed to delete post");
      }
    } catch (err) {
      toast.error("Delete failed");
    }
  };

  const toggleLikePost = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/posts/${id}/like`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const updated = await response.json();
        setPost((prev) => ({ ...prev, likes: updated.likes }));
      } else {
        toast.error("Failed to like/unlike post");
      }
    } catch {
      toast.error("Error liking post");
    }
  };

  const toggleLikeComment = async (commentId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/comments/${commentId}/like/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const updated = await response.json();
        setComments((prev) =>
          prev.map((c) => (c.id === commentId ? { ...c, likes: updated.likes } : c))
        );
      } else {
        toast.error("Failed to like/unlike comment");
      }
    } catch {
      toast.error("Error liking comment");
    }
  };

  const isPostLiked = () => post?.liked_by?.includes(user?.id);
  const isCommentLiked = (comment) => comment?.liked_by?.includes(user?.id);

  const formatDate = (date) =>
    new Date(date).toLocaleString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });

  if (loading) return <p className="text-center p-6">Loading...</p>;
  if (error) return <p className="text-center text-red-600 p-6">{error}</p>;
  if (!post) return <p className="text-center p-6">Post not found</p>;

  return (
    <div className="max-w-4xl mx-auto p-6">
      <Link to="/" className="text-indigo-600 hover:underline mb-4 inline-block">← Back</Link>

      <article className="bg-white border p-6 rounded-lg shadow-sm">
        <header className="mb-4">
          <h1 className="text-3xl font-bold">{post.title}</h1>
          <p className="text-sm text-gray-500">By User #{post.user_id} • {formatDate(post.created_at)}</p>
        </header>

        <p className="mb-4 text-gray-800 whitespace-pre-wrap">{post.content}</p>

        <div className="flex items-center gap-4">
          {user && (
            <button
              onClick={toggleLikePost}
              className={`px-3 py-1 rounded ${
                isPostLiked()
                  ? "bg-red-100 text-red-600 border border-red-300"
                  : "bg-gray-100 text-gray-600 border"
              }`}
            >
              {isPostLiked() ? "♥ Unlike" : "♡ Like"} ({post.likes || 0})
            </button>
          )}

          {user?.id === post.user_id && (
            <>
              <Link to={`/posts/${post.id}/edit`} className="bg-blue-500 text-white px-3 py-1 rounded">
                Edit
              </Link>
              <button onClick={handleDeletePost} className="bg-red-600 text-white px-3 py-1 rounded">
                Delete
              </button>
            </>
          )}
        </div>
      </article>

      <section className="mt-8">
        <h2 className="text-xl font-semibold mb-4">Comments ({comments.length})</h2>

        {user ? (
          <CommentBox postId={post.id} onCommentSubmit={refreshComments} />
        ) : (
          <p className="text-center text-gray-500">Please <Link to="/login" className="text-indigo-600">log in</Link> to comment</p>
        )}

        <div className="mt-6 space-y-4">
          {commentsLoading ? (
            <p className="text-gray-500">Loading comments...</p>
          ) : comments.length === 0 ? (
            <p className="text-gray-400">No comments yet.</p>
          ) : (
            comments.map((comment) => (
              <div key={comment.id} className="bg-gray-50 border p-4 rounded">
                <p className="text-gray-800 mb-2 whitespace-pre-wrap">{comment.content}</p>
                <div className="flex justify-between text-xs text-gray-500">
                  <span>By User #{comment.user_id}</span>
                  <time>{formatDate(comment.created_at)}</time>
                </div>
                {user && (
                  <button
                    onClick={() => toggleLikeComment(comment.id)}
                    className={`mt-2 px-2 py-1 text-sm rounded ${
                      isCommentLiked(comment)
                        ? "text-red-600 bg-red-100 border border-red-300"
                        : "text-gray-600 bg-gray-100 border"
                    }`}
                  >
                    {isCommentLiked(comment) ? "♥ Unlike" : "♡ Like"} ({comment.likes || 0})
                  </button>
                )}
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  );
};

export default SinglePost;
