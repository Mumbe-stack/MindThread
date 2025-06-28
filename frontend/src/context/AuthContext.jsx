// frontend/src/context/AuthContext.jsx
// Add this function to your EXISTING AuthContext.jsx file

import { createContext, useContext, useState, useEffect } from "react";
import toast from "react-hot-toast";

const AuthContext = createContext();

const API_URL = import.meta.env.VITE_API_URL || "https://mindthread-1.onrender.com";

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Initialize auth state from localStorage
  useEffect(() => {
    const initializeAuth = () => {
      try {
        const storedToken = localStorage.getItem("token");
        const storedUser = localStorage.getItem("user");

        if (storedToken && storedUser) {
          setToken(storedToken);
          setUser(JSON.parse(storedUser));
          
          // Verify token is still valid
          verifyToken(storedToken);
        }
      } catch (error) {
        console.error("Error initializing auth:", error);
        localStorage.removeItem("token");
        localStorage.removeItem("user");
      } finally {
        setLoading(false);
      }
    };

    initializeAuth();
  }, []);

  // Verify token validity
  const verifyToken = async (tokenToVerify = token) => {
    if (!tokenToVerify) return false;

    try {
      const response = await fetch(`${API_URL}/api/auth/verify-token`, {
        method: "GET",
        headers: {
          "Authorization": `Bearer ${tokenToVerify}`,
          "Content-Type": "application/json",
        },
        credentials: "include",
      });

      if (response.ok) {
        const data = await response.json();
        if (data.user) {
          setUser(data.user);
          localStorage.setItem("user", JSON.stringify(data.user));
        }
        return true;
      } else {
        logout();
        return false;
      }
    } catch (error) {
      console.error("Token verification failed:", error);
      logout();
      return false;
    }
  };

  // Enhanced authenticated request function
  const authenticatedRequest = async (url, options = {}) => {
    if (!token) {
      throw new Error("No authentication token available");
    }

    const defaultOptions = {
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`,
        ...options.headers,
      },
      credentials: "include",
    };

    const finalOptions = { ...defaultOptions, ...options };

    try {
      const response = await fetch(url, finalOptions);

      if (response.status === 401) {
        logout();
        toast.error("Session expired. Please log in again.");
        throw new Error("Authentication expired");
      }

      return response;
    } catch (error) {
      console.error("Authenticated request failed:", error);
      throw error;
    }
  };

  // ADD THIS FUNCTION - This is what's missing and causing your error
  const getPostComments = async (postId) => {
    try {
      if (!postId) {
        console.error('Post ID is required for getPostComments');
        return { success: false, error: 'Post ID is required', comments: [] };
      }

      console.log(`Fetching comments for post ${postId}`);

      const headers = {
        'Content-Type': 'application/json',
      };

      // Add authorization header if token is available
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${API_URL}/api/comments?post_id=${postId}`, {
        method: 'GET',
        headers,
        credentials: 'include',
      });

      console.log(`Comments API response status: ${response.status}`);

      if (!response.ok) {
        if (response.status === 404) {
          console.log('No comments found, returning empty array');
          return {
            success: true,
            comments: [],
            pagination: null,
          };
        }
        
        const errorData = await response.json().catch(() => ({}));
        console.error('Comments API error:', errorData);
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log(`Successfully fetched ${data.comments?.length || 0} comments`);
      
      return {
        success: true,
        comments: data.comments || [],
        pagination: data.pagination || null,
      };

    } catch (error) {
      console.error('Error fetching post comments:', error);
      return {
        success: false,
        error: error.message,
        comments: [],
      };
    }
  };

  // CREATE COMMENT FUNCTION
  const createComment = async (postId, content) => {
    try {
      if (!postId || !content || !token) {
        throw new Error('Post ID, content, and authentication are required');
      }

      const response = await authenticatedRequest(`${API_URL}/api/comments`, {
        method: 'POST',
        body: JSON.stringify({
          post_id: postId,
          content: content.trim(),
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      toast.success('Comment added successfully!');
      return {
        success: true,
        comment: data,
      };

    } catch (error) {
      console.error('Error creating comment:', error);
      toast.error(error.message);
      return {
        success: false,
        error: error.message,
      };
    }
  };

  // UPDATE COMMENT FUNCTION
  const updateComment = async (commentId, content) => {
    try {
      if (!commentId || !content || !token) {
        throw new Error('Comment ID, content, and authentication are required');
      }

      const response = await authenticatedRequest(`${API_URL}/api/comments/${commentId}`, {
        method: 'PATCH',
        body: JSON.stringify({
          content: content.trim(),
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      toast.success('Comment updated successfully!');
      return {
        success: true,
        comment: data,
      };

    } catch (error) {
      console.error('Error updating comment:', error);
      toast.error(error.message);
      return {
        success: false,
        error: error.message,
      };
    }
  };

  // DELETE COMMENT FUNCTION
  const deleteComment = async (commentId) => {
    try {
      if (!commentId || !token) {
        throw new Error('Comment ID and authentication are required');
      }

      const response = await authenticatedRequest(`${API_URL}/api/comments/${commentId}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      toast.success('Comment deleted successfully!');
      return {
        success: true,
      };

    } catch (error) {
      console.error('Error deleting comment:', error);
      toast.error(error.message);
      return {
        success: false,
        error: error.message,
      };
    }
  };

  // LIKE COMMENT FUNCTION
  const toggleCommentLike = async (commentId) => {
    try {
      if (!commentId || !token) {
        throw new Error('Comment ID and authentication are required');
      }

      const response = await authenticatedRequest(`${API_URL}/api/comments/${commentId}/like`, {
        method: 'POST',
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return {
        success: true,
        liked: data.liked_by_user,
        likes_count: data.likes_count,
      };

    } catch (error) {
      console.error('Error toggling comment like:', error);
      toast.error(error.message);
      return {
        success: false,
        error: error.message,
      };
    }
  };

  // Login function
  const login = async (credentials) => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_URL}/api/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify(credentials),
      });

      const data = await response.json();

      if (response.ok) {
        const { access_token, user: userData, message } = data;
        
        if (access_token && userData) {
          setToken(access_token);
          setUser(userData);
          
          localStorage.setItem("token", access_token);
          localStorage.setItem("user", JSON.stringify(userData));
          
          toast.success(message || "Login successful!");
          return { success: true, user: userData };
        } else {
          throw new Error("Invalid response format");
        }
      } else {
        const errorMessage = data.error || data.message || "Login failed";
        setError(errorMessage);
        toast.error(errorMessage);
        return { success: false, error: errorMessage };
      }
    } catch (error) {
      console.error("Login error:", error);
      const errorMessage = error.message || "Network error during login";
      setError(errorMessage);
      toast.error(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      setLoading(false);
    }
  };

  // Register function
  const register = async (userData) => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_URL}/api/auth/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify(userData),
      });

      const data = await response.json();

      if (response.ok) {
        const { access_token, user: newUser, message } = data;
        
        if (access_token && newUser) {
          setToken(access_token);
          setUser(newUser);
          
          localStorage.setItem("token", access_token);
          localStorage.setItem("user", JSON.stringify(newUser));
          
          toast.success(message || "Registration successful!");
          return { success: true, user: newUser };
        } else {
          toast.success(data.message || "Registration successful! Please log in.");
          return { success: true, requiresLogin: true };
        }
      } else {
        const errorMessage = data.error || data.message || "Registration failed";
        setError(errorMessage);
        toast.error(errorMessage);
        return { success: false, error: errorMessage };
      }
    } catch (error) {
      console.error("Registration error:", error);
      const errorMessage = error.message || "Network error during registration";
      setError(errorMessage);
      toast.error(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      setLoading(false);
    }
  };

  // Logout function
  const logout = async (showMessage = true) => {
    try {
      if (token) {
        await fetch(`${API_URL}/api/auth/logout`, {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          credentials: "include",
        });
      }
    } catch (error) {
      console.error("Logout request failed:", error);
    } finally {
      setUser(null);
      setToken(null);
      setError(null);
      
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      
      if (showMessage) {
        toast.success("Logged out successfully");
      }
    }
  };

  // Change password function
  const changePassword = async (passwordData) => {
    try {
      setLoading(true);
      setError(null);

      const response = await authenticatedRequest(`${API_URL}/api/auth/change-password`, {
        method: "POST",
        body: JSON.stringify(passwordData),
      });

      const data = await response.json();

      if (response.ok) {
        toast.success(data.message || "Password changed successfully!");
        return { success: true };
      } else {
        const errorMessage = data.error || "Failed to change password";
        setError(errorMessage);
        toast.error(errorMessage);
        return { success: false, error: errorMessage };
      }
    } catch (error) {
      console.error("Change password error:", error);
      const errorMessage = error.message || "Network error";
      setError(errorMessage);
      toast.error(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      setLoading(false);
    }
  };

  // Forgot password function
  const forgotPassword = async (email) => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_URL}/api/auth/forgot-password`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify({ email }),
      });

      const data = await response.json();

      if (response.ok) {
        toast.success(data.message || "Password reset email sent!");
        return { success: true };
      } else {
        const errorMessage = data.error || "Failed to send reset email";
        setError(errorMessage);
        toast.error(errorMessage);
        return { success: false, error: errorMessage };
      }
    } catch (error) {
      console.error("Forgot password error:", error);
      const errorMessage = error.message || "Network error";
      setError(errorMessage);
      toast.error(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      setLoading(false);
    }
  };

  // Refresh token function
  const refreshToken = async () => {
    try {
      const response = await fetch(`${API_URL}/api/auth/refresh`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        credentials: "include",
      });

      if (response.ok) {
        const data = await response.json();
        const { access_token } = data;
        
        if (access_token) {
          setToken(access_token);
          localStorage.setItem("token", access_token);
          return true;
        }
      }
      
      logout(false);
      return false;
    } catch (error) {
      console.error("Token refresh failed:", error);
      logout(false);
      return false;
    }
  };

  // Update user profile
  const updateProfile = async (profileData) => {
    try {
      setLoading(true);
      setError(null);

      const response = await authenticatedRequest(`${API_URL}/api/auth/me`, {
        method: "PATCH",
        body: JSON.stringify(profileData),
      });

      const data = await response.json();

      if (response.ok) {
        setUser(data.user || data);
        localStorage.setItem("user", JSON.stringify(data.user || data));
        toast.success("Profile updated successfully!");
        return { success: true, user: data.user || data };
      } else {
        const errorMessage = data.error || "Failed to update profile";
        setError(errorMessage);
        toast.error(errorMessage);
        return { success: false, error: errorMessage };
      }
    } catch (error) {
      console.error("Update profile error:", error);
      const errorMessage = error.message || "Network error";
      setError(errorMessage);
      toast.error(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      setLoading(false);
    }
  };

  // Check if user is admin
  const isAdmin = () => {
    return user && user.is_admin === true;
  };

  // Check if user is blocked
  const isBlocked = () => {
    return user && user.is_blocked === true;
  };

  // Check if user is active
  const isActive = () => {
    return user && user.is_active !== false;
  };

  const value = {
    // State
    user,
    token,
    loading,
    error,
    
    // Authentication functions
    login,
    register,
    logout,
    
    // Profile management
    changePassword,
    forgotPassword,
    updateProfile,
    
    // Token management
    verifyToken,
    refreshToken,
    
    // Comment functions - THESE ARE THE MISSING FUNCTIONS
    getPostComments,      // <-- This is the main one causing the error
    createComment,
    updateComment,
    deleteComment,
    toggleCommentLike,
    
    // Utility functions
    authenticatedRequest,
    isAdmin,
    isBlocked,
    isActive,
    
    // Computed properties
    isAuthenticated: !!user && !!token,
    isGuest: !user || !token,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};