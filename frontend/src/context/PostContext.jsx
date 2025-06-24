import { createContext, useContext, useState, useEffect } from "react";

const PostContext = createContext();
const api_url = import.meta.env.VITE_API_URL;

export const PostProvider = ({ children }) => {
  const [posts, setPosts] = useState([]);

  const fetchPosts = async () => {
  try {
    const res = await fetch(`${api_url}/api/posts`);

    const contentType = res.headers.get("content-type");
    if (!res.ok || !contentType.includes("application/json")) {
      const text = await res.text();
      console.error("Non-JSON response received:", text);
      throw new Error("API did not return JSON. Check backend.");
    }

    const data = await res.json();
    setPosts(data);
  } catch (err) {
    console.error("Failed to fetch posts:", err.message);
  }
};

  useEffect(() => {
    fetchPosts();
  }, []);

  return (
    <PostContext.Provider value={{ posts, setPosts, fetchPosts }}>
      {children}
    </PostContext.Provider>
  );
};

export const usePosts = () => useContext(PostContext);
