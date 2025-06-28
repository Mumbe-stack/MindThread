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

  // Vote on post only (removed comment voting)
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

  // Vote buttons component (only for posts now)
  const VoteButtons = ({ score = 0, upvotes = 0, downvotes = 0, userVote = null, onVote }) => (
    <div className="flex items-center bg-gray-50 rounded-xl p-2 space-x-1">
      {/* Upvote */}
      <button
        onClick={() => onVote(1)}
        disabled={votesLoading.post || !user}
        className={`flex items-center justify-center w-10 h-10 rounded-lg transition-all duration-200 transform hover:scale-105 ${
          userVote === 1
            ? "bg-gradient-to-r from-green-500 to-emerald-500 text-white shadow-lg"
            : "bg-white text-gray-600 hover:bg-green-50 hover:text-green-600 shadow-sm"
        } ${!user ? "opacity-50 cursor-not-allowed" : "cursor-pointer hover:shadow-md"}`}
        title={user ? "Upvote" : "Login to vote"}
      >
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M3.293 9.707a1 1 0 010-1.414l6-6a1 1 0 011.414 0l6 6a1 1 0 01-1.414 1.414L11 5.414V17a1 1 0 11-2 0V5.414L4.707 9.707a1 1 0 01-1.414 0z" clipRule="evenodd" />
        </svg>
      </button>

      {/* Score Display */}
      <div className="flex flex-col items-center min-w-[60px] px-3 py-2 bg-white rounded-lg shadow-sm">
        <span className={`font-bold text-lg leading-none ${
          score > 0 ? "text-green-600" : score < 0 ? "text-red-600" : "text-gray-600"
        }`}>
          {score}
        </span>
        <span className="text-xs text-gray-500 font-medium">score</span>
      </div>

      {/* Downvote */}
      <button
        onClick={() => onVote(-1)}
        disabled={votesLoading.post || !user}
        className={`flex items-center justify-center w-10 h-10 rounded-lg transition-all duration-200 transform hover:scale-105 ${
          userVote === -1
            ? "bg-gradient-to-r from-red-500 to-rose-500 text-white shadow-lg"
            : "bg-white text-gray-600 hover:bg-red-50 hover:text-red-600 shadow-sm"
        } ${!user ? "opacity-50 cursor-not-allowed" : "cursor-pointer hover:shadow-md"}`}
        title={user ? "Downvote" : "Login to vote"}
      >
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M16.707 10.293a1 1 0 010 1.414l-6 6a1 1 0 01-1.414 0l-6-6a1 1 0 111.414-1.414L9 14.586V3a1 1 0 012 0v11.586l4.293-4.293a1 1 0 011.414 0z" clipRule="evenodd" />
        </svg>
      </button>

      {/* Loading */}
      {votesLoading.post && (
        <div className="flex items-center justify-center w-10 h-10">
          <div className="animate-spin rounded-full h-5 w-5 border-2 border-blue-500 border-t-transparent"></div>
        </div>
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
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <div className="text-center py-16">
            <div className="relative">
              <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent mx-auto mb-6"></div>
              <div className="absolute inset-0 animate-ping rounded-full h-12 w-12 border-4 border-blue-300 mx-auto opacity-20"></div>
            </div>
            <p className="text-gray-600 text-lg font-medium">Loading post...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <div className="bg-white rounded-2xl shadow-lg border border-red-200 p-8">
            <div className="text-center">
              <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Oops! Something went wrong</h2>
              <p className="text-red-600 font-medium mb-6">{error}</p>
              <Link 
                to="/posts" 
                className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-medium rounded-xl hover:from-blue-700 hover:to-indigo-700 transition-all duration-200 transform hover:scale-105 shadow-lg"
              >
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
                Back to Posts
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!post) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <div className="text-center py-16">
            <div className="w-20 h-20 bg-gray-200 rounded-full flex items-center justify-center mx-auto mb-6">
              <svg className="w-10 h-10 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h2 className="text-3xl font-bold text-gray-900 mb-4">Post not found</h2>
            <p className="text-gray-600 mb-8">The post you're looking for doesn't exist or has been removed.</p>
            <Link 
              to="/posts" 
              className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-medium rounded-xl hover:from-blue-700 hover:to-indigo-700 transition-all duration-200 transform hover:scale-105 shadow-lg"
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              Back to Posts
            </Link>
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
          <Link 
            to="/posts" 
            className="inline-flex items-center text-blue-600 hover:text-blue-800 font-medium transition-colors duration-200 group"
          >
            <svg className="w-4 h-4 mr-2 transition-transform group-hover:-translate-x-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Posts
          </Link>
        </div>

        {/* Post */}
        <article className={`bg-white/80 backdrop-blur-sm border rounded-3xl shadow-xl overflow-hidden transition-all duration-300 hover:shadow-2xl ${
          !post.is_approved ? "ring-2 ring-orange-300 ring-opacity-50" : ""
        } ${post.is_flagged ? "ring-2 ring-red-300 ring-opacity-50" : ""}`}>
          
          <div className="p-6 sm:p-8 lg:p-10">
            {/* Post Header */}
            <header className="mb-8">
              <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-gray-900 mb-6 leading-tight">
                {post.title}
                <div className="flex flex-wrap gap-2 mt-3">
                  {!post.is_approved && (
                    <span className="inline-flex items-center text-xs sm:text-sm text-orange-700 font-semibold bg-orange-100 px-3 py-1 rounded-full border border-orange-200">
                      <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
                      </svg>
                      Pending Approval
                    </span>
                  )}
                  {post.is_flagged && (
                    <span className="inline-flex items-center text-xs sm:text-sm text-red-700 font-semibold bg-red-100 px-3 py-1 rounded-full border border-red-200">
                      <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M3 6a3 3 0 013-3h10a1 1 0 01.8 1.6L14.25 8l2.55 3.4A1 1 0 0116 13H6a1 1 0 00-1 1v3a1 1 0 11-2 0V6z" clipRule="evenodd" />
                      </svg>
                      Flagged
                    </span>
                  )}
                </div>
              </h1>
              
              {/* Author and Meta Info */}
              <div className="flex flex-col sm:flex-row sm:items-center sm:space-x-6 space-y-3 sm:space-y-0 text-sm text-gray-600 mb-6">
                <div className="flex items-center">
                  {post.author?.avatar_url && (
                    <img 
                      src={post.author.avatar_url} 
                      alt={`${getAuthorName()}'s avatar`}
                      className="w-8 h-8 rounded-full mr-3 ring-2 ring-gray-200"
                      onError={(e) => { e.target.style.display = 'none'; }}
                    />
                  )}
                  <span className="font-semibold text-gray-800">By {getAuthorName()}</span>
                </div>
                <div className="flex items-center">
                  <svg className="w-4 h-4 mr-2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>{formatDate(post.created_at)}</span>
                </div>
                {post.updated_at !== post.created_at && (
                  <div className="flex items-center text-amber-600">
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                    <span>Edited {formatDate(post.updated_at)}</span>
                  </div>
                )}
              </div>

              {/* Post Stats */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
                <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl p-4 text-center border border-green-100">
                  <div className={`text-2xl font-bold ${
                    post.vote_score > 0 ? "text-green-600" : 
                    post.vote_score < 0 ? "text-red-600" : "text-gray-600"
                  }`}>
                    {post.vote_score || 0}
                  </div>
                  <div className="text-xs text-gray-600 font-medium">Score</div>
                </div>
                <div className="bg-gradient-to-br from-blue-50 to-cyan-50 rounded-xl p-4 text-center border border-blue-100">
                  <div className="text-2xl font-bold text-blue-600">{post.total_votes || 0}</div>
                  <div className="text-xs text-gray-600 font-medium">Votes</div>
                </div>
                <div className="bg-gradient-to-br from-pink-50 to-rose-50 rounded-xl p-4 text-center border border-pink-100">
                  <div className="text-2xl font-bold text-pink-600">{post.likes_count || post.likes || 0}</div>
                  <div className="text-xs text-gray-600 font-medium">Likes</div>
                </div>
                <div className="bg-gradient-to-br from-purple-50 to-indigo-50 rounded-xl p-4 text-center border border-purple-100">
                  <div className="text-2xl font-bold text-purple-600">{comments.length}</div>
                  <div className="text-xs text-gray-600 font-medium">Comments</div>
                </div>
              </div>
            </header>

            {/* Post Content */}
            <div className="prose prose-lg max-w-none mb-8">
              <div className="bg-gray-50 rounded-2xl p-6 lg:p-8 border border-gray-200">
                <p className="text-gray-800 text-lg leading-relaxed whitespace-pre-wrap font-medium">
                  {post.content}
                </p>
              </div>
            </div>

            {/* Tags */}
            {post.tags && (
              <div className="flex flex-wrap gap-2 mb-8">
                {post.tags.split(',').map((tag, index) => (
                  <span
                    key={index}
                    className="inline-flex items-center px-4 py-2 text-sm bg-gradient-to-r from-gray-100 to-gray-200 text-gray-700 rounded-full border border-gray-300 font-medium hover:from-gray-200 hover:to-gray-300 transition-colors"
                  >
                    <span className="text-blue-600 mr-1">#</span>
                    {tag.trim()}
                  </span>
                ))}
              </div>
            )}

            {/* Voting and Like System */}
            <div className="border-t border-gray-200 pt-8">
              <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between space-y-6 lg:space-y-0">
                <div className="flex flex-col sm:flex-row sm:items-center space-y-4 sm:space-y-0 sm:space-x-8">
                  {/* Vote Buttons */}
                  <div className="flex items-center space-x-3">
                    <span className="text-sm text-gray-700 font-semibold">Vote:</span>
                    <VoteButtons
                      score={post.vote_score || 0}
                      upvotes={post.upvotes || 0}
                      downvotes={post.downvotes || 0}
                      userVote={post.userVote}
                      onVote={handlePostVote}
                    />
                  </div>

                  {/* Like Button */}
                  <div className="flex items-center space-x-3">
                    <span className="text-sm text-gray-700 font-semibold">Like:</span>
                    <div className="bg-gray-50 rounded-xl p-2">
                      <LikeButton 
                        type="post" 
                        id={post.id}
                        initialLikes={post.likes_count || post.likes || 0}
                        initialLiked={post.liked_by_user || false}
                      />
                    </div>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex flex-col sm:flex-row space-y-3 sm:space-y-0 sm:space-x-3">
                  {/* Author Controls */}
                  {user?.id === post.user_id && (
                    <div className="flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-2">
                      <Link
                        to={`/posts/${post.id}/edit`}
                        className="inline-flex items-center justify-center px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-medium rounded-xl hover:from-blue-700 hover:to-indigo-700 transition-all duration-200 transform hover:scale-105 shadow-lg"
                      >
                        <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                        Edit Post
                      </Link>
                      <button
                        onClick={handleDeletePost}
                        className="inline-flex items-center justify-center px-4 py-2 bg-gradient-to-r from-red-600 to-rose-600 text-white font-medium rounded-xl hover:from-red-700 hover:to-rose-700 transition-all duration-200 transform hover:scale-105 shadow-lg"
                      >
                        <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                        Delete Post
                      </button>
                    </div>
                  )}

                  {/* Admin Controls */}
                  {user?.is_admin && (
                    <div className="flex flex-col sm:flex-row space-y-2 sm:space-y-0 sm:space-x-2">
                      {!post.is_approved ? (
                        <>
                          <button
                            onClick={() => handleApprovePost(true)}
                            className="inline-flex items-center justify-center px-4 py-2 bg-gradient-to-r from-green-600 to-emerald-600 text-white font-medium rounded-xl hover:from-green-700 hover:to-emerald-700 transition-all duration-200 transform hover:scale-105 shadow-lg"
                          >
                            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                            </svg>
                            Approve Post
                          </button>
                          <button
                            onClick={() => handleApprovePost(false)}
                            className="inline-flex items-center justify-center px-4 py-2 bg-gradient-to-r from-red-600 to-rose-600 text-white font-medium rounded-xl hover:from-red-700 hover:to-rose-700 transition-all duration-200 transform hover:scale-105 shadow-lg"
                          >
                            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                            Reject Post
                          </button>
                        </>
                      ) : (
                        <button
                          onClick={() => handleApprovePost(false)}
                          className="inline-flex items-center justify-center px-4 py-2 bg-gradient-to-r from-orange-600 to-amber-600 text-white font-medium rounded-xl hover:from-orange-700 hover:to-amber-700 transition-all duration-200 transform hover:scale-105 shadow-lg"
                        >
                          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728L5.636 5.636m12.728 12.728L18.364 5.636M5.636 18.364l12.728-12.728" />
                          </svg>
                          Unapprove Post
                        </button>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Admin Vote Management */}
          {user?.is_admin && (
            <div className="bg-gradient-to-r from-red-50 to-pink-50 border-t border-red-200 p-6">
              <h3 className="text-lg font-bold text-red-800 mb-4 flex items-center">
                <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" clipRule="evenodd" />
                </svg>
                Admin: Vote Management
              </h3>
              
              <div className="flex flex-col sm:flex-row space-y-3 sm:space-y-0 sm:space-x-3 mb-6">
                <button
                  onClick={fetchAdminVotes}
                  className="inline-flex items-center justify-center px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-medium rounded-xl hover:from-blue-700 hover:to-indigo-700 transition-all duration-200 transform hover:scale-105 shadow-lg"
                >
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                  View All Votes ({(post.upvotes || 0) + (post.downvotes || 0)})
                </button>
                <button
                  onClick={resetAllVotes}
                  className="inline-flex items-center justify-center px-6 py-3 bg-gradient-to-r from-red-600 to-rose-600 text-white font-medium rounded-xl hover:from-red-700 hover:to-rose-700 transition-all duration-200 transform hover:scale-105 shadow-lg"
                >
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Reset All Votes
                </button>
              </div>

              {/* Admin Votes List */}
              {adminVotesVisible && (
                <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-lg">
                  <h4 className="font-semibold mb-4 text-gray-900">Individual Votes:</h4>
                  {adminVotes.length === 0 ? (
                    <div className="text-center py-8">
                      <svg className="w-12 h-12 text-gray-400 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
                      </svg>
                      <p className="text-gray-500 font-medium">No votes found.</p>
                    </div>
                  ) : (
                    <div className="space-y-3 max-h-80 overflow-y-auto custom-scrollbar">
                      {adminVotes.map((vote) => (
                        <div
                          key={vote.id}
                          className="flex items-center justify-between p-4 bg-gray-50 rounded-xl border hover:bg-gray-100 transition-colors"
                        >
                          <div className="flex items-center space-x-4">
                            <span
                              className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-bold shadow-lg ${
                                vote.value === 1 ? "bg-gradient-to-r from-green-500 to-emerald-500" : "bg-gradient-to-r from-red-500 to-rose-500"
                              }`}
                            >
                              {vote.value === 1 ? "+" : "-"}
                            </span>
                            <div>
                              <span className="font-semibold text-gray-900">{vote.username}</span>
                              <span className="text-gray-500 text-sm ml-2">(ID: {vote.user_id})</span>
                              {vote.created_at && (
                                <div className="text-gray-400 text-xs mt-1">
                                  {formatDate(vote.created_at)}
                                </div>
                              )}
                            </div>
                          </div>
                          <button
                            onClick={() => deleteAdminVote(vote.id)}
                            className="px-4 py-2 bg-gradient-to-r from-red-500 to-rose-500 text-white text-sm font-medium rounded-lg hover:from-red-600 hover:to-rose-600 transition-all duration-200 transform hover:scale-105 shadow-lg"
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
        <section className="mt-12">
          <div className="bg-white/80 backdrop-blur-sm rounded-3xl shadow-xl border border-gray-200">
            <div className="p-6 sm:p-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center">
                <svg className="w-6 h-6 mr-3 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                Comments ({comments.length})
              </h2>
              <CommentBox 
                postId={post.id} 
                onCommentSubmit={refreshComments}
                comments={comments}
              />
            </div>
          </div>
        </section>
      </div>

      {/* Custom Scrollbar Styles */}
      <style jsx>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 8px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: #f1f5f9;
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #cbd5e1;
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: #94a3b8;
        }
      `}</style>
    </div>
  );
};

export default SinglePost;