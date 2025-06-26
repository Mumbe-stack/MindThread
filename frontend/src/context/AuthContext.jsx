import { createContext, useContext, useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";

const AuthContext = createContext();
const api_url = import.meta.env.VITE_API_URL || "https://mindthread.onrender.com";

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem("token"));
  const navigate = useNavigate();

  useEffect(() => {
    if (token) {
      fetchCurrentUser();
    }
  }, [token]);

  const fetchCurrentUser = async () => {
    try {
      const res = await fetch(`${api_url}/api/users/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!res.ok) throw new Error("Unauthorized");

      const data = await res.json();
      setUser({
        id: data.id,
        username: data.username,
        email: data.email,
        is_admin: data.is_admin,
        created_at: data.created_at,
      });
    } catch (err) {
      console.error("Fetch user error:", err);
      handleUnauth();
      toast.error("Session expired. Please login again.");
    }
  };

  const handleUnauth = () => {
    localStorage.removeItem("token");
    setToken(null);
    setUser(null);
  };

  const login = async (email, password) => {
    try {
      const res = await fetch(`${api_url}/api/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include", // only if using cookies
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();

      if (!res.ok) {
        console.warn("Login failed:", data);
        toast.error(data.error || "Invalid credentials");
        return false;
      }

      localStorage.setItem("token", data.access_token);
      setToken(data.access_token);
      setUser({
        id: data.user_id,
        username: data.username,
        is_admin: data.is_admin,
      });
      toast.success("Logged in successfully");
      return true;
    } catch (err) {
      console.error("Login error:", err);
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

      if (!res.ok) {
        toast.error(data.error || "Registration failed");
        return;
      }

      toast.success("Account created successfully");
      navigate("/login");
    } catch (err) {
      toast.error("Network error during registration");
    }
  };

  const logout = async () => {
    try {
      await fetch(`${api_url}/api/auth/logout`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
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
      const res = await fetch(`${api_url}/api/users/${user.id}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
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
      const res = await fetch(`${api_url}/api/users`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!res.ok) throw new Error("Fetch failed");
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
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
