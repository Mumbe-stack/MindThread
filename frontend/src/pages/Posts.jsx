// src/pages/Posts.jsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import LikeButton from "../components/LikeButton"; // ✅ Make sure this path is correct

const Posts = () => {
  const [posts, setPosts] = useState([]);
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

  useEffect(() => {
    fetch(`${API_BASE_URL}/posts`)
      .then((res) => res.json())
      .then(setPosts)
      .catch((err) => console.error("Failed to load posts", err));
  }, [API_BASE_URL]);

  return (
    <div className="max-w-5xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6 text-center text-indigo-800">
        All Posts
      </h1>

      {posts.length === 0 ? (
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

                {/* Like button for each post */}
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
