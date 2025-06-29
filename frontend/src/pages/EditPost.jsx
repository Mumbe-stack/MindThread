import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";

const VITE_API_URL = import.meta.env.VITE_API_URL|| "https://mindthread-1.onrender.com";

const EditPost = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [post, setPost] = useState({ title: "", content: "" });

  useEffect(() => {
    const fetchPost = async () => {
      const token = localStorage.getItem("token");

      if (!token) {
        toast.error("You must be logged in.");
        navigate("/login");
        return;
      }

      try {
        const res = await fetch(`${VITE_API_URL}/api/posts/${id}`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (!res.ok) {
          if (res.status === 403) {
            toast.error("You are not authorized to edit this post.");
            navigate("/posts");
            return;
          }
          if (res.status === 401) {
            toast.error("Session expired. Please log in again.");
            navigate("/login");
            return;
          }
          if (res.status === 404) {
            toast.error("Post not found.");
            navigate("/posts");
            return;
          }
          throw new Error("Failed to fetch post.");
        }

        const data = await res.json();
        setPost({ title: data.title, content: data.content });
      } catch (err) {
        toast.error("Could not load the post.");
      }
    };

    fetchPost();
  }, [id, navigate]);

  const handleUpdate = async (e) => {
    e.preventDefault();
    const token = localStorage.getItem("token");

    if (!token) {
      toast.error("You must be logged in.");
      navigate("/login");
      return;
    }

    if (!post.title.trim() || !post.content.trim()) {
      toast.error("Title and content cannot be empty.");
      return;
    }

    try {
      const res = await fetch(`${VITE_API_URL}/api/posts/${id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(post),
      });

      if (res.ok) {
        const data = await res.json();
        toast.success(data.message || "Post updated successfully.");
        navigate(`/posts/${id}`);
      } else {
        const error = await res.json();
        toast.error(error.message || "Failed to update post.");
      }
    } catch (err) {
      toast.error("Something went wrong while updating.");
    }
  };

  return (
    <div className="max-w-xl mx-auto p-6 mt-10 bg-white shadow rounded">
      <h2 className="text-2xl font-bold mb-6 text-indigo-800">✏️ Edit Post</h2>
      <form onSubmit={handleUpdate} className="space-y-4">
        <input
          type="text"
          className="w-full border p-2 rounded"
          placeholder="Post title"
          value={post.title}
          onChange={(e) => setPost({ ...post, title: e.target.value })}
          required
        />
        <textarea
          className="w-full border p-2 rounded h-40"
          placeholder="Post content"
          value={post.content}
          onChange={(e) => setPost({ ...post, content: e.target.value })}
          required
        />
        <div className="flex justify-between">
          <button
            type="submit"
            className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
          >
            Save Changes
          </button>
          <button
            type="button"
            onClick={() => navigate(`/posts/${id}`)}
            className="text-gray-500 hover:underline"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
};

export default EditPost;