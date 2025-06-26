import { createContext, useContext, useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";

const AuthContext = createContext();
const VITE_API_URL = import.meta.env.VITE_API_URL;

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem("token"));
  const navigate = useNavigate();

  const authHeader = token ? { Authorization: `Bearer ${token}` } : {};

  useEffect(() => {
    if (token) {
      fetchCurrentUser();
    }
  }, [token]);

  const fetchCurrentUser = async () => {
    try {
      const res = await fetch(`${VITE_API_URL}/api/auth/me`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          ...authHeader,
        },
        credentials: "include",
      });

      if (!res.ok) throw new Error("Unauthorized or session expired");

      const data = await res.json();
      setUser({
        id: data.id,
        username: data.username,
        email: data.email,
        is_admin: data.is_admin,
        created_at: data.created_at,
      });
    } catch (error) {
      console.error("❌ Fetch user failed:", error.message);
      toast.error("Session expired. Please login again.");
      handleUnauth();
    }
  };

  const handleUnauth = () => {
    localStorage.removeItem("token");
    setToken(null);
    setUser(null);
  };

  const login = async (email, password) => {
    try {
      const res = await fetch(`${VITE_API_URL}/api/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          password: password.trim(),
        }),
      });

      const data = await res.json();

      if (res.ok) {
        localStorage.setItem("token", data.access_token);
        setToken(data.access_token);
        setUser({
          id: data.user_id,
          username: data.username,
          is_admin: data.is_admin,
          email: data.email,
        });
        toast.success("Login successful");
        return true;
      } else {
        toast.error(data.error || "Invalid credentials");
        return false;
      }
    } catch (err) {
      console.error("Login error:", err);
      toast.error("Network error during login");
      return false;
    }
  };

  const register = async (form) => {
    try {
      const res = await fetch(`${VITE_API_URL}/api/auth/register`, {
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
      } else {
        toast.error(data.error || "Registration failed");
      }
    } catch {
      toast.error("Network error during registration");
    }
  };

  const logout = async () => {
    try {
      await fetch(`${VITE_API_URL}/api/auth/logout`, {
        method: "DELETE",
        headers: {
          ...authHeader,
        },
        credentials: "include",
      });
      toast.success("Logged out successfully");
    } catch {
      toast.error("Logout failed");
    } finally {
      handleUnauth();
      navigate("/");
    }
  };

  const updateProfile = async (updates) => {
    try {
      const res = await fetch(`${VITE_API_URL}/api/users/${user.id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          ...authHeader,
        },
        body: JSON.stringify(updates),
      });

      if (res.ok) {
        toast.success("Profile updated");
        fetchCurrentUser();
      } else {
        toast.error("Update failed");
      }
    } catch {
      toast.error("Error updating profile");
    }
  };

  const deleteUser = async () => {
    try {
      const res = await fetch(`${VITE_API_URL}/api/users/${user.id}`, {
        method: "DELETE",
        headers: {
          ...authHeader,
        },
        credentials: "include",
      });

      if (res.ok) {
        toast.success("Account deleted");
        await logout();
      } else {
        toast.error("Failed to delete account");
      }
    } catch {
      toast.error("Error deleting account");
    }
  };

  const fetchAllUsers = async () => {
    try {
      const res = await fetch(`${VITE_API_URL}/api/users`, {
        headers: {
          ...authHeader,
        },
        credentials: "include",
      });

      if (!res.ok) throw new Error("Failed to fetch users");
      return await res.json();
    } catch {
      toast.error("Unable to fetch users");
      return [];
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        login,
        register,
        logout,
        updateProfile,
        deleteUser,
        fetchAllUsers,
        setUser, // optional utility
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
