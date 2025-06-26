import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import toast from "react-hot-toast";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";

const AddPost = () => {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [tags, setTags] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState({});

  const navigate = useNavigate();
  const { token } = useAuth();

  const validateForm = () => {
    const newErrors = {};

    if (!title.trim()) newErrors.title = "Title is required";
    else if (title.length > 200) newErrors.title = "Max 200 characters allowed";

    if (!content.trim()) newErrors.content = "Content is required";
    else if (content.length < 10) newErrors.content = "Min 10 characters required";

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    setIsSubmitting(true);

    try {
      const payload = {
        title: title.trim(),
        content: content.trim(),
        ...(tags.trim() && { tags: tags.trim() })
      };

      const res = await fetch(`${API_BASE_URL}/api/posts`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });

      const data = await res.json();

      if (res.ok) {
        toast.success("Post published successfully!");
        navigate(`/posts/${data.post_id}`);
      } else {
        if (res.status === 409) {
          setErrors({ title: "A post with this title already exists." });
        } else {
          toast.error(data.error || "Something went wrong.");
        }
      }
    } catch (error) {
      console.error("Submit error:", error);
      toast.error("Failed to submit post. Check your network.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-6 bg-white shadow-md rounded-lg mt-8">
      <h2 className="text-2xl font-bold mb-6">Create New Post</h2>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Title */}
        <div>
          <label htmlFor="title" className="block text-sm font-medium mb-1">
            Title *
          </label>
          <input
            type="text"
            id="title"
            maxLength={200}
            value={title}
            onChange={(e) => {
              setTitle(e.target.value);
              if (errors.title) setErrors((prev) => ({ ...prev, title: "" }));
            }}
            disabled={isSubmitting}
            required
            className={`w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 ${
              errors.title ? "border-red-500 focus:ring-red-500" : "border-gray-300 focus:ring-indigo-500"
            }`}
            placeholder="e.g. Why React is Great"
          />
          <div className="flex justify-between mt-1 text-sm text-gray-500">
            {errors.title && <span className="text-red-600">{errors.title}</span>}
            <span>{title.length}/200</span>
          </div>
        </div>

        {/* Content */}
        <div>
          <label htmlFor="content" className="block text-sm font-medium mb-1">
            Content *
          </label>
          <textarea
            id="content"
            rows="8"
            value={content}
            onChange={(e) => {
              setContent(e.target.value);
              if (errors.content) setErrors((prev) => ({ ...prev, content: "" }));
            }}
            disabled={isSubmitting}
            required
            className={`w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 resize-y ${
              errors.content ? "border-red-500 focus:ring-red-500" : "border-gray-300 focus:ring-indigo-500"
            }`}
            placeholder="Write your thoughts here..."
          />
          <div className="flex justify-between mt-1 text-sm text-gray-500">
            {errors.content && <span className="text-red-600">{errors.content}</span>}
            <span>{content.length} characters</span>
          </div>
        </div>

        {/* Tags */}
        <div>
          <label htmlFor="tags" className="block text-sm font-medium mb-1">
            Tags (optional)
          </label>
          <input
            type="text"
            id="tags"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            disabled={isSubmitting}
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="e.g. react, webdev, tailwind"
          />
          <p className="text-sm text-gray-400 mt-1">Separate tags with commas</p>
        </div>

        {/* Buttons */}
        <div className="flex items-center gap-4">
          <button
            type="submit"
            disabled={isSubmitting}
            className="bg-indigo-600 text-white px-6 py-2 rounded-md hover:bg-indigo-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {isSubmitting ? "Publishing..." : "Publish"}
          </button>
          <button
            type="button"
            onClick={() => navigate("/")}
            disabled={isSubmitting}
            className="text-gray-700 px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-100"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
};

export default AddPost;
