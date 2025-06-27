import { createContext, useContext, useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";

const AuthContext = createContext();
const api_url = import.meta.env.VITE_API_URL || "https://mindthread-1.onrender.com";

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(null);
  const [refreshToken, setRefreshToken] = useState(null);
  const navigate = useNavigate();

  // Initialize authentication state from localStorage
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        const storedToken = localStorage.getItem("access_token");
        const storedRefreshToken = localStorage.getItem("refresh_token");
        const storedUser = localStorage.getItem("user");

        if (storedToken) {
          setToken(storedToken);
          setRefreshToken(storedRefreshToken);
          
          if (storedUser) {
            try {
              const parsedUser = JSON.parse(storedUser);
              setUser(parsedUser);
            } catch (parseError) {
              console.error("Error parsing stored user:", parseError);
              localStorage.removeItem("user");
            }
          }
          
          // Verify token validity
          await verifyCurrentUser(storedToken);
        }
      } catch (error) {
        console.error("Auth initialization error:", error);
        clearAuthData();
      } finally {
        setLoading(false);
      }
    };

    initializeAuth();
  }, []);

  const clearAuthData = () => {
    setUser(null);
    setToken(null);
    setRefreshToken(null);
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
  };

  const storeAuthData = (authData) => {
    const { access_token, refresh_token, user: userData } = authData;
    
    setToken(access_token);
    setUser(userData);
    
    localStorage.setItem("access_token", access_token);
    localStorage.setItem("user", JSON.stringify(userData));
    
    if (refresh_token) {
      setRefreshToken(refresh_token);
      localStorage.setItem("refresh_token", refresh_token);
    }
  };

  const refreshAccessToken = async () => {
    try {
      const storedRefreshToken = localStorage.getItem("refresh_token");
      if (!storedRefreshToken) {
        throw new Error("No refresh token available");
      }

      const res = await fetch(`${api_url}/api/auth/refresh`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${storedRefreshToken}`,
        },
        credentials: "include",
      });

      if (!res.ok) {
        throw new Error("Token refresh failed");
      }

      const data = await res.json();
      
      if (data.success && data.access_token) {
        setToken(data.access_token);
        localStorage.setItem("access_token", data.access_token);
        return data.access_token;
      } else {
        throw new Error("Invalid refresh response");
      }
    } catch (error) {
      console.error("Token refresh error:", error);
      clearAuthData();
      toast.error("Session expired. Please login again.");
      navigate("/login");
      throw error;
    }
  };

  const verifyCurrentUser = async (tokenToVerify = token) => {
    if (!tokenToVerify) return false;

    try {
      const res = await fetch(`${api_url}/api/auth/me`, {
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${tokenToVerify}`,
        },
        credentials: "include",
      });

      if (res.ok) {
        const data = await res.json();
        if (data.success && data.user) {
          setUser(data.user);
          localStorage.setItem("user", JSON.stringify(data.user));
          return true;
        }
      } else if (res.status === 401) {
        // Token expired, try to refresh
        try {
          const newToken = await refreshAccessToken();
          return await verifyCurrentUser(newToken);
        } catch (refreshError) {
          return false;
        }
      }
      
      return false;
    } catch (error) {
      console.error("User verification error:", error);
      return false;
    }
  };

  const login = async (credentials) => {
    try {
      const res = await fetch(`${api_url}/api/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify(credentials),
      });

      const data = await res.json();

      if (res.ok && data.success) {
        // Handle both old and new response formats
        const userData = data.user || {
          id: data.user_id,
          username: data.username,
          email: data.email,
          is_admin: data.is_admin,
        };

        storeAuthData({
          access_token: data.access_token,
          refresh_token: data.refresh_token,
          user: userData
        });

        toast.success("Login successful!");
        navigate("/");
        return { success: true, user: userData };
      } else {
        // Handle specific error cases
        let errorMessage = "Login failed";
        
        if (res.status === 401) {
          errorMessage = data.error || "Invalid credentials";
        } else if (res.status === 403) {
          errorMessage = data.error || "Account is blocked or inactive";
        } else if (res.status === 400) {
          errorMessage = data.error || "Invalid input data";
        } else {
          errorMessage = data.error || "Login failed";
        }
        
        toast.error(errorMessage);
        return { success: false, error: errorMessage };
      }
    } catch (error) {
      console.error("Login error:", error);
      const errorMessage = "Network error during login";
      toast.error(errorMessage);
      return { success: false, error: errorMessage };
    }
  };

  const register = async (userData) => {
    try {
      const res = await fetch(`${api_url}/api/auth/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify(userData),
      });

      const data = await res.json();

      if (res.ok && data.success) {
        // Handle auto-login after registration if tokens are provided
        if (data.access_token) {
          const newUser = data.user || {
            id: data.user_id,
            username: userData.username,
            email: userData.email,
            is_admin: false,
          };

          storeAuthData({
            access_token: data.access_token,
            refresh_token: data.refresh_token,
            user: newUser
          });

          toast.success("Registration successful! You are now logged in.");
          navigate("/");
        } else {
          toast.success("Account created successfully! Please login.");
          navigate("/login");
        }
        
        return { success: true };
      } else {
        // Handle specific error cases
        let errorMessage = "Registration failed";
        
        if (res.status === 409) {
          errorMessage = data.error || "User already exists";
        } else if (res.status === 400) {
          errorMessage = data.error || "Invalid input data";
        } else {
          errorMessage = data.error || "Registration failed";
        }
        
        toast.error(errorMessage);
        return { success: false, error: errorMessage };
      }
    } catch (error) {
      console.error("Registration error:", error);
      const errorMessage = "Network error during registration";
      toast.error(errorMessage);
      return { success: false, error: errorMessage };
    }
  };

  const logout = async () => {
    try {
      // Call logout endpoint if token exists
      if (token) {
        await fetch(`${api_url}/api/auth/logout`, {
          method: "POST", // Changed from DELETE to POST to match backend
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`,
          },
          credentials: "include",
        });
      }
    } catch (error) {
      console.error("Logout API error:", error);
      // Continue with local logout even if API call fails
    } finally {
      clearAuthData();
      toast.success("Logged out successfully");
      navigate("/");
    }
  };

  const updateProfile = async (updates) => {
    try {
      const res = await fetch(`${api_url}/api/users/${user.id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        credentials: "include",
        body: JSON.stringify(updates),
      });

      if (res.ok) {
        const data = await res.json();
        toast.success("Profile updated successfully");
        
        // Refresh user data
        await verifyCurrentUser();
        return { success: true, data };
      } else {
        const errorData = await res.json();
        const errorMessage = errorData.error || "Update failed";
        toast.error(errorMessage);
        return { success: false, error: errorMessage };
      }
    } catch (error) {
      console.error("Update profile error:", error);
      const errorMessage = "Error updating profile";
      toast.error(errorMessage);
      return { success: false, error: errorMessage };
    }
  };

  const deleteUser = async () => {
    try {
      const res = await fetch(`${api_url}/api/users/me`, {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        credentials: "include",
      });

      if (res.ok) {
        toast.success("Account deleted successfully");
        clearAuthData();
        navigate("/");
        return { success: true };
      } else {
        const errorData = await res.json();
        const errorMessage = errorData.error || "Failed to delete account";
        toast.error(errorMessage);
        return { success: false, error: errorMessage };
      }
    } catch (error) {
      console.error("Delete user error:", error);
      const errorMessage = "Error deleting account";
      toast.error(errorMessage);
      return { success: false, error: errorMessage };
    }
  };

  const fetchAllUsers = async () => {
    try {
      const res = await fetch(`${api_url}/api/users`, {
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        credentials: "include",
      });

      if (!res.ok) {
        if (res.status === 401) {
          // Try to refresh token
          try {
            const newToken = await refreshAccessToken();
            const retryRes = await fetch(`${api_url}/api/users`, {
              headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${newToken}`,
              },
              credentials: "include",
            });
            
            if (retryRes.ok) {
              return await retryRes.json();
            }
          } catch (refreshError) {
            throw new Error("Authentication failed");
          }
        }
        
        const errorData = await res.json();
        throw new Error(errorData.error || "Failed to fetch users");
      }

      return await res.json();
    } catch (error) {
      console.error("Fetch users error:", error);
      toast.error("Unable to fetch users");
      return [];
    }
  };

  // Enhanced API request helper with automatic token refresh
  const authenticatedRequest = async (url, options = {}) => {
    const makeRequest = async (tokenToUse) => {
      return fetch(url, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${tokenToUse}`,
          ...options.headers,
        },
        credentials: "include",
      });
    };

    try {
      let response = await makeRequest(token);

      // If unauthorized, try to refresh token
      if (response.status === 401 && refreshToken) {
        try {
          const newToken = await refreshAccessToken();
          response = await makeRequest(newToken);
        } catch (refreshError) {
          clearAuthData();
          navigate("/login");
          throw new Error("Session expired. Please login again.");
        }
      }

      return response;
    } catch (error) {
      console.error("Authenticated request error:", error);
      throw error;
    }
  };

  const refreshUser = async () => {
    if (token) {
      await verifyCurrentUser();
    }
  };

  // Check if user is authenticated
  const isAuthenticated = Boolean(token && user);
  const isAdmin = Boolean(user?.is_admin);
  const isBlocked = Boolean(user?.is_blocked);

  const value = {
    user,
    token,
    refreshToken,
    loading,
    isAuthenticated,
    isAdmin,
    isBlocked,
    login,
    register,
    logout,
    updateProfile,
    deleteUser,
    fetchAllUsers,
    refreshUser,
    clearAuthData,
    authenticatedRequest,
    refreshAccessToken,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

export default AuthContext;