import { createContext, useContext, useState, useEffect } from "react";
import toast from "react-hot-toast";

const PostContext = createContext();
const api_url = import.meta.env.VITE_API_URL || "http://localhost:5000";

export const usePosts = () => useContext(PostContext);

export const PostProvider = ({ children }) => {
  const [posts, setPosts] = useState([]);

  const fetchPosts = async () => {
    try {
      const res = await fetch(`${api_url}/api/posts/`, {
        method: "GET",
        credentials: "include", 
        headers: {
          "Content-Type": "application/json",
        },
      });

      const contentType = res.headers.get("content-type") || "";
      if (!res.ok || !contentType.includes("application/json")) {
        throw new Error("API did not return valid JSON");
      }

      const data = await res.json();
      setPosts(data);
    } catch (err) {
      toast.error("Failed to load posts");
      console.error("Fetch error:", err.message);
    }
  };

  useEffect(() => {
    fetchPosts();
  }, []);

  return (
    <PostContext.Provider value={{ posts, fetchPosts, setPosts }}>
      {children}
    </PostContext.Provider>
  );
};
