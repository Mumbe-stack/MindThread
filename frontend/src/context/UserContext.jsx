import { createContext, useContext, useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";


const API_URL = import.meta.env.VITE_API_URL;

export const UserProvider = ({ children }) => {
  const navigate = useNavigate();
  const [currentUser, setCurrentUser] = useState(null);
  const [authToken, setAuthToken] = useState(() => localStorage.getItem("token"));

  useEffect(() => {
    if (authToken) {
      fetch(`${API_URL}/users/me`, {
        headers: { Authorization: `Bearer ${authToken}` }
      })
        .then(res => res.ok ? res.json() : Promise.reject("Unauthorized"))
        .then(setCurrentUser)
        .catch(() => {
          logout();
          toast.error("Session expired. Please log in again.");
        });
    }
  }, [authToken]);

  const register = async (username, email, password) => {
    toast.loading("Registering...");
    try {
      const res = await fetch(`${API_URL}/users/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, email, password })
      });
      const data = await res.json();
      toast.dismiss();
      if (res.ok) {
        toast.success("Registration successful. Please log in.");
        navigate("/login");
      } else {
        toast.error(data.error || "Registration failed");
      }
    } catch (err) {
      toast.dismiss();
      toast.error("Something went wrong");
    }
  };

  const login = async (email, password) => {
    toast.loading("Logging in...");
    try {
      const res = await fetch(`${API_URL}/users/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });
      const data = await res.json();
      toast.dismiss();
      if (res.ok) {
        localStorage.setItem("token", data.token);
        setAuthToken(data.token);
        setCurrentUser(data.user);
        toast.success("Login successful!");
        navigate("/");
        return true;
      } else {
        toast.error(data.error || "Login failed");
        return false;
      }
    } catch (err) {
      toast.dismiss();
      toast.error("Something went wrong");
      return false;
    }
  };

  const logout = () => {
    localStorage.removeItem("token");
    setAuthToken(null);
    setCurrentUser(null);
    toast.success("Logged out");
    navigate("/login");
  };

  const updateProfile = async (updates) => {
    toast.loading("Updating profile...");
    try {
      const res = await fetch(`${API_URL}/users/${currentUser.id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${authToken}`
        },
        body: JSON.stringify(updates)
      });
      const data = await res.json();
      toast.dismiss();
      if (res.ok) {
        setCurrentUser(data);
        toast.success("Profile updated");
      } else {
        toast.error(data.error || "Update failed");
      }
    } catch {
      toast.dismiss();
      toast.error("Something went wrong");
    }
  };

  const deleteProfile = async () => {
    const confirm = window.confirm("Are you sure you want to delete your account?");
    if (!confirm) return;

    toast.loading("Deleting account...");
    try {
      const res = await fetch(`${API_URL}/users/${currentUser.id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${authToken}` }
      });
      const data = await res.json();
      toast.dismiss();
      if (res.ok) {
        logout();
        toast.success("Account deleted");
      } else {
        toast.error(data.error || "Failed to delete account");
      }
    } catch {
      toast.dismiss();
      toast.error("Something went wrong");
    }
  };

  return (
    <UserContext.Provider
      value={{
        currentUser,
        authToken,
        register,
        login,
        logout,
        updateProfile,
        deleteProfile
      }}
    >
      {children}
    </UserContext.Provider>
  );
};

export const UserContext = createContext();
export const useUser = () => useContext(UserContext);
