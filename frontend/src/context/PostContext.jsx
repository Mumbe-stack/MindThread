import { createContext, useContext, useState, useEffect } from "react";
import toast from "react-hot-toast";

const PostContext = createContext();


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
      
      
      const res = await fetch(`${API_URL}/api/posts`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
        },
        credentials: "include", 
      });

    

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: Failed to fetch posts`);
      }

      const contentType = res.headers.get("content-type") || "";
      if (!contentType.includes("application/json")) {
        const textResponse = await res.text();
        
        throw new Error("API did not return valid JSON");
      }

      const data = await res.json();
     
      
      
      if (!Array.isArray(data)) {
        
        throw new Error("Invalid posts data format");
      }

      setPosts(data);
      setError(null);
    } catch (err) {
    
      setError(err.message);
      toast.error("Failed to load posts");
      setPosts([]); 
    } finally {
      setLoading(false);
    }
  };

  const createPost = async (postData, token) => {
    try {
     
      
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

     
      const data = await res.json();
     

      if (res.ok) {
        toast.success("Post created successfully");
        await fetchPosts(); 
        return { success: true, data };
      } else {
        toast.error(data.error || "Failed to create post");
        return { success: false, error: data.error };
      }
    } catch (error) {
     
      toast.error("Network error while creating post");
      return { success: false, error: error.message };
    }
  };

  const updatePost = async (postId, postData, token) => {
    try {
      
      
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
     

      if (res.ok) {
        toast.success("Post updated successfully");
        await fetchPosts(); 
        return { success: true, data };
      } else {
        toast.error(data.error || "Failed to update post");
        return { success: false, error: data.error };
      }
    } catch (error) {
     
      toast.error("Network error while updating post");
      return { success: false, error: error.message };
    }
  };

  const deletePost = async (postId, token) => {
    try {
      
      const res = await fetch(`${API_URL}/api/posts/${postId}`, {
        method: "DELETE",
        headers: {
          "Accept": "application/json",
          ...(token && { Authorization: `Bearer ${token}` }),
        },
        credentials: "include",
      });

      const data = await res.json();
      

      if (res.ok) {
        toast.success("Post deleted successfully");
        
        setPosts(prevPosts => prevPosts.filter(post => post.id !== postId));
        return { success: true, data };
      } else {
        toast.error(data.error || "Failed to delete post");
        return { success: false, error: data.error };
      }
    } catch (error) {
      
      toast.error("Network error while deleting post");
      return { success: false, error: error.message };
    }
  };

  const getPost = async (postId, token = null) => {
    try {
     
      
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
      

      if (res.ok) {
        return { success: true, data };
      } else {
       
        return { success: false, error: data.error };
      }
    } catch (error) {
      
      return { success: false, error: error.message };
    }
  };

  const likePost = async (postId, token) => {
    try {
     
      
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
     

      if (res.ok) {
        toast.success(data.message || "Like toggled");
        
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
     
      toast.error("Network error while toggling like");
      return { success: false, error: error.message };
    }
  };

  
  const testPostsAPI = async () => {
    try {
      
      const response = await fetch(`${API_URL}/api/posts`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
        },
        credentials: "include",
      });
      
  
      
      if (response.ok) {
        const data = await response.json();
        
        return true;
      } else {
        const errorText = await response.text();
        
        return false;
      }
    } catch (error) {
      
      return false;
    }
  };

  
  useEffect(() => {
    fetchPosts();
  }, []);

  const value = {
    
    posts,
    loading,
    error,
    
    
    fetchPosts,
    setPosts,
    createPost,
    updatePost,
    deletePost,
    getPost,
    likePost,
    
    
    testPostsAPI,
    
   
    postsCount: posts.length,
    isEmpty: posts.length === 0 && !loading,
  };

  return (
    <PostContext.Provider value={value}>
      {children}
    </PostContext.Provider>
  );
};