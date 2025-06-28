import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import LikeButton from "../components/LikeButton";
import toast from "react-hot-toast";

const VITE_API_URL =
  import.meta.env.VITE_API_URL || "https://mindthread-1.onrender.com";

const Posts = () => {
  const { user, token } = useAuth();
  const [posts, setPosts] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [votesLoading, setVotesLoading] = useState({});

  const fetchPosts = async () => {
    const headers = {
      "Content-Type": "application/json",
      Accept: "application/json",
    };
    if (token) headers.Authorization = `Bearer ${token}`;

    try {
      // Use admin endpoint if user is admin, regular endpoint otherwise
      const endpoint = user?.is_admin 
        ? `${VITE_API_URL}/api/admin/posts` 
        : `${VITE_API_URL}/api/posts`;

      const res = await fetch(endpoint, {
        method: "GET",
        credentials: "include",
        headers,
      });

      const contentType = res.headers.get("content-type") || "";
      if (!res.ok) {
        const raw = await res.text();
        throw new Error(`HTTP ${res.status}: ${raw}`);
      }

      if (!contentType.includes("application/json")) {
        const raw = await res.text();
        throw new Error(`Expected JSON but received: ${raw.slice(0, 100)}`);
      }

      const data = await res.json();
      const postsArray = Array.isArray(data) ? data : [];

      // Posts now come with all stats from backend, no need for separate fetch
      return postsArray;
    } catch (err) {
      throw new Error(err.message || "Failed to fetch posts");
    }
  };

  const handleVote = async (postId, value) => {
    if (!user || !token) {
      toast.error("Please login to vote");
      return;
    }

    if (votesLoading[postId]) return;

    setVotesLoading((prev) => ({ ...prev, [postId]: true }));

    try {
      const res = await fetch(`${VITE_API_URL}/api/votes/post`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        credentials: "include",
        body: JSON.stringify({ post_id: postId, value }),
      });

      if (res.ok) {
        const data = await res.json();
        setPosts((prev) =>
          prev.map((post) =>
            post.id === postId
              ? {
                  ...post,
                  vote_score: data.score,
                  upvotes: data.upvotes,
                  downvotes: data.downvotes,
                  total_votes: data.total_votes,
                  userVote: data.user_vote,
                }
              : post
          )
        );
        toast.success(
          data.message || (value === 1 ? "Upvoted" : "Downvoted")
        );
      } else {
        const errorData = await res.json();
        toast.error(errorData.error || "Failed to vote");
      }
    } catch (error) {
      console.error("Error voting:", error);
      toast.error("Network error while voting");
    } finally {
      setVotesLoading((prev) => ({ ...prev, [postId]: false }));
    }
  };

  const handleApprovePost = async (postId, isApproved) => {
    if (!user?.is_admin || !token) {
      toast.error("Admin access required");
      return;
    }

    try {
      const res = await fetch(
        `${VITE_API_URL}/api/admin/posts/${postId}/approve`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          credentials: "include",
          body: JSON.stringify({ is_approved: isApproved }),
        }
      );

      const data = await res.json();

      if (res.ok) {
        toast.success(
          data.message || (isApproved ? "Post approved" : "Post rejected")
        );
        setPosts((prev) =>
          prev.map((post) =>
            post.id === postId ? { ...post, is_approved: isApproved } : post
          )
        );
      } else {
        toast.error(data.error || "Failed to update post approval");
      }
    } catch (err) {
      console.error("Approval error:", err);
      toast.error("Network error while updating post approval");
    }
  };

  const handleFlagPost = async (postId, isFlagged = true) => {
    if (!user?.is_admin || !token) {
      toast.error("Admin access required");
      return;
    }

    try {
      const res = await fetch(
        `${VITE_API_URL}/api/admin/posts/${postId}/flag`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          credentials: "include",
          body: JSON.stringify({ is_flagged: isFlagged }),
        }
      );

      const data = await res.json();

      if (res.ok) {
        toast.success(
          data.message || (isFlagged ? "Post flagged" : "Post unflagged")
        );
        setPosts((prev) =>
          prev.map((post) =>
            post.id === postId ? { ...post, is_flagged: isFlagged } : post
          )
        );
      } else {
        toast.error(data.error || "Failed to flag post");
      }
    } catch (err) {
      console.error("Flagging error:", err);
      toast.error("Network error while flagging post");
    }
  };

  const handleDeletePost = async (postId) => {
    if (!token) {
      toast.error("Please login to delete posts");
      return;
    }

    if (!window.confirm("Are you sure you want to delete this post? This action cannot be undone.")) {
      return;
    }

    try {
      const res = await fetch(`${VITE_API_URL}/api/posts/${postId}`, {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        credentials: "include",
      });

      if (res.ok) {
        toast.success("Post deleted successfully");
        setPosts((prev) => prev.filter((post) => post.id !== postId));
      } else {
        const data = await res.json();
        toast.error(data.error || "Failed to delete post");
      }
    } catch (err) {
      console.error("Delete error:", err);
      toast.error("Network error while deleting post");
    }
  };

  const VoteButtons = ({ post }) => (
    <div className="flex flex-col items-center space-y-1 mr-3">
      {/* Upvote */}
      <button
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          handleVote(post.id, 1);
        }}
        disabled={votesLoading[post.id] || !user}
        className={`p-1.5 rounded transition-colors ${
          post.userVote === 1
            ? "bg-green-100 text-green-700 border border-green-300"
            : "bg-gray-100 text-gray-600 hover:bg-green-50 hover:text-green-600"
        } ${!user ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
        title={user ? "Upvote" : "Login to vote"}
      >
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M3.293 9.707a1 1 0 010-1.414l6-6a1 1 0 011.414 0l6 6a1 1 0 01-1.414 1.414L11 5.414V17a1 1 0 11-2 0V5.414L4.707 9.707a1 1 0 01-1.414 0z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {/* Score */}
      <div className="text-center">
        <span
          className={`font-bold text-sm ${
            post.vote_score > 0
              ? "text-green-600"
              : post.vote_score < 0
              ? "text-red-600"
              : "text-gray-600"
          }`}
        >
          {post.vote_score || 0}
        </span>
        <div className="text-xs text-gray-500">
          {post.upvotes || 0}↑ {post.downvotes || 0}↓
        </div>
      </div>

      {/* Downvote */}
      <button
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          handleVote(post.id, -1);
        }}
        disabled={votesLoading[post.id] || !user}
        className={`p-1.5 rounded transition-colors ${
          post.userVote === -1
            ? "bg-red-100 text-red-700 border border-red-300"
            : "bg-gray-100 text-gray-600 hover:bg-red-50 hover:text-red-600"
        } ${!user ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
        title={user ? "Downvote" : "Login to vote"}
      >
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M16.707 10.293a1 1 0 010 1.414l-6 6a1 1 0 01-1.414 0l-6-6a1 1 0 111.414-1.414L9 14.586V3a1 1 0 012 0v11.586l4.293-4.293a1 1 0 011.414 0z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {votesLoading[post.id] && (
        <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-gray-900"></div>
      )}
    </div>
  );

  useEffect(() => {
    setLoading(true);
    fetchPosts()
      .then((data) => {
        setPosts(data);
        setError("");
      })
      .catch((err) => {
        setError(err.message);
        setPosts([]);
      })
      .finally(() => setLoading(false));
  }, [user]); // Re-fetch when user changes (login/logout)

  return (
    <div className="max-w-5xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold text-indigo-800">
          {user?.is_admin ? "All Posts (Admin View)" : "All Posts"}
        </h1>
        {user && (
          <Link
            to="/posts/new"
            className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors"
          >
            Create New Post
          </Link>
        )}
      </div>

      {user?.is_admin && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <h3 className="font-semibold text-blue-900 mb-2">👨‍💼 Admin Controls</h3>
          <p className="text-blue-700 text-sm">
            You can see all posts including unapproved ones. Use the controls below each post to approve, flag, or manage content.
          </p>
        </div>
      )}

      {loading && (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto mb-4"></div>
          <p className="text-gray-500">Loading posts...</p>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          <p className="text-red-600 font-medium text-center">{error}</p>
        </div>
      )}

      {!loading && posts.length === 0 && !error ? (
        <div className="text-center py-12">
          <div className="text-gray-500 text-xl mb-4">No posts available</div>
          {user ? (
            <Link
              to="/posts/new"
              className="bg-indigo-600 text-white px-6 py-3 rounded-lg hover:bg-indigo-700 transition-colors"
            >
              Create the first post!
            </Link>
          ) : (
            <p className="text-gray-600">
              <Link to="/login" className="text-indigo-600 hover:underline">
                Login
              </Link>{" "}
              to create posts
            </p>
          )}
        </div>
      ) : (
        <div className="grid gap-4">
          {posts.map((post) => (
            <div
              key={post.id}
              className={`border rounded shadow hover:shadow-md transition bg-white ${
                !post.is_approved ? "border-orange-300 bg-orange-50" : ""
              } ${post.is_flagged ? "border-red-300 bg-red-50" : ""}`}
            >
              <div className="p-4 flex space-x-3">
                <VoteButtons post={post} />
                <div className="flex-1">
                  <Link to={`/posts/${post.id}`} className="block">
                    <h2 className="text-xl font-semibold text-blue-700 hover:text-indigo-600 transition-colors flex items-center flex-wrap gap-2">
                      {post.title}
                      {!post.is_approved && (
                        <span className="text-xs text-orange-700 font-semibold bg-orange-100 px-2 py-0.5 rounded-full">
                          ⏳ Pending Approval
                        </span>
                      )}
                      {post.is_flagged && (
                        <span className="text-xs text-red-700 font-semibold bg-red-100 px-2 py-0.5 rounded-full">
                          🚩 Flagged
                        </span>
                      )}
                    </h2>
                    <p className="text-gray-600 mt-1 mb-3">
                      {post.content?.length > 120
                        ? `${post.content.slice(0, 120)}...`
                        : post.content}
                    </p>
                  </Link>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4 text-sm text-gray-500">
                      <span>
                        By{" "}
                        <span className="font-medium text-gray-700">
                          {post.author?.username || post.username || "Unknown"}
                        </span>
                      </span>
                      <span>
                        {new Date(post.created_at).toLocaleDateString()}
                      </span>
                      {(post.total_votes > 0 || post.likes_count > 0) && (
                        <div className="flex items-center space-x-2">
                          {post.total_votes > 0 && (
                            <span className="text-indigo-600 font-medium">
                              {post.total_votes} vote{post.total_votes !== 1 ? "s" : ""}
                            </span>
                          )}
                          {post.likes_count > 0 && (
                            <span className="text-pink-600 font-medium">
                              {post.likes_count} like{post.likes_count !== 1 ? "s" : ""}
                            </span>
                          )}
                        </div>
                      )}
                      {post.comments_count > 0 && (
                        <span className="text-blue-600 font-medium">
                          {post.comments_count} comment{post.comments_count !== 1 ? "s" : ""}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center space-x-2">
                      <LikeButton type="post" id={post.id} />
                      
                      {/* Author controls */}
                      {user?.id === post.user_id && (
                        <div className="flex items-center space-x-2">
                          <Link
                            to={`/posts/${post.id}/edit`}
                            className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded hover:bg-blue-200 transition-colors"
                          >
                            Edit
                          </Link>
                          <button
                            onClick={(e) => {
                              e.preventDefault();
                              handleDeletePost(post.id);
                            }}
                            className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded hover:bg-red-200 transition-colors"
                          >
                            Delete
                          </button>
                        </div>
                      )}

                      {/* Admin controls */}
                      {user?.is_admin && (
                        <div className="flex items-center space-x-2">
                          {!post.is_approved && (
                            <>
                              <button
                                onClick={(e) => {
                                  e.preventDefault();
                                  e.stopPropagation();
                                  handleApprovePost(post.id, true);
                                }}
                                className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded hover:bg-green-200 transition-colors"
                              >
                                ✓ Approve
                              </button>
                              <button
                                onClick={(e) => {
                                  e.preventDefault();
                                  e.stopPropagation();
                                  handleApprovePost(post.id, false);
                                }}
                                className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded hover:bg-red-200 transition-colors"
                              >
                                ✗ Reject
                              </button>
                            </>
                          )}
                          {post.is_approved && (
                            <button
                              onClick={(e) => {
                                e.preventDefault();
                                e.stopPropagation();
                                const confirm = window.confirm(
                                  "Remove approval from this post? It will become unapproved."
                                );
                                if (confirm) handleApprovePost(post.id, false);
                              }}
                              className="text-xs bg-orange-100 text-orange-700 px-2 py-1 rounded hover:bg-orange-200 transition-colors"
                            >
                              Unapprove
                            </button>
                          )}
                          <button
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              const confirm = window.confirm(
                                post.is_flagged
                                  ? "Unflag this post?"
                                  : "Flag this post as inappropriate?"
                              );
                              if (confirm) handleFlagPost(post.id, !post.is_flagged);
                            }}
                            className={`text-xs px-2 py-1 rounded transition-colors ${
                              post.is_flagged
                                ? "bg-yellow-100 text-yellow-700 hover:bg-yellow-200"
                                : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                            }`}
                          >
                            {post.is_flagged ? "🚩 Unflag" : "🚩 Flag"}
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Posts;