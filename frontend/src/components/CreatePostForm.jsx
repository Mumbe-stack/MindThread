import { useState } from "react";
import toast from "react-hot-toast";
import RichTextEditor from "../components/RichTextEditor";

const VITE_API_URL = import.meta.env.VITE_API_URL|| "https://mindthread-1.onrender.com";

const CreatePostForm = ({ onClose }) => {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    const token = localStorage.getItem("token");

    if (!title.trim() || !content.trim()) {
      toast.error("Title and content are required");
      return;
    }

    try {
      const res = await fetch(`${VITE_API_URL}/api/posts`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ title, content }),
      });

      if (res.ok) {
        toast.success("Post created successfully");
        setTitle("");
        setContent("");
        if (onClose) onClose(); 
        const data = await res.json();
        toast.error(data.error || "Failed to create post");
      }
    } catch (err) {
     
      toast.error("Something went wrong");
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 p-4">
      <input
        type="text"
        placeholder="Post Title"
        className="w-full p-2 border rounded"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        required
      />

      <RichTextEditor value={content} onChange={setContent} />

      <button
        type="submit"
        className="w-full bg-indigo-600 text-white py-2 rounded hover:bg-indigo-700"
      >
        Publish Post
      </button>
    </form>
  );
};

export default CreatePostForm;