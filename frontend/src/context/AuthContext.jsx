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

 
  useEffect(() => {
    const initializeAuth = () => {
      try {
        const storedToken = localStorage.getItem("token");
        const storedUser = localStorage.getItem("user");

        if (storedToken && storedUser) {
          setToken(storedToken);
          setUser(JSON.parse(storedUser));
          
          
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

 
  const verifyToken = async (tokenToVerify = token) => {
    if (!tokenToVerify) return false;

    try {
      const response = await fetch(`${API_URL}/api/verify-token`, {
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


  const login = async (credentials) => {
    try {
      setLoading(true);
      setError(null);

      console.log("Attempting login with:", { ...credentials, password: "[HIDDEN]" });

      const response = await fetch(`${API_URL}/api/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify(credentials),
      });

      const data = await response.json();
      console.log("Login response:", { ...data, access_token: data.access_token ? "[PRESENT]" : "[MISSING]" });

      if (response.ok && data.success) {
     
        const { access_token, refresh_token, user: userData, message } = data;
        
        if (access_token && userData) {
       
          const userInfo = {
            id: userData.id,
            username: userData.username,
            email: userData.email,
            is_admin: userData.is_admin || false,
            is_blocked: userData.is_blocked || false,
            is_active: userData.is_active !== false, 
            created_at: userData.created_at,
            updated_at: userData.updated_at
          };
          
          console.log("Setting user data:", userInfo);
          
          setToken(access_token);
          setUser(userInfo);
          
          
          localStorage.setItem("token", access_token);
          localStorage.setItem("user", JSON.stringify(userInfo));
          
       
          if (refresh_token) {
            localStorage.setItem("refresh_token", refresh_token);
          }
          
          toast.success(message || "Login successful!");
          return { success: true, user: userInfo };
        } else {
          throw new Error("Invalid response format: missing token or user data");
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

 
  const register = async (userData) => {
    try {
      setLoading(true);
      setError(null);

      console.log("Attempting registration with:", { ...userData, password: "[HIDDEN]" });

      const response = await fetch(`${API_URL}/api/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify(userData),
      });

      const data = await response.json();
      console.log("Registration response:", { ...data, access_token: data.access_token ? "[PRESENT]" : "[MISSING]" });

      if (response.ok && data.success) {
     
        const { access_token, refresh_token, user: userInfo, message } = data;
        
        if (access_token && userInfo) {
       
          const newUser = {
            id: userInfo.id,
            username: userInfo.username,
            email: userInfo.email,
            is_admin: userInfo.is_admin || false,
            is_blocked: userInfo.is_blocked || false,
            is_active: userInfo.is_active !== false,
            created_at: userInfo.created_at,
            updated_at: userInfo.updated_at
          };
          
          console.log("Setting registered user data:", newUser);
          
          setToken(access_token);
          setUser(newUser);
          
         
          localStorage.setItem("token", access_token);
          localStorage.setItem("user", JSON.stringify(newUser));
          
        
          if (refresh_token) {
            localStorage.setItem("refresh_token", refresh_token);
          }
          
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


  const logout = async (showMessage = true) => {
    try {
      if (token) {
      
        await fetch(`${API_URL}/api/logout`, {
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
      localStorage.removeItem("refresh_token");
      
      if (showMessage) {
        toast.success("Logged out successfully");
      }
    }
  };


  const deleteUser = async () => {
    try {
      setLoading(true);
      
      if (!user || !token) {
        throw new Error("No user logged in");
      }

      const response = await authenticatedRequest(`${API_URL}/api/users/${user.id}`, {
        method: "DELETE",
      });

      if (response.ok) {
  
        await logout(false);
        return { success: true };
      } else {
        const data = await response.json();
        const errorMessage = data.error || "Failed to delete account";
        throw new Error(errorMessage);
      }
    } catch (error) {
      console.error("Delete user error:", error);
      toast.error(error.message || "Failed to delete account");
      throw error;
    } finally {
      setLoading(false);
    }
  };


  const changePassword = async (passwordData) => {
    try {
      setLoading(true);
      setError(null);

      const response = await authenticatedRequest(`${API_URL}/api/change-password`, {
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


  const forgotPassword = async (email) => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_URL}/api/forgot-password`, {
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

 
  const refreshToken = async () => {
    try {
      const refresh_token = localStorage.getItem("refresh_token");
      
      if (!refresh_token) {
        logout(false);
        return false;
      }

      const response = await fetch(`${API_URL}/api/refresh`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${refresh_token}`,
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


  const updateProfile = async (profileData) => {
    try {
      setLoading(true);
      setError(null);

      const response = await authenticatedRequest(`${API_URL}/api/me`, {
        method: "PATCH",
        body: JSON.stringify(profileData),
      });

      const data = await response.json();

      if (response.ok) {
        const updatedUser = data.user || data;
        setUser(updatedUser);
        localStorage.setItem("user", JSON.stringify(updatedUser));
        toast.success("Profile updated successfully!");
        return { success: true, user: updatedUser };
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


  const isAdmin = () => {
    return user && user.is_admin === true;
  };


  const isBlocked = () => {
    return user && user.is_blocked === true;
  };


  const isActive = () => {
    return user && user.is_active !== false;
  };

  const value = {
  
    user,
    token,
    loading,
    error,
    
  
    login,
    register,
    logout,
    deleteUser,
    
 
    changePassword,
    forgotPassword,
    updateProfile,
    
  
    verifyToken,
    refreshToken,
    
  
    authenticatedRequest,
    isAdmin,
    isBlocked,
    isActive,
    
 
    isAuthenticated: !!user && !!token,
    isGuest: !user || !token,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};