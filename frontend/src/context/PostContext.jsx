import { createContext, useContext, useState, useEffect } from "react";
import toast from "react-hot-toast";

const PostContext = createContext();

// Use the correct API URL to match your backend
const API_URL = import.meta.env.VITE_API_URL || "https://mindthread-1.onrender.com";

export const usePosts = () => {
  const context = useContext(PostContext);
  if (!context) {
    throw new Error("usePosts must be used within a PostProvider");
  }
  return context;
};

export const PostProvider = ({ children }) => {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchPosts = async () => {
    try {
      setLoading(true);
      setError(null);
      
      console.log("🔍 Fetching posts from:", `${API_URL}/api/posts`);
      
      const res = await fetch(`${API_URL}/api/posts`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
        },
        credentials: "include", // For proper CORS handling
      });

      console.log("📡 Posts response status:", res.status);

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: Failed to fetch posts`);
      }

      const contentType = res.headers.get("content-type") || "";
      if (!contentType.includes("application/json")) {
        const textResponse = await res.text();
        console.error("❌ Non-JSON response:", textResponse);
        throw new Error("API did not return valid JSON");
      }

      const data = await res.json();
      console.log("📦 Posts data received:", data.length, "posts");
      
      // Ensure data is an array
      if (!Array.isArray(data)) {
        console.error("❌ Posts data is not an array:", data);
        throw new Error("Invalid posts data format");
      }

      setPosts(data);
      setError(null);
    } catch (err) {
      console.error("💥 Fetch posts error:", err);
      setError(err.message);
      toast.error("Failed to load posts");
      setPosts([]); // Set empty array on error
    } finally {
      setLoading(false);
    }
  };

  const createPost = async (postData, token) => {
    try {
      console.log("🔍 Creating post:", postData);
      
      const res = await fetch(`${API_URL}/api/posts`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
          ...(token && { Authorization: `Bearer ${token}` }),
        },
        credentials: "include",
        body: JSON.stringify(postData),
      });

      console.log("📡 Create post response status:", res.status);

      const data = await res.json();
      console.log("📦 Create post response data:", data);

      if (res.ok) {
        toast.success("Post created successfully");
        await fetchPosts(); // Refresh posts list
        return { success: true, data };
      } else {
        toast.error(data.error || "Failed to create post");
        return { success: false, error: data.error };
      }
    } catch (error) {
      console.error("💥 Create post error:", error);
      toast.error("Network error while creating post");
      return { success: false, error: error.message };
    }
  };

  const updatePost = async (postId, postData, token) => {
    try {
      console.log("🔍 Updating post:", postId, postData);
      
      const res = await fetch(`${API_URL}/api/posts/${postId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
          ...(token && { Authorization: `Bearer ${token}` }),
        },
        credentials: "include",
        body: JSON.stringify(postData),
      });

      const data = await res.json();
      console.log("📦 Update post response:", data);

      if (res.ok) {
        toast.success("Post updated successfully");
        await fetchPosts(); // Refresh posts list
        return { success: true, data };
      } else {
        toast.error(data.error || "Failed to update post");
        return { success: false, error: data.error };
      }
    } catch (error) {
      console.error("💥 Update post error:", error);
      toast.error("Network error while updating post");
      return { success: false, error: error.message };
    }
  };

  const deletePost = async (postId, token) => {
    try {
      console.log("🔍 Deleting post:", postId);
      
      const res = await fetch(`${API_URL}/api/posts/${postId}`, {
        method: "DELETE",
        headers: {
          "Accept": "application/json",
          ...(token && { Authorization: `Bearer ${token}` }),
        },
        credentials: "include",
      });

      const data = await res.json();
      console.log("📦 Delete post response:", data);

      if (res.ok) {
        toast.success("Post deleted successfully");
        // Remove post from local state instead of refetching all posts
        setPosts(prevPosts => prevPosts.filter(post => post.id !== postId));
        return { success: true, data };
      } else {
        toast.error(data.error || "Failed to delete post");
        return { success: false, error: data.error };
      }
    } catch (error) {
      console.error("💥 Delete post error:", error);
      toast.error("Network error while deleting post");
      return { success: false, error: error.message };
    }
  };

  const getPost = async (postId, token = null) => {
    try {
      console.log("🔍 Fetching single post:", postId);
      
      const headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
      };
      
      if (token) {
        headers.Authorization = `Bearer ${token}`;
      }

      const res = await fetch(`${API_URL}/api/posts/${postId}`, {
        method: "GET",
        headers,
        credentials: "include",
      });

      const data = await res.json();
      console.log("📦 Single post response:", data);

      if (res.ok) {
        return { success: true, data };
      } else {
        console.error("❌ Failed to fetch post:", data);
        return { success: false, error: data.error };
      }
    } catch (error) {
      console.error("💥 Get post error:", error);
      return { success: false, error: error.message };
    }
  };

  const likePost = async (postId, token) => {
    try {
      console.log("🔍 Toggling like for post:", postId);
      
      const res = await fetch(`${API_URL}/api/posts/${postId}/like`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
          Authorization: `Bearer ${token}`,
        },
        credentials: "include",
      });

      const data = await res.json();
      console.log("📦 Like post response:", data);

      if (res.ok) {
        toast.success(data.message || "Like toggled");
        // Update the post in local state
        setPosts(prevPosts =>
          prevPosts.map(post =>
            post.id === postId
              ? {
                  ...post,
                  likes: data.likes || 0,
                  liked_by: data.liked_by || []
                }
              : post
          )
        );
        return { success: true, data };
      } else {
        toast.error(data.error || "Failed to toggle like");
        return { success: false, error: data.error };
      }
    } catch (error) {
      console.error("💥 Like post error:", error);
      toast.error("Network error while toggling like");
      return { success: false, error: error.message };
    }
  };

  // Health check function for debugging
  const testPostsAPI = async () => {
    try {
      console.log("🧪 Testing posts API...");
      const response = await fetch(`${API_URL}/api/posts`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
        },
        credentials: "include",
      });
      
      console.log("Posts API test status:", response.status);
      console.log("Posts API test headers:", Object.fromEntries(response.headers.entries()));
      
      if (response.ok) {
        const data = await response.json();
        console.log("Posts API test data:", data);
        return true;
      } else {
        const errorText = await response.text();
        console.error("Posts API test failed:", errorText);
        return false;
      }
    } catch (error) {
      console.error("Posts API test error:", error);
      return false;
    }
  };

  // Load posts on component mount
  useEffect(() => {
    fetchPosts();
  }, []);

  const value = {
    // State
    posts,
    loading,
    error,
    
    // Actions
    fetchPosts,
    setPosts,
    createPost,
    updatePost,
    deletePost,
    getPost,
    likePost,
    
    // Debug
    testPostsAPI,
    
    // Helpers
    postsCount: posts.length,
    isEmpty: posts.length === 0 && !loading,
  };

  return (
    <PostContext.Provider value={value}>
      {children}
    </PostContext.Provider>
  );
};