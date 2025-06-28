import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import CommentBox from "../components/CommentBox";
import toast from "react-hot-toast";

const VITE_API_URL = import.meta.env.VITE_API_URL || "https://mindthread-1.onrender.com";

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

  const fetchPost = async () => {
    try {
      setLoading(true);
      const res = await fetch(`${VITE_API_URL}/api/posts/${id}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        credentials: "include",
      });
      if (!res.ok) throw new Error("Failed to fetch post");
      const data = await res.json();
      setPost(data);
      // Fetch vote data for the post
      await fetchPostVotes(data.id);
    } catch (err) {
      toast.error("Could not load post");
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchPostVotes = async (postId) => {
    try {
      const res = await fetch(`${VITE_API_URL}/api/votes/post/${postId}/score`);
      if (res.ok) {
        const data = await res.json();
        setPost(prev => ({
          ...prev,
          vote_score: data.score,
          upvotes: data.upvotes,
          downvotes: data.downvotes,
          total_votes: data.total_votes
        }));
      }
    } catch (error) {
      console.error("Error fetching post votes:", error);
    }
  };

  const fetchComments = async () => {
    try {
      setCommentsLoading(true);
     
      const headers = {
        "Content-Type": "application/json"
      };
      
      if (token) {
        headers.Authorization = `Bearer ${token}`;
      }
      
      const res = await fetch(`${VITE_API_URL}/api/comments?post_id=${id}`, {
        headers,
        credentials: "include",
      });
      
      if (!res.ok) {
        throw new Error(`Failed to fetch comments: ${res.status}`);
      }
      
      const data = await res.json();
      const commentsArray = Array.isArray(data) ? data : [];
      setComments(commentsArray);
      
      // Fetch vote scores for each comment
      commentsArray.forEach(comment => fetchCommentVotes(comment.id));
    } catch (err) {
      setComments([]);
    } finally {
      setCommentsLoading(false);
    }
  };

  const fetchCommentVotes = async (commentId) => {
    try {
      const res = await fetch(`${VITE_API_URL}/api/votes/comment/${commentId}/score`);
      if (res.ok) {
        const data = await res.json();
        setComments(prev => prev.map(comment => 
          comment.id === commentId 
            ? { 
                ...comment, 
                vote_score: data.score, 
                upvotes: data.upvotes, 
                downvotes: data.downvotes,
                total_votes: data.total_votes
              }
            : comment
        ));
      }
    } catch (error) {
      console.error("Error fetching comment votes:", error);
    }
  };

  const refreshComments = async () => {
    await fetchComments();
  };

  useEffect(() => {
    if (id) {
      fetchPost();
      fetchComments();
    }
  }, [id]); 

  // NEW: Vote on post
  const handlePostVote = async (value) => {
    if (!user || !token) {
      toast.error("Please login to vote");
      return;
    }

    if (votesLoading.post) return;

    setVotesLoading(prev => ({ ...prev, post: true }));

    try {
      const res = await fetch(`${VITE_API_URL}/api/votes/post`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({
          post_id: post.id,
          value: value,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setPost(prev => ({
          ...prev,
          vote_score: data.score,
          upvotes: data.upvotes,
          downvotes: data.downvotes,
          userVote: data.user_vote
        }));
        
        if (data.message === "Vote removed") {
          toast.success("Vote removed");
        } else {
          toast.success(`${value === 1 ? "Upvoted" : "Downvoted"}`);
        }
      } else {
        const errorData = await res.json();
        toast.error(errorData.error || "Failed to vote");
      }
    } catch (error) {
      console.error("Error voting on post:", error);
      toast.error("Network error while voting");
    } finally {
      setVotesLoading(prev => ({ ...prev, post: false }));
    }
  };

  // NEW: Vote on comment
  const handleCommentVote = async (commentId, value) => {
    if (!user || !token) {
      toast.error("Please login to vote");
      return;
    }

    if (votesLoading[`comment_${commentId}`]) return;

    setVotesLoading(prev => ({ ...prev, [`comment_${commentId}`]: true }));

    try {
      const res = await fetch(`${VITE_API_URL}/api/votes/comment`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({
          comment_id: commentId,
          value: value,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setComments(prev => prev.map(comment => 
          comment.id === commentId 
            ? { 
                ...comment, 
                vote_score: data.score, 
                upvotes: data.upvotes, 
                downvotes: data.downvotes,
                userVote: data.user_vote
              }
            : comment
        ));
        
        if (data.message === "Vote removed") {
          toast.success("Vote removed");
        } else {
          toast.success(`${value === 1 ? "Upvoted" : "Downvoted"}`);
        }
      } else {
        const errorData = await res.json();
        toast.error(errorData.error || "Failed to vote");
      }
    } catch (error) {
      console.error("Error voting on comment:", error);
      toast.error("Network error while voting");
    } finally {
      setVotesLoading(prev => ({ ...prev, [`comment_${commentId}`]: false }));
    }
  };

  // EXISTING: Like functions (keeping for backward compatibility)
  const toggleLikePost = async () => {
    if (!user || !token) {
      toast.error("Please log in to like posts");
      return;
    }

    try {
      const res = await fetch(`${VITE_API_URL}/api/posts/${id}/like`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        credentials: "include",
      });

      if (res.ok) {
        const data = await res.json();
        setPost((prev) => ({
          ...prev,
          likes: data.likes || 0,
          liked_by: data.liked_by || []
        }));
        toast.success(data.message || "Post like toggled");
      } else {
        const errorData = await res.json();
        toast.error(errorData.error || "Failed to like/unlike post");
      }
    } catch (error) {
      toast.error("Server error while toggling post like");
    }
  };

  const toggleLikeComment = async (commentId) => {
    if (!user || !token) {
      toast.error("Please log in to like comments");
      return;
    }

    try {
      const res = await fetch(`${VITE_API_URL}/api/comments/${commentId}/like`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        credentials: "include",
      });

      if (res.ok) {
        const data = await res.json();
        setComments((prev) =>
          prev.map((c) =>
            c.id === commentId
              ? { 
                  ...c, 
                  likes: data.likes || 0, 
                  liked_by: data.liked_by || []
                }
              : c
          )
        );
        toast.success(data.message || "Comment like toggled");
      } else {
        const errorData = await res.json();
        toast.error(errorData.error || "Failed to like/unlike comment");
      }
    } catch (error) {
      toast.error("Error toggling comment like");
    }
  };

  // NEW: Admin functions
  const fetchAdminVotes = async () => {
    if (!user?.is_admin || !token) return;

    try {
      const res = await fetch(`${VITE_API_URL}/api/votes/admin/post/${post.id}/votes`, {
        headers: { "Authorization": `Bearer ${token}` },
      });

      if (res.ok) {
        const data = await res.json();
        setAdminVotes(data.votes);
        setAdminVotesVisible(true);
      } else {
        toast.error("Failed to fetch admin votes");
      }
    } catch (error) {
      console.error("Error fetching admin votes:", error);
      toast.error("Network error");
    }
  };

  const deleteAdminVote = async (voteId) => {
    if (!user?.is_admin || !token) return;

    const confirmed = window.confirm("Delete this vote?");
    if (!confirmed) return;

    try {
      const res = await fetch(`${VITE_API_URL}/api/votes/admin/vote/${voteId}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` },
      });

      if (res.ok) {
        toast.success("Vote deleted");
        fetchAdminVotes();
        fetchPostVotes(post.id);
      } else {
        toast.error("Failed to delete vote");
      }
    } catch (error) {
      console.error("Error deleting vote:", error);
      toast.error("Network error");
    }
  };

  const resetAllVotes = async () => {
    if (!user?.is_admin || !token) return;

    const confirmed = window.confirm(`Delete ALL votes on "${post.title}"? This cannot be undone.`);
    if (!confirmed) return;

    try {
      const res = await fetch(`${VITE_API_URL}/api/votes/admin/reset/post/${post.id}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` },
      });

      if (res.ok) {
        const data = await res.json();
        toast.success(`${data.votes_deleted} votes deleted`);
        setAdminVotes([]);
        setAdminVotesVisible(false);
        fetchPostVotes(post.id);
      } else {
        toast.error("Failed to reset votes");
      }
    } catch (error) {
      console.error("Error resetting votes:", error);
      toast.error("Network error");
    }
  };

  // NEW: Vote buttons component
  const VoteButtons = ({ type, itemId, score = 0, upvotes = 0, downvotes = 0, userVote = null, onVote }) => (
    <div className="flex items-center space-x-2">
      {/* Upvote */}
      <button
        onClick={() => onVote(1)}
        disabled={votesLoading[type === 'post' ? 'post' : `comment_${itemId}`] || !user}
        className={`flex items-center space-x-1 px-2 py-1 rounded transition-colors ${
          userVote === 1
            ? "bg-green-100 text-green-700 border border-green-300"
            : "bg-gray-100 text-gray-600 hover:bg-green-50 hover:text-green-600"
        } ${!user ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
        title={user ? "Upvote" : "Login to vote"}
      >
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M3.293 9.707a1 1 0 010-1.414l6-6a1 1 0 011.414 0l6 6a1 1 0 01-1.414 1.414L11 5.414V17a1 1 0 11-2 0V5.414L4.707 9.707a1 1 0 01-1.414 0z" clipRule="evenodd" />
        </svg>
        <span className="text-sm">{upvotes}</span>
      </button>

      {/* Score */}
      <div className="flex flex-col items-center">
        <span className={`font-medium text-sm ${
          score > 0 ? "text-green-600" : score < 0 ? "text-red-600" : "text-gray-600"
        }`}>
          {score}
        </span>
      </div>

      {/* Downvote */}
      <button
        onClick={() => onVote(-1)}
        disabled={votesLoading[type === 'post' ? 'post' : `comment_${itemId}`] || !user}
        className={`flex items-center space-x-1 px-2 py-1 rounded transition-colors ${
          userVote === -1
            ? "bg-red-100 text-red-700 border border-red-300"
            : "bg-gray-100 text-gray-600 hover:bg-red-50 hover:text-red-600"
        } ${!user ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
        title={user ? "Downvote" : "Login to vote"}
      >
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M16.707 10.293a1 1 0 010 1.414l-6 6a1 1 0 01-1.414 0l-6-6a1 1 0 111.414-1.414L9 14.586V3a1 1 0 012 0v11.586l4.293-4.293a1 1 0 011.414 0z" clipRule="evenodd" />
        </svg>
        <span className="text-sm">{downvotes}</span>
      </button>

      {/* Loading */}
      {votesLoading[type === 'post' ? 'post' : `comment_${itemId}`] && (
        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-900"></div>
      )}
    </div>
  );

  const isPostLiked = () => post?.liked_by?.includes(user?.id);
  const isCommentLiked = (comment) => comment?.liked_by?.includes(user?.id);

  const handleDeletePost = async () => {
    if (!user || post.user_id !== user.id) {
      toast.error("You can only delete your own posts");
      return;
    }
    if (!window.confirm("Are you sure you want to delete this post?")) return;

    try {
      const res = await fetch(`${VITE_API_URL}/api/posts/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
        credentials: "include",
      });
      if (res.ok) {
        toast.success("Post deleted");
        navigate("/");
      } else {
        toast.error("Delete failed");
      }
    } catch {
      toast.error("Server error on delete");
    }
  };

  const formatDate = (date) =>
    new Date(date).toLocaleString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });

  if (loading) return <p className="text-center p-6">Loading...</p>;
  if (error) return <p className="text-center text-red-600 p-6">{error}</p>;
  if (!post) return <p className="text-center p-6">Post not found</p>;

  return (
    <div className="max-w-4xl mx-auto p-6">
      <Link to="/" className="text-indigo-600 hover:underline mb-4 inline-block">
        ← Back
      </Link>

      <article className="bg-white border p-6 rounded-lg shadow-sm">
        <header className="mb-4">
          <h1 className="text-3xl font-bold">{post.title}</h1>
          <p className="text-sm text-gray-500">
            By User #{post.user_id} • {formatDate(post.created_at)}
          </p>
        </header>

        <p className="mb-4 text-gray-800 whitespace-pre-wrap">{post.content}</p>

        {/* NEW: Vote System + Existing Like System */}
        <div className="flex items-center gap-6 mb-4">
          {/* NEW: Vote Buttons */}
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-600 font-medium">Vote:</span>
            <VoteButtons
              type="post"
              itemId={post.id}
              score={post.vote_score || 0}
              upvotes={post.upvotes || 0}
              downvotes={post.downvotes || 0}
              userVote={post.userVote}
              onVote={handlePostVote}
            />
          </div>

          {/* EXISTING: Like Button (keeping for compatibility) */}
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-600 font-medium">Like:</span>
            {user ? (
              <button
                onClick={toggleLikePost}
                className={`px-3 py-1 rounded-md font-medium transition-colors ${
                  isPostLiked()
                    ? "bg-red-100 text-red-600 border border-red-300 hover:bg-red-200"
                    : "bg-gray-100 text-gray-700 border border-gray-300 hover:bg-gray-200"
                }`}
              >
                {isPostLiked() ? "♥ Unlike" : "♡ Like"} ({post.likes || 0})
              </button>
            ) : (
              <span className="px-3 py-1 rounded-md text-gray-500 bg-gray-100 border border-gray-300">
                ♡ Like ({post.likes || 0})
              </span>
            )}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-4">
          {user?.id === post.user_id && (
            <>
              <Link
                to={`/posts/${post.id}/edit`}
                className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
              >
                Edit
              </Link>
              <button
                onClick={handleDeletePost}
                className="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700"
              >
                Delete
              </button>
            </>
          )}
        </div>

        {/* NEW: Admin Controls */}
        {user?.is_admin && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mt-6">
            <h3 className="text-lg font-semibold text-red-800 mb-3">
              🛡️ Admin: Vote Management
            </h3>
            
            <div className="flex space-x-3 mb-4">
              <button
                onClick={fetchAdminVotes}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
              >
                View All Votes ({(post.upvotes || 0) + (post.downvotes || 0)})
              </button>
              <button
                onClick={resetAllVotes}
                className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
              >
                Reset All Votes
              </button>
            </div>

            {/* Admin Votes List */}
            {adminVotesVisible && (
              <div className="bg-white rounded border p-4">
                <h4 className="font-medium mb-3">Individual Votes:</h4>
                {adminVotes.length === 0 ? (
                  <p className="text-gray-500">No votes found.</p>
                ) : (
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {adminVotes.map((vote) => (
                      <div
                        key={vote.id}
                        className="flex items-center justify-between p-3 bg-gray-50 rounded"
                      >
                        <div className="flex items-center space-x-3">
                          <span
                            className={`w-6 h-6 rounded-full flex items-center justify-center text-white text-sm font-bold ${
                              vote.value === 1 ? "bg-green-500" : "bg-red-500"
                            }`}
                          >
                            {vote.value === 1 ? "+" : "-"}
                          </span>
                          <span className="font-medium">{vote.username}</span>
                          <span className="text-gray-500 text-sm">(ID: {vote.user_id})</span>
                        </div>
                        <button
                          onClick={() => deleteAdminVote(vote.id)}
                          className="px-3 py-1 bg-red-500 text-white text-sm rounded hover:bg-red-600"
                        >
                          Delete
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </article>

      <section className="mt-8">
        <h2 className="text-xl font-semibold mb-4">Comments ({comments.length})</h2>

        {user ? (
          <CommentBox postId={post.id} onCommentSubmit={refreshComments} />
        ) : (
          <p className="text-center text-gray-500">
            Please <Link to="/login" className="text-indigo-600">log in</Link> to comment
          </p>
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
                <div className="flex justify-between items-center text-xs text-gray-500 mb-3">
                  <span>By User #{comment.user_id}</span>
                  <time>{formatDate(comment.created_at)}</time>
                </div>
                
                {/* NEW: Vote System + Existing Like System for Comments */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    {/* NEW: Comment Vote Buttons */}
                    <div className="flex items-center space-x-2">
                      <span className="text-xs text-gray-600">Vote:</span>
                      <VoteButtons
                        type="comment"
                        itemId={comment.id}
                        score={comment.vote_score || 0}
                        upvotes={comment.upvotes || 0}
                        downvotes={comment.downvotes || 0}
                        userVote={comment.userVote}
                        onVote={(value) => handleCommentVote(comment.id, value)}
                      />
                    </div>

                    {/* EXISTING: Like Button for Comments */}
                    <div className="flex items-center space-x-2">
                      <span className="text-xs text-gray-600">Like:</span>
                      {user ? (
                        <button
                          onClick={() => toggleLikeComment(comment.id)}
                          className={`px-2 py-1 text-xs rounded transition-colors ${
                            isCommentLiked(comment)
                              ? "text-red-600 bg-red-100 border border-red-300 hover:bg-red-200"
                              : "text-gray-600 bg-gray-100 border border-gray-300 hover:bg-gray-200"
                          } cursor-pointer`}
                        >
                          {isCommentLiked(comment) ? "♥ Unlike" : "♡ Like"} ({comment.likes || 0})
                        </button>
                      ) : (
                        <span className="px-2 py-1 text-xs text-gray-500 bg-gray-100 border border-gray-300 rounded">
                          ♡ Like ({comment.likes || 0})
                        </span>
                      )}
                    </div>
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