import { useEffect, useState } from "react"; 
import { useParams, useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import CommentBox from "../components/CommentBox";
import VoteButton from "../components/VoteButton";
import LikeButton from "../components/LikeButton";
import toast from "react-hot-toast";

const API = import.meta.env.VITE_API_URL || "https://mindthread-1.onrender.com";

const SinglePost = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, token } = useAuth();

  const [post, setPost] = useState(null);
  const [comments, setComments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [commentsLoading, setCommentsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [votesLoading, setVotesLoading] = useState({});
  const [adminVotesVisible, setAdminVotesVisible] = useState(false);
  const [adminVotes, setAdminVotes] = useState([]);

  /* Fetch post and comments on mount */
  useEffect(() => {
    fetchPost();
    fetchComments();
  }, [id]);

  const fetchPost = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/posts/${id}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        credentials: "include",
      });
      if (!res.ok) throw new Error("Failed to load post");
      const data = await res.json();
      setPost(data);
    } catch (err) {
      setError(err.message);
      toast.error("Could not load post");
    } finally {
      setLoading(false);
    }
  };

  const fetchComments = async () => {
    setCommentsLoading(true);
    try {
      const headers = { "Content-Type": "application/json" };
      if (token) headers.Authorization = `Bearer ${token}`;

      const res = await fetch(`${API}/api/posts/${id}`, {
        headers,
        credentials: "include",
      });
      if (!res.ok) throw new Error("Failed to load comments");
      const data = await res.json();
      setComments(data.comments || []);
    } catch {
      setComments([]);
    } finally {
      setCommentsLoading(false);
    }
  };

  /* Voting helpers */
  const handleVote = async ({ type, itemId, value }) => {
    if (!user) {
      toast.error("Login to vote");
      return;
    }
    const key = type === "post" ? "post" : `comment_${itemId}`;
    if (votesLoading[key]) return;
    setVotesLoading(v => ({ ...v, [key]: true }));

    try {
      const res = await fetch(`${API}/api/votes/${type}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(
          type === "post" ? { post_id: itemId, value } : { comment_id: itemId, value }
        ),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Vote failed");

      if (type === "post") {
        setPost(p => ({ ...p,
          vote_score: data.vote_score,
          upvotes: data.upvotes,
          downvotes: data.downvotes,
          user_vote: data.user_vote
        }));
      } else {
        setComments(cs =>
          cs.map(c =>
            c.id === itemId
              ? { ...c,
                  vote_score: data.vote_score,
                  upvotes: data.upvotes,
                  downvotes: data.downvotes,
                  user_vote: data.user_vote }
              : c
          )
        );
      }

      toast.success(data.message || "Vote updated");
    } catch (err) {
      toast.error(err.message);
    } finally {
      setVotesLoading(v => ({ ...v, [key]: false }));
    }
  };

  /* Like helpers */
  const handleLike = async ({ type, itemId }) => {
    if (!user) {
      toast.error("Login to like");
      return;
    }
    try {
      const url =
        type === "post"
          ? `${API}/api/posts/${id}/like`
          : `${API}/api/comments/${itemId}/like`;
      const res = await fetch(url, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        credentials: "include",
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Like failed");

      if (type === "post") {
        setPost(p => ({ ...p, liked_by_user: data.liked_by_user, likes_count: data.likes }));
      } else {
        setComments(cs =>
          cs.map(c =>
            c.id === itemId
              ? { ...c, liked_by_user: data.liked_by_user, likes_count: data.likes }
              : c
          )
        );
      }
      toast.success(data.message);
    } catch (err) {
      toast.error(err.message);
    }
  };

  /* Admin vote management */
  const fetchAdminVotes = async () => {
    if (!user?.is_admin) return;
    try {
      const res = await fetch(`${API}/api/votes/admin/post/${id}/votes`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Load votes failed");
      const { votes } = await res.json();
      setAdminVotes(votes);
      setAdminVotesVisible(true);
    } catch {
      toast.error("Unable to load admin votes");
    }
  };

  const deleteAdminVote = async voteId => {
    if (!user?.is_admin) return;
    if (!confirm("Delete this vote?")) return;
    try {
      const res = await fetch(`${API}/api/votes/admin/vote/${voteId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Delete failed");
      toast.success("Vote deleted");
      fetchAdminVotes();
      fetchPost();
    } catch {
      toast.error("Unable to delete vote");
    }
  };

  const resetAllVotes = async () => {
    if (!user?.is_admin) return;
    if (!confirm("Reset ALL votes?")) return;
    try {
      const res = await fetch(`${API}/api/votes/admin/reset/post/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Reset failed");
      toast.success(`${data.votes_deleted} votes removed`);
      setAdminVotes([]);
      setAdminVotesVisible(false);
      fetchPost();
    } catch {
      toast.error("Unable to reset votes");
    }
  };

  const handleDeletePost = async () => {
    if (user?.id !== post.user_id) {
      toast.error("Not your post");
      return;
    }
    if (!confirm("Delete post?")) return;
    try {
      const res = await fetch(`${API}/api/posts/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
        credentials: "include",
      });
      if (!res.ok) throw new Error("Delete failed");
      toast.success("Post deleted");
      navigate("/");
    } catch {
      toast.error("Unable to delete");
    }
  };

  const formatDate = iso =>
    new Date(iso).toLocaleString("en-US", {
      year: "numeric", month: "short", day: "numeric",
      hour: "2-digit", minute: "2-digit"
    });

  if (loading) return <p>Loading...</p>;
  if (error)   return <p className="text-red-600">{error}</p>;
  if (!post)   return <p>Post not found.</p>;

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      <Link to="/" className="text-indigo-600 hover:underline">
        ← Back to Posts
      </Link>

      <article className="bg-white shadow rounded p-6">
        <h1 className="text-2xl font-bold">{post.title}</h1>
        <p className="text-sm text-gray-500">
          By {post.author.username} • {formatDate(post.created_at)}
        </p>
        <div className="mt-4 prose whitespace-pre-wrap">{post.content}</div>

        <div className="flex items-center space-x-6 mt-6">
          {/* Vote */}
          <div className="flex items-center space-x-2">
            <span className="font-medium">Vote:</span>
            <VoteButton
              type="post"
              id={post.id}
              currentVote={post.user_vote}
              onVote={v => handleVote({ type: "post", itemId: post.id, value: v })}
            />
            <span>{post.vote_score || 0}</span>
          </div>

          {/* Like */}
          <div className="flex items-center space-x-2">
            <span className="font-medium">Like:</span>
            <LikeButton
              type="post"
              id={post.id}
              liked={post.liked_by_user}
              onClick={() => handleLike({ type: "post", itemId: post.id })}
            />
            <span>{post.likes_count}</span>
          </div>
        </div>

        {/* Post actions */}
        <div className="mt-4 space-x-3">
          {user?.id === post.user_id && (
            <>
              <Link
                to={`/posts/${post.id}/edit`}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                Edit
              </Link>
              <button
                onClick={handleDeletePost}
                className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
              >
                Delete
              </button>
            </>
          )}
        </div>

        {/* Admin controls */}
        {user?.is_admin && (
          <section className="mt-6 p-4 bg-red-50 border border-red-200 rounded">
            <h3 className="text-lg font-semibold text-red-800">
              Admin: Manage Votes
            </h3>
            <div className="mt-2 flex space-x-3">
              <button
                onClick={fetchAdminVotes}
                className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                View Votes
              </button>
              <button
                onClick={resetAllVotes}
                className="px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700"
              >
                Reset Votes
              </button>
            </div>
            {adminVotesVisible && (
              <div className="mt-4 space-y-2 max-h-60 overflow-y-auto">
                {adminVotes.length === 0 ? (
                  <p className="text-gray-500">No votes recorded.</p>
                ) : (
                  adminVotes.map(v => (
                    <div
                      key={v.id}
                      className="flex justify-between items-center p-2 bg-white border rounded"
                    >
                      <span>
                        {v.username} ({v.user_id}) —{" "}
                        <strong className={v.value === 1 ? "text-green-600" : "text-red-600"}>
                          {v.value > 0 ? `+${v.value}` : v.value}
                        </strong>
                      </span>
                      <button
                        onClick={() => deleteAdminVote(v.id)}
                        className="px-2 py-1 bg-red-500 text-white rounded hover:bg-red-600"
                      >
                        Delete
                      </button>
                    </div>
                  ))
                )}
              </div>
            )}
          </section>
        )}
      </article>

      {/* Comments Section */}
      <section>
        <h2 className="text-xl font-semibold">
          Comments ({post.comments_count})
        </h2>

        {user ? (
          <CommentBox postId={post.id} onCommentSubmit={fetchComments} />
        ) : (
          <p className="text-gray-500">
            <Link to="/login" className="text-indigo-600 hover:underline">
              Log in
            </Link>{" "}
            to comment.
          </p>
        )}

        <div className="mt-4 space-y-4">
          {commentsLoading ? (
            <p className="text-gray-500">Loading comments…</p>
          ) : comments.length === 0 ? (
            <p className="text-gray-400">No comments yet.</p>
          ) : (
            comments.map(c => (
              <div key={c.id} className="p-4 bg-gray-50 border rounded">
                <p className="whitespace-pre-wrap">{c.content}</p>
                <p className="text-xs text-gray-500 mt-1">
                  By {c.author.username} • {formatDate(c.created_at)}
                </p>

                <div className="flex items-center space-x-6 mt-2">
                  {/* Comment vote */}
                  <div className="flex items-center space-x-2">
                    <span className="text-sm">Vote:</span>
                    <VoteButton
                      type="comment"
                      id={c.id}
                      currentVote={c.user_vote}
                      onVote={v => handleVote({ type: "comment", itemId: c.id, value: v })}
                    />
                    <span>{c.vote_score || 0}</span>
                  </div>

                  {/* Comment like */}
                  <div className="flex items-center space-x-2">
                    <span className="text-sm">Like:</span>
                    <LikeButton
                      type="comment"
                      id={c.id}
                      liked={c.liked_by_user}
                      onClick={() => handleLike({ type: "comment", itemId: c.id })}
                    />
                    <span>{c.likes_count}</span>
                  </div>
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