import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import LikeButton from "../components/LikeButton";
import toast from "react-hot-toast";

const VITE_API_URL = import.meta.env.VITE_API_URL || "https://mindthread-1.onrender.com";

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
      const res = await fetch(`${VITE_API_URL}/api/posts`, {
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
      
      // Fetch vote scores for each post
      for (const post of postsArray) {
        await fetchPostVotes(post.id);
      }
      
      return postsArray;
    } catch (err) {
      throw new Error(err.message || "Failed to fetch posts");
    }
  };

  const fetchPostVotes = async (postId) => {
    try {
      const res = await fetch(`${VITE_API_URL}/api/votes/post/${postId}/score`);
      if (res.ok) {
        const data = await res.json();
        setPosts(prev => prev.map(post => 
          post.id === postId 
            ? { 
                ...post, 
                vote_score: data.score, 
                upvotes: data.upvotes, 
                downvotes: data.downvotes,
                total_votes: data.total_votes
              }
            : post
        ));
      }
    } catch (error) {
      console.error("Error fetching post votes:", error);
    }
  };

  const handleVote = async (postId, value) => {
    if (!user || !token) {
      toast.error("Please login to vote");
      return;
    }

    if (votesLoading[postId]) return;

    setVotesLoading(prev => ({ ...prev, [postId]: true }));

    try {
      const res = await fetch(`${VITE_API_URL}/api/votes/post`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({
          post_id: postId,
          value: value,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setPosts(prev => prev.map(post => 
          post.id === postId 
            ? { 
                ...post, 
                vote_score: data.score, 
                upvotes: data.upvotes, 
                downvotes: data.downvotes,
                userVote: data.user_vote
              }
            : post
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
      console.error("Error voting:", error);
      toast.error("Network error while voting");
    } finally {
      setVotesLoading(prev => ({ ...prev, [postId]: false }));
    }
  };

  // Vote buttons component
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
          <path fillRule="evenodd" d="M3.293 9.707a1 1 0 010-1.414l6-6a1 1 0 011.414 0l6 6a1 1 0 01-1.414 1.414L11 5.414V17a1 1 0 11-2 0V5.414L4.707 9.707a1 1 0 01-1.414 0z" clipRule="evenodd" />
        </svg>
      </button>

      {/* Score Display */}
      <div className="text-center">
        <span className={`font-bold text-sm ${
          (post.vote_score || 0) > 0 ? "text-green-600" : 
          (post.vote_score || 0) < 0 ? "text-red-600" : "text-gray-600"
        }`}>
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
          <path fillRule="evenodd" d="M16.707 10.293a1 1 0 010 1.414l-6 6a1 1 0 01-1.414 0l-6-6a1 1 0 111.414-1.414L9 14.586V3a1 1 0 012 0v11.586l4.293-4.293a1 1 0 011.414 0z" clipRule="evenodd" />
        </svg>
      </button>

      {/* Loading indicator */}
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
  }, []);

  return (
    <div className="max-w-5xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold text-indigo-800">All Posts</h1>
        {user && (
          <Link
            to="/posts/new"
            className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 transition-colors"
          >
            Create New Post
          </Link>
        )}
      </div>

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
              className="border rounded shadow hover:shadow-md transition bg-white"
            >
              <div className="p-4 flex space-x-3">
                {/* Vote Section */}
                <VoteButtons post={post} />

                {/* Post Content */}
                <div className="flex-1">
                  <Link to={`/posts/${post.id}`} className="block">
                    <h2 className="text-xl font-semibold text-blue-700 hover:text-indigo-600 transition-colors">
                      {post.title}
                    </h2>
                    <p className="text-gray-600 mt-1 mb-3">
                      {post.content?.length > 120
                        ? `${post.content.slice(0, 120)}...`
                        : post.content}
                    </p>
                  </Link>

                  {/* Post Meta & Actions */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4 text-sm text-gray-500">
                      <span>By User #{post.user_id}</span>
                      <span>{new Date(post.created_at).toLocaleDateString()}</span>
                      {post.total_votes > 0 && (
                        <span className="text-indigo-600 font-medium">
                          {post.total_votes} vote{post.total_votes !== 1 ? 's' : ''}
                        </span>
                      )}
                    </div>
                    
                    {/* Like Button & User Actions */}
                    <div className="flex items-center space-x-3">
                      <LikeButton 
                        type="post" 
                        id={post.id}
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                        }}
                      />
                      
                      {/* User Actions */}
                      {user?.id === post.user_id && (
                        <div className="flex items-center space-x-2">
                          <Link
                            to={`/posts/${post.id}/edit`}
                            className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded hover:bg-blue-200"
                            onClick={(e) => e.stopPropagation()}
                          >
                            Edit
                          </Link>
                          <button
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              if (window.confirm("Delete this post?")) {
                                // Add delete functionality
                                console.log("Delete post", post.id);
                              }
                            }}
                            className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded hover:bg-red-200"
                          >
                            Delete
                          </button>
                        </div>
                      )}

                      {/* Admin Actions */}
                      {user?.is_admin && user?.id !== post.user_id && (
                        <div className="flex items-center space-x-2">
                          <span className="text-xs text-red-600 font-medium">🛡️</span>
                          <Link
                            to={`/posts/${post.id}/edit`}
                            className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded hover:bg-purple-200"
                            onClick={(e) => e.stopPropagation()}
                          >
                            Edit
                          </Link>
                          <button
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              if (window.confirm("Admin delete this post?")) {
                                console.log("Admin delete post", post.id);
                              }
                            }}
                            className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded hover:bg-red-200"
                          >
                            Delete
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