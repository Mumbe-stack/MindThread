import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import toast from "react-hot-toast";


const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";

const Home = () => {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { user } = useAuth();

  useEffect(() => {
    fetchPosts();
  }, []);

  const fetchPosts = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch(`${API_BASE_URL}/api/posts`);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch posts: ${response.status}`);
      }
      
      const contentType = response.headers.get("content-type");
      if (!contentType || !contentType.includes("application/json")) {
        throw new Error("Server did not return valid JSON");
      }
      
      const data = await response.json();
      setPosts(Array.isArray(data) ? data : []);
      
    } catch (err) {
      console.error("Failed to load posts:", err);
      setError(err.message);
      toast.error("Failed to load posts");
      setPosts([]);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    } catch {
      return 'Unknown date';
    }
  };

  const truncateContent = (content, maxLength = 150) => {
    if (!content) return '';
    if (content.length <= maxLength) return content;
    return content.substring(0, maxLength).trim() + '...';
  };

  const renderTagList = (tags) => {
    if (!tags) return null;
    
    const tagArray = tags.split(',').map(tag => tag.trim()).filter(Boolean);
    if (tagArray.length === 0) return null;
    
    return (
      <div className="flex flex-wrap gap-1 mt-2">
        {tagArray.slice(0, 3).map((tag, index) => (
          <span
            key={index}
            className="px-2 py-1 bg-blue-100 text-blue-600 text-xs rounded-full"
          >
            #{tag}
          </span>
        ))}
        {tagArray.length > 3 && (
          <span className="px-2 py-1 bg-gray-100 text-gray-500 text-xs rounded-full">
            +{tagArray.length - 3} more
          </span>
        )}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto p-6">
        <h1 className="text-3xl font-bold mb-6 text-center text-indigo-800">
          MindThread Blogging App
        </h1>
        <div className="grid gap-4">
          {[...Array(3)].map((_, index) => (
            <div key={index} className="border p-4 rounded shadow animate-pulse">
              <div className="h-6 bg-gray-200 rounded mb-2"></div>
              <div className="h-4 bg-gray-200 rounded mb-2"></div>
              <div className="h-4 bg-gray-200 rounded w-3/4"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-5xl mx-auto p-6">
        <h1 className="text-3xl font-bold mb-6 text-center text-indigo-800">
          MindThread Blogging App
        </h1>
        <div className="text-center py-12">
          <div className="text-red-600 mb-4">
            <svg className="mx-auto h-12 w-12 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">Failed to Load Posts</h3>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={fetchPosts}
            className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto p-6">
      {/* Header */}
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold text-indigo-800 mb-2">
          MindThread
        </h1>
        <p className="text-gray-600 mb-6">
          Share your thoughts, connect with others! 
        </p>
        
        {user && (
          <Link
            to="/posts/new"
            className="inline-flex items-center bg-indigo-600 text-white px-6 py-2 rounded-lg hover:bg-indigo-700 transition-colors"
          >
            <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Create New Post
          </Link>
        )}
      </div>

      {/* Stats Bar */}
      {posts.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-8">
          <div className="flex items-center justify-center space-x-8 text-sm text-gray-600">
            <div className="text-center">
              <div className="text-2xl font-bold text-indigo-600">{posts.length}</div>
              <div>Posts</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {posts.reduce((total, post) => total + (post.tags ? post.tags.split(',').length : 0), 0)}
              </div>
              <div>Tags</div>
            </div>
          </div>
        </div>
      )}

      {/* Posts Grid */}
      {posts.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-gray-400 mb-4">
            <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No Posts Yet</h3>
          <p className="text-gray-600 mb-4">
            Be the first to share something interesting!
          </p>
          {user ? (
            <Link
              to="/posts/new"
              className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700"
            >
              Write the First Post
            </Link>
          ) : (
            <div className="space-x-4">
              <Link
                to="/login"
                className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700"
              >
                Sign In to Post
              </Link>
              <Link
                to="/register"
                className="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700"
              >
                Create Account
              </Link>
            </div>
          )}
        </div>
      ) : (
        <div className="grid gap-6">
          {posts.map((post) => (
            <article
              key={post.id}
              className="border border-gray-200 p-6 rounded-lg shadow-sm hover:shadow-md transition-shadow bg-white"
            >
              <Link to={`/posts/${post.id}`} className="block">
                <h2 className="text-xl font-semibold text-indigo-700 hover:text-indigo-800 hover:underline mb-3">
                  {post.title}
                </h2>
              </Link>
              
              <p className="text-gray-700 mb-4 leading-relaxed">
                {truncateContent(post.content)}
              </p>
              
              {renderTagList(post.tags)}
              
              <div className="flex items-center justify-between text-sm text-gray-500 mt-4 pt-4 border-t border-gray-100">
                <span className="flex items-center">
                  <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                  User #{post.user_id}
                </span>
                <time dateTime={post.created_at} className="flex items-center">
                  <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  {formatDate(post.created_at)}
                </time>
              </div>
              
              <Link
                to={`/posts/${post.id}`}
                className="inline-flex items-center text-indigo-600 hover:text-indigo-800 text-sm font-medium mt-3"
              >
                Read more
                <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </Link>
            </article>
          ))}
        </div>
      )}

      {/* Load More / Refresh Section */}
      <div className="text-center mt-8">
        <button
          onClick={fetchPosts}
          disabled={loading}
          className="text-gray-600 hover:text-gray-800 text-sm font-medium disabled:opacity-50 flex items-center mx-auto"
        >
          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          {loading ? "Loading..." : "Refresh Posts"}
        </button>
      </div>

      {/* Footer Message */}
      {posts.length > 0 && (
        <div className="text-center mt-12 pb-8">
          <p className="text-gray-500 text-sm">
            {posts.length === 1 ? "1 post" : `${posts.length} posts`} • 
            Welcome to MindThread community! 🎉
          </p>
          {!user && (
            <p className="text-gray-500 text-sm mt-2">
              <Link to="/register" className="text-indigo-600 hover:underline">
                Join us
              </Link> to start sharing your thoughts
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export default Home;