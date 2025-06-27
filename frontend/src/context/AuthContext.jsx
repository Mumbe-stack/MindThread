import { createContext, useContext, useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";

const AuthContext = createContext();
const api_url = import.meta.env.VITE_API_URL || "https://mindthread-1.onrender.com";

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true); 
  const navigate = useNavigate();
  const [token, setToken] = useState(localStorage.getItem("token"));

  useEffect(() => {
    if (token) {
      fetchCurrentUser();
    } else {
      setLoading(false); 
    }
  }, [token]);

  const fetchCurrentUser = async () => {
    try {
      setLoading(true);
      
    
      const res = await fetch(`${api_url}/api/auth/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (res.ok) {
        const data = await res.json();
        setUser({
          id: data.id,
          username: data.username,
          email: data.email,
          is_admin: data.is_admin,
          is_blocked: data.is_blocked, 
          created_at: data.created_at,
        });
      } else {
        
        localStorage.removeItem("token");
        setToken(null);
        setUser(null);
      }
    } catch (error) {
      console.error("Failed to fetch user data:", error);
      toast.error("Failed to fetch user data");
      
      localStorage.removeItem("token");
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    try {
      const res = await fetch(`${api_url}/api/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();

      if (res.ok) {
        localStorage.setItem("token", data.access_token);
        setToken(data.access_token);
        setUser({
          id: data.user_id,
          username: data.username,
          email: data.email, 
          is_admin: data.is_admin,
        });
        toast.success("Login successful");
        navigate("/");
        return true;
      } else {
        toast.error(data.error || "Invalid credentials");
        return false;
      }
    } catch (error) {
      console.error("Login error:", error);
      toast.error("Network error during login");
      return false;
    }
  };

  const register = async (form) => {
    try {
      const res = await fetch(`${api_url}/api/auth/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(form),
      });

      const data = await res.json();

      if (res.ok) {
        toast.success("Account created successfully");
        navigate("/login");
        return true;
      } else {
        toast.error(data.error || "Registration failed");
        return false;
      }
    } catch (error) {
      console.error("Registration error:", error);
      toast.error("Network error during registration");
      return false;
    }
  };

  const logout = async () => {
    try {
     
      const res = await fetch(`${api_url}/api/auth/logout`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      
      localStorage.removeItem("token");
      setToken(null);
      setUser(null);
      
      if (res.ok) {
        toast.success("Logged out successfully");
      } else {
        toast.success("Logged out locally"); 
      }
      
      navigate("/");
    } catch (error) {
      console.error("Logout error:", error);
      
      localStorage.removeItem("token");
      setToken(null);
      setUser(null);
      toast.success("Logged out locally");
      navigate("/");
    }
  };

  const updateProfile = async (updates) => {
    try {
      const res = await fetch(`${api_url}/api/users/${user.id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(updates),
      });

      if (res.ok) {
        toast.success("Profile updated");
        await fetchCurrentUser(); 
        return true;
      } else {
        const data = await res.json();
        toast.error(data.error || "Update failed");
        return false;
      }
    } catch (error) {
      console.error("Update profile error:", error);
      toast.error("Error updating profile");
      return false;
    }
  };

  const deleteUser = async () => {
    try {
      
      const res = await fetch(`${api_url}/api/users/me`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (res.ok) {
        toast.success("Account deleted");
        
        localStorage.removeItem("token");
        setToken(null);
        setUser(null);
        navigate("/");
        return true;
      } else {
        const data = await res.json();
        toast.error(data.error || "Failed to delete account");
        return false;
      }
    } catch (error) {
      console.error("Delete user error:", error);
      toast.error("Error deleting account");
      return false;
    }
  };

  const fetchAllUsers = async () => {
    try {
      const res = await fetch(`${api_url}/api/users`, { 
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || "Failed to fetch users");
      }
      
      return await res.json();
    } catch (err) {
      console.error("Fetch users error:", err);
      toast.error("Unable to fetch users");
      return [];
    }
  };

 
  const refreshUser = async () => {
    if (token) {
      await fetchCurrentUser();
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        login,
        register,
        logout,
        updateProfile,
        deleteUser,
        fetchAllUsers,
        refreshUser, 
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);