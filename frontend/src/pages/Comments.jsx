import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import toast from "react-hot-toast";

const VITE_API_URL =
  import.meta.env.VITE_API_URL || "https://mindthread-1.onrender.com";

const Comments = ({ postId }) => {
  const { user, token } = useAuth();
  const [comments, setComments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [votesLoading, setVotesLoading] = useState({});
  const [error, setError] = useState("");

  // Fetch comments (via the post endpoint)
  const fetchComments = async () => {
    const headers = { "Content-Type": "application/json", Accept: "application/json" };
    if (token) headers.Authorization = `Bearer ${token}`;

    const res = await fetch(`${VITE_API_URL}/api/posts/${postId}`, {
      method: "GET",
      credentials: "include",
      headers,
    });
    if (!res.ok) {
      const txt = await res.text();
      throw new Error(`HTTP ${res.status}: ${txt}`);
    }
    const data = await res.json();
    // Initialize vote fields
    return (data.comments || []).map((c) => ({
      ...c,
      vote_score: 0,
      upvotes: 0,
      downvotes: 0,
      userVote: null,
    }));
  };

  // Fetch vote score for one comment
  const fetchCommentVotes = async (commentId) => {
    try {
      const res = await fetch(`${VITE_API_URL}/api/votes/comment/${commentId}/score`);
      if (!res.ok) return;
      const data = await res.json();
      setComments((prev) =>
        prev.map((c) =>
          c.id === commentId
            ? { ...c, vote_score: data.score, upvotes: data.upvotes, downvotes: data.downvotes }
            : c
        )
      );
    } catch (e) {
      console.error("Error fetching comment votes:", e);
    }
  };

  // Vote on a comment
  const handleVote = async (commentId, value) => {
    if (!user || !token) {
      toast.error("Please login to vote");
      return;
    }
    if (votesLoading[commentId]) return;

    setVotesLoading((s) => ({ ...s, [commentId]: true }));
    try {
      const res = await fetch(`${VITE_API_URL}/api/votes/comment`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ comment_id: commentId, value }),
      });
      const data = await res.json();
      if (res.ok) {
        setComments((prev) =>
          prev.map((c) =>
            c.id === commentId
              ? {
                  ...c,
                  vote_score: data.score,
                  upvotes: data.upvotes,
                  downvotes: data.downvotes,
                  userVote: data.user_vote,
                }
              : c
          )
        );
        toast.success(data.message || (value === 1 ? "Upvoted" : "Downvoted"));
      } else {
        toast.error(data.error || "Failed to vote");
      }
    } catch (e) {
      console.error("Voting error:", e);
      toast.error("Network error while voting");
    } finally {
      setVotesLoading((s) => ({ ...s, [commentId]: false }));
    }
  };

  // Admin-only flag/unflag
  const handleFlag = async (commentId, isFlagged) => {
    if (!user || !token) {
      toast.error("Login required");
      return;
    }
    if (!user.is_admin) {
      toast.error("Only admins can flag/unflag");
      return;
    }
    try {
      const res = await fetch(
        `${VITE_API_URL}/api/admin/comments/${commentId}/flag`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ is_flagged: isFlagged }),
        }
      );
      const data = await res.json();
      if (res.ok) {
        setComments((prev) =>
          prev.map((c) =>
            c.id === commentId ? { ...c, is_flagged: isFlagged } : c
          )
        );
        toast.success(data.message || (isFlagged ? "Flagged" : "Unflagged"));
      } else {
        toast.error(data.error || "Failed to flag");
      }
    } catch (e) {
      console.error("Flag error:", e);
      toast.error("Network error while flagging");
    }
  };

  // Single comment component
  const CommentItem = ({ comment }) => (
    <div className="border rounded-lg p-4 mb-4 bg-white">
      <div className="flex justify-between items-start">
        <div>
          <p className="text-gray-800">{comment.content}</p>
          <p className="mt-2 text-xs text-gray-500">
            By <span className="font-medium">{comment.author?.username}</span> on{" "}
            {new Date(comment.created_at).toLocaleString()}
          </p>
        </div>
        {comment.is_flagged && (
          <span className="text-xs text-yellow-800 bg-yellow-100 px-2 py-1 rounded-full">
            ⚠️ Flagged
          </span>
        )}
      </div>

      <div className="mt-3 flex items-center space-x-4">
        {/* Upvote */}
        <button
          onClick={() => handleVote(comment.id, 1)}
          disabled={votesLoading[comment.id] || !user}
          className={`p-1 rounded ${
            comment.userVote === 1
              ? "bg-green-100 text-green-700 border border-green-300"
              : "bg-gray-100 text-gray-600 hover:bg-green-50 hover:text-green-600"
          } ${!user ? "opacity-50 cursor-not-allowed" : ""}`}
          title={user ? "Upvote" : "Login to vote"}
        >
          ▲
        </button>

        <span className="text-sm font-bold text-gray-700">
          {comment.vote_score}
        </span>

        <button
          onClick={() => handleVote(comment.id, -1)}
          disabled={votesLoading[comment.id] || !user}
          className={`p-1 rounded ${
            comment.userVote === -1
              ? "bg-red-100 text-red-700 border border-red-300"
              : "bg-gray-100 text-gray-600 hover:bg-red-50 hover:text-red-600"
          } ${!user ? "opacity-50 cursor-not-allowed" : ""}`}
          title={user ? "Downvote" : "Login to vote"}
        >
          ▼
        </button>

        {/* Admin flag button */}
        {user?.is_admin && (
          <button
            onClick={() => {
              const ok = window.confirm(
                comment.is_flagged
                  ? "Unflag this comment?"
                  : "Flag this comment as inappropriate?"
              );
              if (ok) handleFlag(comment.id, !comment.is_flagged);
            }}
            className={`ml-auto text-xs px-2 py-1 rounded ${
              comment.is_flagged
                ? "bg-yellow-100 text-yellow-700 hover:bg-yellow-200"
                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
            }`}
          >
            {comment.is_flagged ? "Unflag" : "Flag"}
          </button>
        )}
      </div>
    </div>
  );

  // Load comments + votes
  useEffect(() => {
    setLoading(true);
    fetchComments()
      .then((list) => {
        setComments(list);
        setError("");
        return list;
      })
      .then((list) => {
        // fetch votes in parallel
        list.forEach((c) => fetchCommentVotes(c.id));
      })
      .catch((err) => {
        setError(err.message);
      })
      .finally(() => setLoading(false));
  }, [postId]);

  if (loading) {
    return <p className="text-center text-gray-500">Loading comments…</p>;
  }
  if (error) {
    return <p className="text-center text-red-500">{error}</p>;
  }
  if (comments.length === 0) {
    return <p className="text-center text-gray-500">No comments yet.</p>;
  }

  return (
    <div>
      {comments.map((comment) => (
        <CommentItem key={comment.id} comment={comment} />
      ))}
    </div>
  );
};

export default Comments;
