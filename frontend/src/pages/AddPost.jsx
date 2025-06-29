import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import toast from "react-hot-toast";

const VITE_API_URL = import.meta.env.VITE_API_URL || "https://mindthread-1.onrender.com";

const AddPost = () => {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [tags, setTags] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState({});

  const navigate = useNavigate();
  const { user, token } = useAuth();


  if (!user) {
    navigate("/login");
    return null;
  }

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

    if (!token) {
      toast.error("Please login to create a post");
      navigate("/login");
      return;
    }

    setIsSubmitting(true);

    try {
      const payload = {
        title: title.trim(),
        content: content.trim(),
        ...(tags.trim() && { tags: tags.trim() })
      };

      const res = await fetch(`${VITE_API_URL}/api/posts`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        credentials: "include",
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errorData = await res.json();
        if (res.status === 409) {
          setErrors({ title: "A post with this title already exists." });
          toast.error("A post with this title already exists");
        } else if (res.status === 401) {
          toast.error("Please login to create a post");
          navigate("/login");
        } else {
          toast.error(errorData.error || "Failed to create post");
        }
        return;
      }

      const data = await res.json();
      
      toast.success("Post published successfully!");
      
     
      if (data.post_id || data.id) {
        navigate(`/posts/${data.post_id || data.id}`);
      } else {
        navigate("/");
      }
      
    } catch (error) {
      console.error("Error creating post:", error);
      toast.error("Failed to submit post. Check your network connection.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = () => {
    if (title.trim() || content.trim()) {
      const confirmed = window.confirm("You have unsaved changes. Are you sure you want to leave?");
      if (!confirmed) return;
    }
    navigate("/");
  };

  return (
    <div className="max-w-2xl mx-auto p-6 bg-white shadow-md rounded-lg mt-8">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold">Create New Post</h2>
        <div className="text-sm text-gray-500">
          Logged in as: <span className="font-medium">{user?.username || `User #${user?.id}`}</span>
        </div>
      </div>

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
            className={`w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 transition-colors ${
              errors.title 
                ? "border-red-500 focus:ring-red-500" 
                : "border-gray-300 focus:ring-indigo-500"
            }`}
            placeholder="e.g. Why React is Great"
          />
          <div className="flex justify-between mt-1 text-sm">
            <span className={errors.title ? "text-red-600" : "text-transparent"}>
              {errors.title || " "}
            </span>
            <span className={`${title.length > 180 ? "text-orange-500" : "text-gray-500"}`}>
              {title.length}/200
            </span>
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
            className={`w-full px-4 py-2 border rounded-md focus:outline-none focus:ring-2 resize-y transition-colors ${
              errors.content 
                ? "border-red-500 focus:ring-red-500" 
                : "border-gray-300 focus:ring-indigo-500"
            }`}
            placeholder="Write your thoughts here... Share something interesting!"
          />
          <div className="flex justify-between mt-1 text-sm">
            <span className={errors.content ? "text-red-600" : "text-transparent"}>
              {errors.content || " "}
            </span>
            <span className={`${
              content.length < 10 ? "text-red-500" : 
              content.length > 5000 ? "text-orange-500" : 
              "text-gray-500"
            }`}>
              {content.length} characters {content.length < 10 ? "(minimum 10)" : ""}
            </span>
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
            className="w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors"
            placeholder="e.g. react, webdev, tailwind, javascript"
          />
          <p className="text-sm text-gray-400 mt-1">
            Separate tags with commas. Tags help others discover your post!
          </p>
        </div>

        {/* Preview Section */}
        {(title.trim() || content.trim()) && (
          <div className="border border-gray-200 rounded-lg p-4 bg-gray-50">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Preview:</h3>
            {title.trim() && (
              <h4 className="text-lg font-semibold text-gray-800 mb-2">
                {title}
              </h4>
            )}
            {content.trim() && (
              <p className="text-gray-600 whitespace-pre-wrap">
                {content.length > 200 ? `${content.substring(0, 200)}...` : content}
              </p>
            )}
            {tags.trim() && (
              <div className="mt-2 flex flex-wrap gap-1">
                {tags.split(',').map((tag, index) => (
                  <span
                    key={index}
                    className="bg-indigo-100 text-indigo-700 px-2 py-1 rounded text-xs"
                  >
                    {tag.trim()}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Buttons */}
        <div className="flex items-center gap-4 pt-4">
          <button
            type="submit"
            disabled={isSubmitting || !title.trim() || !content.trim()}
            className="bg-indigo-600 text-white px-6 py-2 rounded-md hover:bg-indigo-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
          >
            {isSubmitting ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                <span>Publishing...</span>
              </>
            ) : (
              <span>Publish Post</span>
            )}
          </button>
          
          <button
            type="button"
            onClick={handleCancel}
            disabled={isSubmitting}
            className="text-gray-700 px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-100 disabled:opacity-50 transition-colors"
          >
            Cancel
          </button>

          {/* Draft Save (Future Feature) */}
          <button
            type="button"
            disabled={isSubmitting || (!title.trim() && !content.trim())}
            className="text-indigo-600 px-4 py-2 border border-indigo-300 rounded-md hover:bg-indigo-50 disabled:opacity-50 transition-colors"
            onClick={() => {
             
              localStorage.setItem('post_draft', JSON.stringify({
                title: title.trim(),
                content: content.trim(),
                tags: tags.trim(),
                timestamp: new Date().toISOString()
              }));
              toast.success("Draft saved locally!");
            }}
          >
            Save Draft
          </button>
        </div>

        {/* Help Text */}
        <div className="text-sm text-gray-500 bg-blue-50 border border-blue-200 rounded-lg p-3">
          <h4 className="font-medium text-blue-800 mb-1">Tips for a great post:</h4>
          <ul className="list-disc list-inside space-y-1 text-blue-700">
            <li>Use a clear, descriptive title</li>
            <li>Write engaging content that adds value</li>
            <li>Add relevant tags to help others find your post</li>
            <li>Check your spelling and grammar before publishing</li>
          </ul>
        </div>
      </form>
    </div>
  );
};

export default AddPost;