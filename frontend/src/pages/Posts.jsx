import { useEffect, useState } from "react";

// Mock components and hooks for demo
const Link = ({ to, children, className, onClick }) => (
  <a href={to} className={className} onClick={(e) => { e.preventDefault(); onClick?.(e); console.log('Navigate to:', to); }}>
    {children}
  </a>
);

const useAuth = () => ({
  user: { id: 1, username: "johnDoe", is_admin: true },
  token: "mock-token"
});

const LikeButton = ({ type, id }) => (
  <button className="inline-flex items-center px-3 py-1.5 text-xs font-medium bg-pink-100 text-pink-700 rounded-lg hover:bg-pink-200 transition-colors duration-200">
    <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
      <path fillRule="evenodd" d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z" clipRule="evenodd" />
    </svg>
    Like
  </button>
);

const toast = {
  success: (msg) => console.log('Success:', msg),
  error: (msg) => console.log('Error:', msg)
};

const Posts = () => {
  const { user, token } = useAuth();
  const [posts, setPosts] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [votesLoading, setVotesLoading] = useState({});

  const fetchPosts = async () => {
    // Mock data for demonstration
    return [
      {
        id: 1,
        title: "Getting Started with React Hooks",
        content: "React Hooks have revolutionized the way we write React components. In this comprehensive guide, we'll explore useState, useEffect, and custom hooks to build more efficient applications.",
        created_at: "2024-01-15T10:30:00Z",
        author: { username: "techGuru" },
        username: "techGuru",
        user_id: 2,
        vote_score: 15,
        upvotes: 18,
        downvotes: 3,
        total_votes: 21,
        likes_count: 8,
        comments_count: 12,
        userVote: 1,
        is_approved: true,
        is_flagged: false
      },
      {
        id: 2,
        title: "The Future of Web Development",
        content: "As we move into 2024, web development continues to evolve. From AI-powered development tools to new frameworks, let's explore what's coming next in our industry.",
        created_at: "2024-01-14T15:45:00Z",
        author: { username: "webDevExpert" },
        username: "webDevExpert",
        user_id: 3,
        vote_score: -2,
        upvotes: 5,
        downvotes: 7,
        total_votes: 12,
        likes_count: 3,
        comments_count: 8,
        userVote: null,
        is_approved: false,
        is_flagged: false
      },
      {
        id: 3,
        title: "Building Responsive Design Systems",
        content: "Creating consistent, scalable design systems that work across all devices is crucial for modern web applications. Here's how to approach it systematically.",
        created_at: "2024-01-13T09:20:00Z",
        author: { username: "designPro" },
        username: "designPro",
        user_id: 4,
        vote_score: 8,
        upvotes: 10,
        downvotes: 2,
        total_votes: 12,
        likes_count: 15,
        comments_count: 6,
        userVote: -1,
        is_approved: true,
        is_flagged: true
      },
      {
        id: 4,
        title: "Understanding JavaScript Closures",
        content: "Closures are one of the most powerful features in JavaScript, yet they're often misunderstood. Let's break them down with practical examples.",
        created_at: "2024-01-12T14:10:00Z",
        author: { username: "jsNinja" },
        username: "jsNinja",
        user_id: 1,
        vote_score: 22,
        upvotes: 25,
        downvotes: 3,
        total_votes: 28,
        likes_count: 19,
        comments_count: 15,
        userVote: null,
        is_approved: true,
        is_flagged: false
      }
    ];
  };

  const handleVote = async (postId, value) => {
    if (!user || !token) {
      toast.error("Please login to vote");
      return;
    }

    if (votesLoading[postId]) return;

    setVotesLoading((prev) => ({ ...prev, [postId]: true }));

    try {
      // Mock successful vote
      const mockData = {
        score: value === 1 ? 16 : 14,
        upvotes: value === 1 ? 19 : 18,
        downvotes: value === 1 ? 3 : 4,
        total_votes: value === 1 ? 22 : 22,
        user_vote: value
      };

      setPosts((prev) =>
        prev.map((post) =>
          post.id === postId
            ? {
                ...post,
                vote_score: mockData.score,
                upvotes: mockData.upvotes,
                downvotes: mockData.downvotes,
                total_votes: mockData.total_votes,
                userVote: mockData.user_vote,
              }
            : post
        )
      );
      toast.success(value === 1 ? "Upvoted" : "Downvoted");
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
      toast.success(isApproved ? "Post approved" : "Post rejected");
      setPosts((prev) =>
        prev.map((post) =>
          post.id === postId ? { ...post, is_approved: isApproved } : post
        )
      );
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
      toast.success(isFlagged ? "Post flagged" : "Post unflagged");
      setPosts((prev) =>
        prev.map((post) =>
          post.id === postId ? { ...post, is_flagged: isFlagged } : post
        )
      );
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
      toast.success("Post deleted successfully");
      setPosts((prev) => prev.filter((post) => post.id !== postId));
    } catch (err) {
      console.error("Delete error:", err);
      toast.error("Network error while deleting post");
    }
  };

  const VoteButtons = ({ post }) => (
    <div className="flex flex-col items-center space-y-1 sm:space-y-2 mr-2 sm:mr-4 flex-shrink-0">
      {/* Upvote */}
      <button
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          handleVote(post.id, 1);
        }}
        disabled={votesLoading[post.id] || !user}
        className={`p-1.5 sm:p-2 rounded-lg transition-all duration-200 ${
          post.userVote === 1
            ? "bg-green-100 text-green-700 border border-green-300 shadow-sm"
            : "bg-gray-100 text-gray-600 hover:bg-green-50 hover:text-green-600 hover:shadow-sm"
        } ${!user ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
        title={user ? "Upvote" : "Login to vote"}
      >
        <svg className="w-3 h-3 sm:w-4 sm:h-4" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M3.293 9.707a1 1 0 010-1.414l6-6a1 1 0 011.414 0l6 6a1 1 0 01-1.414 1.414L11 5.414V17a1 1 0 11-2 0V5.414L4.707 9.707a1 1 0 01-1.414 0z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {/* Score */}
      <div className="text-center py-1">
        <span
          className={`font-bold text-xs sm:text-sm ${
            post.vote_score > 0
              ? "text-green-600"
              : post.vote_score < 0
              ? "text-red-600"
              : "text-gray-600"
          }`}
        >
          {post.vote_score || 0}
        </span>
        <div className="text-xs text-gray-500 leading-tight">
          <div>{post.upvotes || 0}↑</div>
          <div>{post.downvotes || 0}↓</div>
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
        className={`p-1.5 sm:p-2 rounded-lg transition-all duration-200 ${
          post.userVote === -1
            ? "bg-red-100 text-red-700 border border-red-300 shadow-sm"
            : "bg-gray-100 text-gray-600 hover:bg-red-50 hover:text-red-600 hover:shadow-sm"
        } ${!user ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
        title={user ? "Downvote" : "Login to vote"}
      >
        <svg className="w-3 h-3 sm:w-4 sm:h-4" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M16.707 10.293a1 1 0 010 1.414l-6 6a1 1 0 01-1.414 0l-6-6a1 1 0 111.414-1.414L9 14.586V3a1 1 0 012 0v11.586l4.293-4.293a1 1 0 011.414 0z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {votesLoading[post.id] && (
        <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-indigo-600"></div>
      )}
    </div>
  );

  useEffect(() => {
    setLoading(true);
    // Simulate loading delay for demo
    setTimeout(() => {
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
    }, 1000);
  }, [user]); // Re-fetch when user changes (login/logout)

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
        {/* Header Section */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 sm:p-6 mb-6 sm:mb-8">
          <div className="flex flex-col space-y-4 sm:flex-row sm:items-center sm:justify-between sm:space-y-0">
            <div>
              <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-gray-900 mb-2">
                {user?.is_admin ? "All Posts" : "All Posts"}
              </h1>
              {user?.is_admin && (
                <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-purple-100 text-purple-800 border border-purple-200">
                  <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M9.504 1.132a1 1 0 01.992 0l1.75 1a1 1 0 11-.992 1.736L10 3.152l-1.254.716a1 1 0 11-.992-1.736l1.75-1z" clipRule="evenodd" />
                  </svg>
                  Admin View
                </span>
              )}
            </div>
            {user && (
              <Link
                to="/posts/new"
                className="inline-flex items-center justify-center px-4 sm:px-6 py-3 border border-transparent text-sm sm:text-base font-medium rounded-lg text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-all duration-200 shadow-sm hover:shadow-md"
              >
                <svg className="w-4 h-4 sm:w-5 sm:h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                <span className="hidden sm:inline">Create New Post</span>
                <span className="sm:hidden">New Post</span>
              </Link>
            )}
          </div>
        </div>

        {/* Admin Notice */}
        {user?.is_admin && (
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-4 sm:p-6 mb-6 sm:mb-8">
            <div className="flex items-start space-x-3">
              <div className="flex-shrink-0">
                <svg className="w-5 h-5 sm:w-6 sm:h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
                </svg>
              </div>
              <div>
                <h3 className="font-semibold text-blue-900 text-sm sm:text-base mb-1">👨‍💼 Admin Controls</h3>
                <p className="text-blue-700 text-xs sm:text-sm">
                  You can see all posts including unapproved ones. Use the controls below each post to approve, flag, or manage content.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 sm:p-12 text-center">
            <div className="animate-spin rounded-full h-8 w-8 sm:h-12 sm:w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
            <p className="text-gray-500 text-sm sm:text-base">Loading posts...</p>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="bg-white rounded-xl shadow-sm border border-red-200 p-4 sm:p-6 mb-6">
            <div className="flex items-center space-x-3">
              <svg className="w-5 h-5 text-red-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-red-600 font-medium text-sm sm:text-base">{error}</p>
            </div>
          </div>
        )}

        {/* Empty State */}
        {!loading && posts.length === 0 && !error ? (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 sm:p-12 text-center">
            <div className="text-gray-400 text-4xl sm:text-6xl mb-4">📝</div>
            <h3 className="text-lg sm:text-xl font-semibold text-gray-900 mb-2">No posts available</h3>
            <p className="text-gray-500 text-sm sm:text-base mb-6">Be the first to share something with the community!</p>
            {user ? (
              <Link
                to="/posts/new"
                className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-lg text-white bg-indigo-600 hover:bg-indigo-700 transition-colors shadow-sm hover:shadow-md"
              >
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Create the first post!
              </Link>
            ) : (
              <p className="text-gray-600 text-sm sm:text-base">
                <Link to="/login" className="text-indigo-600 hover:text-indigo-700 font-medium">
                  Login
                </Link>{" "}
                to create posts
              </p>
            )}
          </div>
        ) : (
          /* Posts Grid */
          <div className="space-y-4 sm:space-y-6">
            {posts.map((post) => (
              <div
                key={post.id}
                className={`bg-white rounded-xl shadow-sm border transition-all duration-200 hover:shadow-md ${
                  !post.is_approved ? "border-orange-300 bg-gradient-to-r from-orange-50 to-yellow-50" : "border-gray-200"
                } ${post.is_flagged ? "border-red-300 bg-gradient-to-r from-red-50 to-pink-50" : ""}`}
              >
                <div className="p-4 sm:p-6">
                  <div className="flex space-x-3 sm:space-x-4">
                    {/* Vote Buttons - Always visible but responsive */}
                    <VoteButtons post={post} />
                    
                    {/* Post Content */}
                    <div className="flex-1 min-w-0">
                      <Link to={`/posts/${post.id}`} className="block group">
                        <div className="mb-3">
                          <h2 className="text-lg sm:text-xl lg:text-2xl font-semibold text-gray-900 group-hover:text-indigo-600 transition-colors duration-200 mb-2 break-words">
                            {post.title}
                          </h2>
                          
                          {/* Status Badges */}
                          <div className="flex flex-wrap gap-2 mb-3">
                            {!post.is_approved && (
                              <span className="inline-flex items-center px-2 py-1 text-xs font-semibold bg-orange-100 text-orange-800 rounded-full border border-orange-200">
                                <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
                                </svg>
                                Pending Approval
                              </span>
                            )}
                            {post.is_flagged && (
                              <span className="inline-flex items-center px-2 py-1 text-xs font-semibold bg-red-100 text-red-800 rounded-full border border-red-200">
                                <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                  <path fillRule="evenodd" d="M3 6a3 3 0 013-3h10a1 1 0 01.8 1.6L14.25 8l2.55 3.4A1 1 0 0116 13H6a1 1 0 00-1 1v3a1 1 0 11-2 0V6z" clipRule="evenodd" />
                                </svg>
                                Flagged
                              </span>
                            )}
                          </div>
                          
                          <p className="text-gray-600 text-sm sm:text-base leading-relaxed break-words">
                            {post.content?.length > 120
                              ? `${post.content.slice(0, 120)}...`
                              : post.content}
                          </p>
                        </div>
                      </Link>
                      
                      {/* Post Metadata */}
                      <div className="flex flex-col space-y-3 sm:flex-row sm:items-center sm:justify-between sm:space-y-0">
                        {/* Author and Date Info */}
                        <div className="flex flex-wrap items-center gap-2 sm:gap-4 text-xs sm:text-sm text-gray-500">
                          <div className="flex items-center space-x-1">
                            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                            </svg>
                            <span className="font-medium text-gray-700">
                              {post.author?.username || post.username || "Unknown"}
                            </span>
                          </div>
                          
                          <div className="flex items-center space-x-1">
                            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd" />
                            </svg>
                            <span>{new Date(post.created_at).toLocaleDateString()}</span>
                          </div>

                          {/* Stats */}
                          <div className="flex flex-wrap items-center gap-3">
                            {post.total_votes > 0 && (
                              <span className="flex items-center space-x-1 text-indigo-600 font-medium">
                                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                  <path fillRule="evenodd" d="M2 10a8 8 0 018-8v8h8a8 8 0 11-16 0z" clipRule="evenodd" />
                                </svg>
                                <span>{post.total_votes} vote{post.total_votes !== 1 ? "s" : ""}</span>
                              </span>
                            )}
                            {post.likes_count > 0 && (
                              <span className="flex items-center space-x-1 text-pink-600 font-medium">
                                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                  <path fillRule="evenodd" d="M3.172 5.172a4 4 0 015.656 0L10 6.343l1.172-1.171a4 4 0 115.656 5.656L10 17.657l-6.828-6.829a4 4 0 010-5.656z" clipRule="evenodd" />
                                </svg>
                                <span>{post.likes_count} like{post.likes_count !== 1 ? "s" : ""}</span>
                              </span>
                            )}
                            {post.comments_count > 0 && (
                              <span className="flex items-center space-x-1 text-blue-600 font-medium">
                                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                  <path fillRule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clipRule="evenodd" />
                                </svg>
                                <span>{post.comments_count} comment{post.comments_count !== 1 ? "s" : ""}</span>
                              </span>
                            )}
                          </div>
                        </div>
                        
                        {/* Action Buttons */}
                        <div className="flex flex-wrap items-center gap-2">
                          <LikeButton type="post" id={post.id} />
                          
                          {/* Author Controls */}
                          {user?.id === post.user_id && (
                            <div className="flex items-center space-x-2">
                              <Link
                                to={`/posts/${post.id}/edit`}
                                className="inline-flex items-center px-3 py-1.5 text-xs font-medium bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 transition-colors duration-200"
                              >
                                <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                </svg>
                                Edit
                              </Link>
                              <button
                                onClick={(e) => {
                                  e.preventDefault();
                                  handleDeletePost(post.id);
                                }}
                                className="inline-flex items-center px-3 py-1.5 text-xs font-medium bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors duration-200"
                              >
                                <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                                Delete
                              </button>
                            </div>
                          )}

                          {/* Admin Controls */}
                          {user?.is_admin && (
                            <div className="flex flex-wrap items-center gap-2">
                              {!post.is_approved && (
                                <>
                                  <button
                                    onClick={(e) => {
                                      e.preventDefault();
                                      e.stopPropagation();
                                      handleApprovePost(post.id, true);
                                    }}
                                    className="inline-flex items-center px-3 py-1.5 text-xs font-medium bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-colors duration-200"
                                  >
                                    <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                    </svg>
                                    Approve
                                  </button>
                                  <button
                                    onClick={(e) => {
                                      e.preventDefault();
                                      e.stopPropagation();
                                      handleApprovePost(post.id, false);
                                    }}
                                    className="inline-flex items-center px-3 py-1.5 text-xs font-medium bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors duration-200"
                                  >
                                    <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                    </svg>
                                    Reject
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
                                  className="inline-flex items-center px-3 py-1.5 text-xs font-medium bg-orange-100 text-orange-700 rounded-lg hover:bg-orange-200 transition-colors duration-200"
                                >
                                  <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728L5.636 5.636m12.728 12.728L18.364 5.636M5.636 18.364l12.728-12.728" />
                                  </svg>
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
                                className={`inline-flex items-center px-3 py-1.5 text-xs font-medium rounded-lg transition-colors duration-200 ${
                                  post.is_flagged
                                    ? "bg-yellow-100 text-yellow-700 hover:bg-yellow-200"
                                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                                }`}
                              >
                                <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                  <path fillRule="evenodd" d="M3 6a3 3 0 013-3h10a1 1 0 01.8 1.6L14.25 8l2.55 3.4A1 1 0 0116 13H6a1 1 0 00-1 1v3a1 1 0 11-2 0V6z" clipRule="evenodd" />
                                </svg>
                                {post.is_flagged ? "Unflag" : "Flag"}
                              </button>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Posts;