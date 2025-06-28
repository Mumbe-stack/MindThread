import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import CommentBox from "../components/CommentBox";
import LikeButton from "../components/LikeButton";
import toast from "react-hot-toast";

const VITE_API_URL = import.meta.env.VITE_API_URL || "https://mindthread-1.onrender.com";

const SinglePost = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, token } = useAuth();

  const [post, setPost] = useState(null);
  const [comments, setComments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [votesLoading, setVotesLoading] = useState({});
  const [adminVotesVisible, setAdminVotesVisible] = useState(false);
  const [adminVotes, setAdminVotes] = useState([]);

  const fetchPost = async () => {
    try {
      setLoading(true);
      const headers = {
        "Content-Type": "application/json",
      };
      if (token) {
        headers.Authorization = `Bearer ${token}`;
      }

      const res = await fetch(`${VITE_API_URL}/api/posts/${id}`, {
        headers,
        credentials: "include",
      });
      
      if (!res.ok) {
        if (res.status === 404) {
          throw new Error("Post not found");
        }
        throw new Error("Failed to fetch post");
      }
      
      const data = await res.json();
      setPost(data);
      
      // Comments are included in the post response, or fetch separately
      if (data.comments && Array.isArray(data.comments)) {
        setComments(data.comments);
      } else {
        await fetchComments();
      }
    } catch (err) {
      console.error("Error fetching post:", err);
      setError(err.message);
      toast.error(err.message || "Could not load post");
    } finally {
      setLoading(false);
    }
  };

  const fetchComments = async () => {
    try {
      const headers = {
        "Content-Type": "application/json",
      };
      if (token) {
        headers.Authorization = `Bearer ${token}`;
      }
      
      // Use the correct endpoint for fetching post comments
      const res = await fetch(`${VITE_API_URL}/api/posts/${id}/comments`, {
        headers,
        credentials: "include",
      });
      
      if (res.ok) {
        const data = await res.json();
        const commentsArray = Array.isArray(data) ? data : [];
        setComments(commentsArray);
      } else {
        console.error("Failed to fetch comments:", res.status);
        setComments([]);
      }
    } catch (err) {
      console.error("Error fetching comments:", err);
      setComments([]);
    }
  };

  const refreshComments = async (newComment) => {
    if (newComment) {
      // Add the new comment to the list if it's approved or user is admin
      if (newComment.is_approved || (user && user.is_admin)) {
        setComments(prev => [...prev, newComment]);
      }
    } else {
      // Refresh all comments
      await fetchComments();
    }
  };

  useEffect(() => {
    if (id) {
      fetchPost();
    }
  }, [id, token]); 

  // Vote on post
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
        credentials: "include",
        body: JSON.stringify({
          post_id: parseInt(id),
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
          total_votes: data.total_votes,
          userVote: data.user_vote
        }));
        
        const action = data.user_vote === null ? "removed vote" : 
                      data.user_vote === 1 ? "upvoted" : "downvoted";
        toast.success(data.message || `Post ${action}`);
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

  // Vote on comment
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
        credentials: "include",
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
                total_votes: data.total_votes,
                userVote: data.user_vote
              }
            : comment
        ));
        
        const action = data.user_vote === null ? "removed vote" : 
                      data.user_vote === 1 ? "upvoted" : "downvoted";
        toast.success(data.message || `Comment ${action}`);
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

  // Admin functions
  const handleApprovePost = async (isApproved) => {
    if (!user?.is_admin || !token) {
      toast.error("Admin access required");
      return;
    }

    try {
      const res = await fetch(`${VITE_API_URL}/api/admin/posts/${id}/approve`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        credentials: "include",
        body: JSON.stringify({ is_approved: isApproved }),
      });

      const data = await res.json();

      if (res.ok) {
        setPost(prev => ({ ...prev, is_approved: isApproved }));
        toast.success(data.message || (isApproved ? "Post approved" : "Post rejected"));
      } else {
        toast.error(data.error || "Failed to update post approval");
      }
    } catch (err) {
      console.error("Approval error:", err);
      toast.error("Network error while updating post approval");
    }
  };

  const fetchAdminVotes = async () => {
    if (!user?.is_admin || !token) return;

    try {
      const res = await fetch(`${VITE_API_URL}/api/votes/admin/post/${post.id}/votes`, {
        headers: { "Authorization": `Bearer ${token}` },
        credentials: "include",
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
        credentials: "include",
      });

      if (res.ok) {
        toast.success("Vote deleted");
        fetchAdminVotes();
        // Refresh post to update vote counts
        fetchPost();
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
        credentials: "include",
      });

      if (res.ok) {
        const data = await res.json();
        toast.success(`${data.votes_deleted} votes deleted`);
        setAdminVotes([]);
        setAdminVotesVisible(false);
        // Refresh post to update vote counts
        fetchPost();
      } else {
        toast.error("Failed to reset votes");
      }
    } catch (error) {
      console.error("Error resetting votes:", error);
      toast.error("Network error");
    }
  };

  const handleDeletePost = async () => {
    if (!user || !token) {
      toast.error("Please login to delete posts");
      return;
    }

    if (post.user_id !== user.id && !user.is_admin) {
      toast.error("You can only delete your own posts");
      return;
    }

    if (!window.confirm("Are you sure you want to delete this post? This action cannot be undone.")) {
      return;
    }

    try {
      const res = await fetch(`${VITE_API_URL}/api/posts/${id}`, {
        method: "DELETE",
        headers: { 
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}` 
        },
        credentials: "include",
      });
      
      if (res.ok) {
        toast.success("Post deleted successfully");
        navigate("/posts");
      } else {
        const data = await res.json();
        toast.error(data.error || "Failed to delete post");
      }
    } catch (error) {
      console.error("Delete error:", error);
      toast.error("Network error while deleting post");
    }
  };

  // Vote buttons component
  const VoteButtons = ({ type, itemId, score = 0, upvotes = 0, downvotes = 0, userVote = null, onVote }) => (
    <div className="flex items-center space-x-2">
      {/* Upvote */}
      <button
        onClick={() => onVote(1)}
        disabled={votesLoading[type === 'post' ? 'post' : `comment_${itemId}`] || !user}
        className={`flex items-center space-x-1 px-3 py-1 rounded-lg transition-colors font-medium ${
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
      <div className="flex flex-col items-center px-2">
        <span className={`font-bold text-lg ${
          score > 0 ? "text-green-600" : score < 0 ? "text-red-600" : "text-gray-600"
        }`}>
          {score}
        </span>
        <span className="text-xs text-gray-500">score</span>
      </div>

      {/* Downvote */}
      <button
        onClick={() => onVote(-1)}
        disabled={votesLoading[type === 'post' ? 'post' : `comment_${itemId}`] || !user}
        className={`flex items-center space-x-1 px-3 py-1 rounded-lg transition-colors font-medium ${
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
        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-900 ml-2"></div>
      )}
    </div>
  );

  const formatDate = (date) => {
    try {
      return new Date(date).toLocaleString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return "Unknown date";
    }
  };

  const getAuthorName = () => {
    return post?.author?.username || post?.username || "Unknown";
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto mb-4"></div>
          <p className="text-gray-500">Loading post...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-600 font-medium text-center">{error}</p>
          <div className="text-center mt-4">
            <Link to="/posts" className="text-indigo-600 hover:underline">
              ← Back to Posts
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!post) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="text-center py-8">
          <p className="text-gray-500 text-xl">Post not found</p>
          <Link to="/posts" className="text-indigo-600 hover:underline mt-4 inline-block">
            ← Back to Posts
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      {/* Navigation */}
      <div className="mb-6">
        <Link to="/posts" className="text-indigo-600 hover:underline">
          ← Back to Posts
        </Link>
      </div>

      {/* Post */}
      <article className={`bg-white border rounded-lg shadow-lg overflow-hidden ${
        !post.is_approved ? "border-2 border-orange-300" : ""
      } ${post.is_flagged ? "border-2 border-red-300" : ""}`}>
        
        <div className="p-6">
          {/* Post Header */}
          <header className="mb-6">
            <h1 className="text-3xl font-bold text-gray-900 mb-4 flex items-center flex-wrap gap-2">
              {post.title}
              {!post.is_approved && (
                <span className="text-sm text-orange-700 font-semibold bg-orange-100 px-3 py-1 rounded-full">
                  ⏳ Pending Approval
                </span>
              )}
              {post.is_flagged && (
                <span className="text-sm text-red-700 font-semibold bg-red-100 px-3 py-1 rounded-full">
                  🚩 Flagged
                </span>
              )}
            </h1>
            
            {/* Author and Meta Info */}
            <div className="flex items-center space-x-4 text-sm text-gray-500 mb-4">
              <div className="flex items-center">
                {post.author?.avatar_url && (
                  <img 
                    src={post.author.avatar_url} 
                    alt={`${getAuthorName()}'s avatar`}
                    className="w-6 h-6 rounded-full mr-2"
                    onError={(e) => { e.target.style.display = 'none'; }}
                  />
                )}
                <span className="font-medium text-gray-700">By {getAuthorName()}</span>
              </div>
              <span>{formatDate(post.created_at)}</span>
              {post.updated_at !== post.created_at && (
                <span className="text-yellow-600">(edited {formatDate(post.updated_at)})</span>
              )}
            </div>

            {/* Post Stats */}
            <div className="flex items-center space-x-6 text-sm text-gray-500 mb-6">
              <span className={`font-medium ${
                post.vote_score > 0 ? "text-green-600" : 
                post.vote_score < 0 ? "text-red-600" : "text-gray-600"
              }`}>
                Score: {post.vote_score || 0}
              </span>
              <span className="text-blue-600">
                {post.total_votes || 0} {(post.total_votes || 0) === 1 ? "vote" : "votes"}
              </span>
              <span className="text-pink-600">
                {post.likes_count || post.likes || 0} {(post.likes_count || post.likes || 0) === 1 ? "like" : "likes"}
              </span>
              <span className="text-purple-600">
                {comments.length} {comments.length === 1 ? "comment" : "comments"}
              </span>
            </div>
          </header>

          {/* Post Content */}
          <div className="prose max-w-none mb-6">
            <p className="text-gray-800 text-lg leading-relaxed whitespace-pre-wrap">
              {post.content}
            </p>
          </div>

          {/* Tags */}
          {post.tags && (
            <div className="flex flex-wrap gap-2 mb-6">
              {post.tags.split(',').map((tag, index) => (
                <span
                  key={index}
                  className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded-full"
                >
                  #{tag.trim()}
                </span>
              ))}
            </div>
          )}

          {/* Voting and Like System */}
          <div className="flex items-center justify-between border-t pt-4">
            <div className="flex items-center space-x-6">
              {/* Vote Buttons */}
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

              {/* Like Button */}
              <div className="flex items-center space-x-2">
                <span className="text-sm text-gray-600 font-medium">Like:</span>
                <LikeButton 
                  type="post" 
                  id={post.id}
                  initialLikes={post.likes_count || post.likes || 0}
                  initialLiked={post.liked_by_user || false}
                />
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex items-center space-x-3">
              {/* Author Controls */}
              {user?.id === post.user_id && (
                <div className="flex items-center space-x-2">
                  <Link
                    to={`/posts/${post.id}/edit`}
                    className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    Edit Post
                  </Link>
                  <button
                    onClick={handleDeletePost}
                    className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors"
                  >
                    Delete Post
                  </button>
                </div>
              )}

              {/* Admin Controls */}
              {user?.is_admin && (
                <div className="flex items-center space-x-2">
                  {!post.is_approved ? (
                    <>
                      <button
                        onClick={() => handleApprovePost(true)}
                        className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors"
                      >
                        ✓ Approve Post
                      </button>
                      <button
                        onClick={() => handleApprovePost(false)}
                        className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors"
                      >
                        ✗ Reject Post
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={() => handleApprovePost(false)}
                      className="bg-orange-600 text-white px-4 py-2 rounded-lg hover:bg-orange-700 transition-colors"
                    >
                      Unapprove Post
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Admin Vote Management */}
        {user?.is_admin && (
          <div className="bg-red-50 border-t border-red-200 p-4">
            <h3 className="text-lg font-semibold text-red-800 mb-3">
              🛡️ Admin: Vote Management
            </h3>
            
            <div className="flex space-x-3 mb-4">
              <button
                onClick={fetchAdminVotes}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                View All Votes ({(post.upvotes || 0) + (post.downvotes || 0)})
              </button>
              <button
                onClick={resetAllVotes}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                Reset All Votes
              </button>
            </div>

            {/* Admin Votes List */}
            {adminVotesVisible && (
              <div className="bg-white rounded-lg border p-4">
                <h4 className="font-medium mb-3">Individual Votes:</h4>
                {adminVotes.length === 0 ? (
                  <p className="text-gray-500">No votes found.</p>
                ) : (
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {adminVotes.map((vote) => (
                      <div
                        key={vote.id}
                        className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
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
                          {vote.created_at && (
                            <span className="text-gray-400 text-xs">
                              {formatDate(vote.created_at)}
                            </span>
                          )}
                        </div>
                        <button
                          onClick={() => deleteAdminVote(vote.id)}
                          className="px-3 py-1 bg-red-500 text-white text-sm rounded-lg hover:bg-red-600 transition-colors"
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

      {/* Comments Section */}
      <section className="mt-8">
        <CommentBox 
          postId={post.id} 
          onCommentSubmit={refreshComments}
          comments={comments}
        />
      </section>
    </div>
  );
};

export default SinglePost;