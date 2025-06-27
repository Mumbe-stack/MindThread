import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import LikeButton from "../components/LikeButton";

const VITE_API_URL = import.meta.env.VITE_API_URL || "https://mindthread-1.onrender.com";

const Posts = () => {
  const [posts, setPosts] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const fetchPosts = async () => {
    const token = localStorage.getItem("token");
    const headers = {
      "Content-Type": "application/json",
      Accept: "application/json",
    };
    if (token) headers.Authorization = `Bearer ${token}`;

    try {
      const res = await fetch(`${VITE_API_URL}/api/posts`, {
        method: "GET",
        credentials: "include",
        headers,
      });

      const contentType = res.headers.get("content-type") || "";

      if (!res.ok) {
        const raw = await res.text();
        
        throw new Error(`HTTP ${res.status}: ${raw}`);
      }

      if (!contentType.includes("application/json")) {
        const raw = await res.text();
        throw new Error(`Expected JSON but received: ${raw.slice(0, 100)}`);
      }

      const data = await res.json();
      return Array.isArray(data) ? data : [];
    } catch (err) {
      throw new Error(err.message || "Failed to fetch posts");
    }
  };

  useEffect(() => {
    setLoading(true);
    fetchPosts()
      .then((data) => {
        setPosts(data);
        setError("");
      })
      .catch((err) => {
        setError(err.message);
        setPosts([]);
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-5xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6 text-center text-indigo-800">
        All Posts
      </h1>

      {loading && (
        <p className="text-center text-gray-500 mb-4">Loading posts...</p>
      )}

      {error && (
        <p className="text-red-600 text-center font-medium mb-4">{error}</p>
      )}

      {!loading && posts.length === 0 && !error ? (
        <p className="text-gray-500 text-center">No posts available.</p>
      ) : (
        <div className="grid gap-4">
          {posts.map((post) => (
            <div
              key={post.id}
              className="border p-4 rounded shadow hover:shadow-md transition bg-white"
            >
              <Link to={`/posts/${post.id}`}>
                <h2 className="text-xl font-semibold text-blue-700 hover:underline">
                  {post.title}
                </h2>
                <p className="text-gray-600 mt-1">
                  {post.content.slice(0, 120)}...
                </p>
              </Link>

              <div className="mt-3 flex items-center justify-between">
                <p className="text-sm text-gray-500">
                  By User #{post.user_id} •{" "}
                  {new Date(post.created_at).toLocaleDateString()}
                </p>
                <LikeButton type="post" id={post.id} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Posts;
