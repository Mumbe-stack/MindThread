
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

const Home = () => {
  const [posts, setPosts] = useState([]);

  useEffect(() => {
    fetch("/api/posts")
      .then((res) => res.json())
      .then(setPosts)
      .catch((err) => console.error("Failed to load posts", err));
  }, []);

  return (
    <div className="max-w-5xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6 text-center text-indigo-800">📰 Latest Posts</h1>
      {posts.length === 0 ? (
        <p className="text-gray-500 text-center">No posts available.</p>
      ) : (
        <div className="grid gap-4">
          {posts.map((post) => (
            <div key={post.id} className="border p-4 rounded shadow hover:shadow-md transition">
              <Link to={`/posts/${post.id}`}>
                <h2 className="text-xl font-semibold text-blue-700 hover:underline">{post.title}</h2>
                <p className="text-gray-600 mt-1">{post.content.slice(0, 120)}...</p>
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Home;
