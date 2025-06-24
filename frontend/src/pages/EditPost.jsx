import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import toast from "react-hot-toast";

const api_url = import.meta.env.VITE_API_URL || "";

const EditPost = () => {
  const { id } = useParams();
  const [post, setPost] = useState({ title: "", content: "" });
  const navigate = useNavigate();

  useEffect(() => {
    fetch(`${api_url}/api/posts/${id}`)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch post");
        return res.json();
      })
      .then(setPost)
      .catch(() => toast.error("Failed to load post"));
  }, [id]);

  const handleUpdate = async (e) => {
    e.preventDefault();
    const token = localStorage.getItem("token");

    const res = await fetch(`${api_url}/api/posts/${id}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify(post)
    });

    if (res.ok) {
      toast.success("Post updated successfully");
      navigate(`/posts/${id}`);
    } else {
      toast.error("Failed to update post");
    }
  };

  return (
    <div className="max-w-xl mx-auto p-6 mt-10 bg-white shadow rounded">
      <h2 className="text-2xl font-bold mb-6">✏️ Edit Post</h2>
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
        <button className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">
          Save Changes
        </button>
      </form>
    </div>
  );
};

export default EditPost;
