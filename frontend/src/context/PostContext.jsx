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
  const [comments, setComments] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Enhanced API request helper
  const makeApiRequest = async (url, options = {}) => {
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
          ...options.headers,
        },
        credentials: "include",
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
      }

      const contentType = response.headers.get("content-type") || "";
      if (!contentType.includes("application/json")) {
        throw new Error("Server returned non-JSON response");
      }

      return await response.json();
    } catch (error) {
      throw error;
    }
  };

  // Posts API
  const fetchPosts = async (filters = {}) => {
    try {
      setLoading(true);
      setError(null);
      
      const queryParams = new URLSearchParams();
      if (filters.search) queryParams.append('search', filters.search);
      if (filters.sort) queryParams.append('sort', filters.sort);
      if (filters.order) queryParams.append('order', filters.order);
      if (filters.page) queryParams.append('page', filters.page);
      if (filters.per_page) queryParams.append('per_page', filters.per_page);

      const url = `${API_URL}/api/posts${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
      const data = await makeApiRequest(url);
      
      if (!Array.isArray(data)) {
        throw new Error("Invalid posts data format");
      }

      setPosts(data);
      setError(null);
      return { success: true, data };
    } catch (err) {
      setError(err.message);
      toast.error(`Failed to load posts: ${err.message}`);
      setPosts([]);
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  };

  const createPost = async (postData, token) => {
    try {
      const data = await makeApiRequest(`${API_URL}/api/posts`, {
        method: "POST",
        headers: {
          ...(token && { Authorization: `Bearer ${token}` }),
        },
        body: JSON.stringify(postData),
      });

      toast.success("Post created successfully");
      await fetchPosts();
      return { success: true, data };
    } catch (error) {
      toast.error(`Failed to create post: ${error.message}`);
      return { success: false, error: error.message };
    }
  };

  const updatePost = async (postId, postData, token) => {
    try {
      const data = await makeApiRequest(`${API_URL}/api/posts/${postId}`, {
        method: "PATCH",
        headers: {
          ...(token && { Authorization: `Bearer ${token}` }),
        },
        body: JSON.stringify(postData),
      });

      toast.success("Post updated successfully");
      await fetchPosts();
      return { success: true, data };
    } catch (error) {
      toast.error(`Failed to update post: ${error.message}`);
      return { success: false, error: error.message };
    }
  };

  const deletePost = async (postId, token) => {
    try {
      await makeApiRequest(`${API_URL}/api/posts/${postId}`, {
        method: "DELETE",
        headers: {
          ...(token && { Authorization: `Bearer ${token}` }),
        },
      });

      toast.success("Post deleted successfully");
      setPosts(prevPosts => prevPosts.filter(post => post.id !== postId));
      return { success: true };
    } catch (error) {
      toast.error(`Failed to delete post: ${error.message}`);
      return { success: false, error: error.message };
    }
  };

  const getPost = async (postId, token = null) => {
    try {
      const headers = {};
      if (token) headers.Authorization = `Bearer ${token}`;

      const data = await makeApiRequest(`${API_URL}/api/posts/${postId}`, {
        headers,
      });

      return { success: true, data };
    } catch (error) {
      return { success: false, error: error.message };
    }
  };

  const likePost = async (postId, token) => {
    try {
      const data = await makeApiRequest(`${API_URL}/api/posts/${postId}/like`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      toast.success(data.message || "Like toggled");
      
      // FIXED: Update posts state with consistent field names for both list and detail views
      setPosts(prevPosts =>
        prevPosts.map(post =>
          post.id === postId
            ? {
                ...post,
                likes_count: data.likes_count || 0,
                likes: data.likes_count || 0, // Ensure both field names are updated
                liked_by_user: data.liked_by_user || false
              }
            : post
        )
      );
      
      return { success: true, data };
    } catch (error) {
      toast.error(`Failed to toggle like: ${error.message}`);
      return { success: false, error: error.message };
    }
  };

  // Voting API
  const votePost = async (postId, value, token) => {
    try {
      const data = await makeApiRequest(`${API_URL}/api/votes/post/${postId}`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ value }), // 1 for upvote, -1 for downvote, 0 to remove vote
      });

      toast.success(data.message || "Vote recorded");
      
      // Update posts state with new vote counts
      setPosts(prevPosts =>
        prevPosts.map(post =>
          post.id === postId
            ? {
                ...post,
                upvotes: data.upvotes || post.upvotes,
                downvotes: data.downvotes || post.downvotes,
                vote_score: data.vote_score || post.vote_score,
                user_vote: data.user_vote
              }
            : post
        )
      );
      
      return { success: true, data };
    } catch (error) {
      toast.error(`Failed to vote: ${error.message}`);
      return { success: false, error: error.message };
    }
  };

  const voteComment = async (commentId, value, token) => {
    try {
      const data = await makeApiRequest(`${API_URL}/api/votes/comment/${commentId}`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ value }),
      });

      toast.success(data.message || "Vote recorded");
      
      // Update comments state
      setComments(prevComments => {
        const updatedComments = { ...prevComments };
        Object.keys(updatedComments).forEach(postId => {
          updatedComments[postId] = updatedComments[postId].map(comment =>
            comment.id === commentId
              ? {
                  ...comment,
                  upvotes: data.upvotes || comment.upvotes,
                  downvotes: data.downvotes || comment.downvotes,
                  vote_score: data.vote_score || comment.vote_score,
                  user_vote: data.user_vote
                }
              : comment
          );
        });
        return updatedComments;
      });
      
      return { success: true, data };
    } catch (error) {
      toast.error(`Failed to vote on comment: ${error.message}`);
      return { success: false, error: error.message };
    }
  };

  // Comments API
  const fetchComments = async (postId, options = {}) => {
    try {
      const queryParams = new URLSearchParams();
      queryParams.append('post_id', postId);
      if (options.parent_id !== undefined) queryParams.append('parent_id', options.parent_id);
      if (options.sort) queryParams.append('sort', options.sort);
      if (options.order) queryParams.append('order', options.order);

      const data = await makeApiRequest(`${API_URL}/api/comments?${queryParams.toString()}`);
      
      if (data.comments) {
        setComments(prev => ({
          ...prev,
          [postId]: data.comments
        }));
        return { success: true, data: data.comments };
      }
      
      return { success: true, data: [] };
    } catch (error) {
      toast.error(`Failed to load comments: ${error.message}`);
      return { success: false, error: error.message };
    }
  };

  const createComment = async (commentData, token) => {
    try {
      const data = await makeApiRequest(`${API_URL}/api/comments`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(commentData),
      });

      toast.success(data.message || "Comment created successfully");
      
      // Refresh comments for this post
      if (commentData.post_id) {
        await fetchComments(commentData.post_id);
      }
      
      return { success: true, data };
    } catch (error) {
      toast.error(`Failed to create comment: ${error.message}`);
      return { success: false, error: error.message };
    }
  };

  const updateComment = async (commentId, commentData, token) => {
    try {
      const data = await makeApiRequest(`${API_URL}/api/comments/${commentId}`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(commentData),
      });

      toast.success("Comment updated successfully");
      
      // Update local comments state
      setComments(prevComments => {
        const updatedComments = { ...prevComments };
        Object.keys(updatedComments).forEach(postId => {
          updatedComments[postId] = updatedComments[postId].map(comment =>
            comment.id === commentId ? { ...comment, ...data } : comment
          );
        });
        return updatedComments;
      });
      
      return { success: true, data };
    } catch (error) {
      toast.error(`Failed to update comment: ${error.message}`);
      return { success: false, error: error.message };
    }
  };

  const deleteComment = async (commentId, token) => {
    try {
      await makeApiRequest(`${API_URL}/api/comments/${commentId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      toast.success("Comment deleted successfully");
      
      // Remove comment from local state
      setComments(prevComments => {
        const updatedComments = { ...prevComments };
        Object.keys(updatedComments).forEach(postId => {
          updatedComments[postId] = updatedComments[postId].filter(comment => comment.id !== commentId);
        });
        return updatedComments;
      });
      
      return { success: true };
    } catch (error) {
      toast.error(`Failed to delete comment: ${error.message}`);
      return { success: false, error: error.message };
    }
  };

  const likeComment = async (commentId, token) => {
    try {
      const data = await makeApiRequest(`${API_URL}/api/comments/${commentId}/like`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      toast.success(data.message || "Like toggled");
      
      // Update comments state
      setComments(prevComments => {
        const updatedComments = { ...prevComments };
        Object.keys(updatedComments).forEach(postId => {
          updatedComments[postId] = updatedComments[postId].map(comment =>
            comment.id === commentId
              ? {
                  ...comment,
                  likes_count: data.likes_count || 0,
                  liked_by_user: data.liked_by_user || false
                }
              : comment
          );
        });
        return updatedComments;
      });
      
      return { success: true, data };
    } catch (error) {
      toast.error(`Failed to toggle comment like: ${error.message}`);
      return { success: false, error: error.message };
    }
  };

  // Flag content
  const flagPost = async (postId, token, reason = "") => {
    try {
      const data = await makeApiRequest(`${API_URL}/api/posts/${postId}/flag`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ is_flagged: true, reason }),
      });

      toast.success("Post flagged successfully");
      return { success: true, data };
    } catch (error) {
      toast.error(`Failed to flag post: ${error.message}`);
      return { success: false, error: error.message };
    }
  };

  const flagComment = async (commentId, token, reason = "") => {
    try {
      const data = await makeApiRequest(`${API_URL}/api/comments/${commentId}/flag`, {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ is_flagged: true, reason }),
      });

      toast.success("Comment flagged successfully");
      return { success: true, data };
    } catch (error) {
      toast.error(`Failed to flag comment: ${error.message}`);
      return { success: false, error: error.message };
    }
  };

  // Refresh posts after any change to ensure consistency
  const refreshPost = async (postId, token = null) => {
    try {
      const result = await getPost(postId, token);
      if (result.success) {
        setPosts(prevPosts =>
          prevPosts.map(post =>
            post.id === postId ? result.data : post
          )
        );
      }
      return result;
    } catch (error) {
      return { success: false, error: error.message };
    }
  };

  const getPostById = (postId) => {
    return posts.find(post => post.id === parseInt(postId));
  };

  const searchPosts = async (searchTerm, filters = {}) => {
    return await fetchPosts({
      search: searchTerm,
      ...filters
    });
  };

  // Auto-fetch posts on mount
  useEffect(() => {
    fetchPosts();
  }, []);

  const value = {
    // State
    posts,
    comments,
    loading,
    error,
    
    // Post operations
    fetchPosts,
    createPost,
    updatePost,
    deletePost,
    getPost,
    likePost,
    searchPosts,
    
    // Voting operations
    votePost,
    voteComment,
    
    // Comment operations
    fetchComments,
    createComment,
    updateComment,
    deleteComment,
    likeComment,
    getPostComments,
    
    // Flagging operations
    flagPost,
    flagComment,
    
    // Utility functions
    getPostComments,
    getPostById,
    searchPosts,
    setPosts,
    setComments,
    
    // FIXED: Add refresh function to sync data between views
    refreshPostData: async (postId, token = null) => {
      try {
        const result = await getPost(postId, token);
        if (result.success) {
          setPosts(prevPosts =>
            prevPosts.map(post =>
              post.id === postId ? result.data : post
            )
          );
        }
        return result;
      } catch (error) {
        return { success: false, error: error.message };
      }
    },
    
    // Computed properties
    postsCount: posts.length,
    isEmpty: posts.length === 0 && !loading,
    hasError: !!error,
  };

  return (
    <PostContext.Provider value={value}>
      {children}
    </PostContext.Provider>
  );
};