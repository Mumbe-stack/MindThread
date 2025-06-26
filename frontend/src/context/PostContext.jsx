import { createContext, useContext, useState, useEffect, useRef } from "react";
import toast from "react-hot-toast";

const PostContext = createContext();
const VITE_API_URL = import.meta.env.VITE_API_URL || 'https://mindthread.onrender.com';

export const usePosts = () => useContext(PostContext);

export const PostProvider = ({ children }) => {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const isMounted = useRef(true);

  const getAuthHeaders = () => {
    const token = localStorage.getItem('token');
    return {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
  };

  const fetchPosts = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${VITE_API_URL}/api/posts`, {
        method: "GET",
        credentials: "include",
        headers: getAuthHeaders(),
      });

      const contentType = res.headers.get("content-type") || "";

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Error ${res.status}: ${text}`);
      }

      if (!contentType.includes("application/json")) {
        const text = await res.text();
        throw new Error("Expected JSON but received invalid response.");
      }

      const data = await res.json();
      if (isMounted.current) {
        setPosts(Array.isArray(data) ? data : []);
      }
    } catch (err) {
      if (isMounted.current) {
        setError(err.message);
        toast.error(err.message);
      }
    } finally {
      if (isMounted.current) setLoading(false);
    }
  };

  const createPost = async (postData) => {
    try {
      const res = await fetch(`${VITE_API_URL}/api/posts`, {
        method: "POST",
        credentials: "include",
        headers: getAuthHeaders(),
        body: JSON.stringify(postData),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to create post");

      await fetchPosts();
      toast.success("Post created successfully!");
      return data;
    } catch (err) {
      toast.error(err.message);
      throw err;
    }
  };

  const updatePost = async (postId, updates) => {
    try {
      const res = await fetch(`${VITE_API_URL}/api/posts/${postId}`, {
        method: "PATCH",
        credentials: "include",
        headers: getAuthHeaders(),
        body: JSON.stringify(updates),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to update post");

      await fetchPosts();
      toast.success("Post updated");
    } catch (err) {
      toast.error(err.message);
      throw err;
    }
  };

  const deletePost = async (postId) => {
    try {
      const res = await fetch(`${VITE_API_URL}/api/posts/${postId}`, {
        method: "DELETE",
        credentials: "include",
        headers: getAuthHeaders(),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to delete post");

      setPosts((prev) => prev.filter((p) => p.id !== postId));
      toast.success("Post deleted");
    } catch (err) {
      toast.error(err.message);
      throw err;
    }
  };

  const getPost = async (postId) => {
    try {
      const res = await fetch(`${VITE_API_URL}/api/posts/${postId}`, {
        method: "GET",
        credentials: "include",
        headers: getAuthHeaders(),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to fetch post");

      return data;
    } catch (err) {
      toast.error(err.message);
      throw err;
    }
  };

  const toggleLikePost = async (postId) => {
    try {
      const res = await fetch(`${VITE_API_URL}/api/posts/${postId}/like`, {
        method: "POST",
        credentials: "include",
        headers: getAuthHeaders(),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to toggle like");

      await fetchPosts();
      toast.success(data.message);
    } catch (err) {
      toast.error(err.message);
      throw err;
    }
  };

  const toggleApprovePost = async (postId) => {
    try {
      const res = await fetch(`${VITE_API_URL}/api/posts/${postId}/approve`, {
        method: "PATCH",
        credentials: "include",
        headers: getAuthHeaders(),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to toggle approval");

      await fetchPosts();
      toast.success(data.message);
    } catch (err) {
      toast.error(err.message);
      throw err;
    }
  };

  const toggleFlagPost = async (postId) => {
    try {
      const res = await fetch(`${VITE_API_URL}/api/posts/${postId}/flag`, {
        method: "PATCH",
        credentials: "include",
        headers: getAuthHeaders(),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to toggle flag");

      await fetchPosts();
      toast.success(data.message);
    } catch (err) {
      toast.error(err.message);
      throw err;
    }
  };

  useEffect(() => {
    isMounted.current = true;
    fetchPosts();
    return () => {
      isMounted.current = false;
    };
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
export default PostProvider;