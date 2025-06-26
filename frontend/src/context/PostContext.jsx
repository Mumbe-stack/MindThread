import { createContext, useContext, useState, useEffect } from "react";
import toast from "react-hot-toast";

const PostContext = createContext();
const VITE_API_URL = import.meta.env.VITE_API_URL || 'https://mindthread.onrender.com';
console.log('🔍 PostContext API_URL:', VITE_API_URL);

export const usePosts = () => useContext(PostContext);

export const PostProvider = ({ children }) => {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchPosts = async () => {
    try {
      setLoading(true);
      setError(null);
      const url = `${VITE_API_URL}/api/posts`;
      console.log('📡 Fetching posts from:', url);

      const token = localStorage.getItem('token');
      const headers = { "Content-Type": "application/json" };
      if (token) headers.Authorization = `Bearer ${token}`;

      const res = await fetch(url, {
        method: "GET",
        credentials: "include",
        headers,
      });

      const contentType = res.headers.get("content-type") || "";

      if (!res.ok) {
        const text = await res.text();
        console.error('❌ Error response:', text.slice(0, 100));
        throw new Error(`Error ${res.status}: ${text}`);
      }

      if (!contentType.includes("application/json")) {
        const text = await res.text();
        console.error('❌ Unexpected HTML response:', text.slice(0, 100));
        throw new Error("Expected JSON but received HTML or invalid response.");
      }

      const data = await res.json();
      console.log('✅ Posts received:', data.length);
      setPosts(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message);
      toast.error(err.message || "Failed to fetch posts");
      console.error("Fetch error:", err);
    } finally {
      setLoading(false);
    }
  };

  const createPost = async (postData) => {
    try {
      const token = localStorage.getItem('token');
      if (!token) throw new Error("Authentication required");

      const res = await fetch(`${VITE_API_URL}/api/posts`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(postData),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || "Failed to create post");
      }

      const newPost = await res.json();
      await fetchPosts();
      toast.success("Post created successfully!");
      return newPost;
    } catch (err) {
      toast.error(err.message || "Failed to create post");
      throw err;
    }
  };

  const updatePost = async (postId, updates) => {
    try {
      const token = localStorage.getItem('token');
      if (!token) throw new Error("Authentication required");

      const res = await fetch(`${VITE_API_URL}/api/posts/${postId}`, {
        method: "PATCH",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(updates),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || "Failed to update post");
      }

      await fetchPosts();
      toast.success("Post updated successfully!");
    } catch (err) {
      toast.error(err.message || "Failed to update post");
      throw err;
    }
  };

  const deletePost = async (postId) => {
    try {
      const token = localStorage.getItem('token');
      if (!token) throw new Error("Authentication required");

      const res = await fetch(`${VITE_API_URL}/api/posts/${postId}`, {
        method: "DELETE",
        credentials: "include",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || "Failed to delete post");
      }

      setPosts(posts.filter(post => post.id !== postId));
      toast.success("Post deleted successfully!");
    } catch (err) {
      toast.error(err.message || "Failed to delete post");
      throw err;
    }
  };

  const getPost = async (postId) => {
    try {
      const token = localStorage.getItem('token');
      const headers = { "Content-Type": "application/json" };
      if (token) headers.Authorization = `Bearer ${token}`;

      const res = await fetch(`${VITE_API_URL}/api/posts/${postId}`, {
        method: "GET",
        credentials: "include",
        headers,
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || "Failed to fetch post");
      }

      return await res.json();
    } catch (err) {
      toast.error(err.message || "Failed to fetch post");
      throw err;
    }
  };

  const toggleLikePost = async (postId) => {
    try {
      const token = localStorage.getItem('token');
      if (!token) throw new Error("Authentication required");

      const res = await fetch(`${VITE_API_URL}/api/posts/${postId}/like`, {
        method: "POST",
        credentials: "include",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || "Failed to toggle like");
      }

      const data = await res.json();
      await fetchPosts();
      toast.success(data.message);
    } catch (err) {
      toast.error(err.message || "Failed to toggle like");
      throw err;
    }
  };

  const toggleApprovePost = async (postId) => {
    try {
      const token = localStorage.getItem('token');
      if (!token) throw new Error("Authentication required");

      const res = await fetch(`${VITE_API_URL}/api/posts/${postId}/approve`, {
        method: "PATCH",
        credentials: "include",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || "Failed to toggle approval");
      }

      const data = await res.json();
      await fetchPosts();
      toast.success(data.message);
    } catch (err) {
      toast.error(err.message || "Failed to toggle approval");
      throw err;
    }
  };

  const toggleFlagPost = async (postId) => {
    try {
      const token = localStorage.getItem('token');
      if (!token) throw new Error("Authentication required");

      const res = await fetch(`${VITE_API_URL}/api/posts/${postId}/flag`, {
        method: "PATCH",
        credentials: "include",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || "Failed to toggle flag");
      }

      const data = await res.json();
      await fetchPosts();
      toast.success(data.message);
    } catch (err) {
      toast.error(err.message || "Failed to toggle flag");
      throw err;
    }
  };

  useEffect(() => {
    fetchPosts(); // Initial fetch
  }, []);

  return (
    <PostContext.Provider
      value={{
        posts,
        loading,
        error,
        fetchPosts,
        createPost,
        updatePost,
        deletePost,
        getPost,
        toggleLikePost,
        toggleApprovePost,
        toggleFlagPost,
        setPosts,
      }}
    >
      {children}
    </PostContext.Provider>
  );
};
