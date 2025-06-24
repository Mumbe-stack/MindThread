import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import toast from "react-hot-toast";

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
    
    if (!title.trim()) {
      newErrors.title = "Title is required";
    } else if (title.length > 200) {
      newErrors.title = "Title must be less than 200 characters";
    }
    
    if (!content.trim()) {
      newErrors.content = "Content is required";
    } else if (content.length < 10) {
      newErrors.content = "Content must be at least 10 characters";
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }
    
    setIsSubmitting(true);

    try {
      const postData = {
        title: title.trim(),
        content: content.trim(),
      };
      
      
      if (tags.trim()) {
        postData.tags = tags.trim();
      }

      const res = await fetch("/api/posts", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}` 
        },
        body: JSON.stringify(postData)
      });

      const data = await res.json();

      if (res.ok) {
        toast.success("Post created successfully!");
        navigate(`/posts/${data.post_id}`);
      } else {
      
        if (res.status === 409) {
          setErrors({ title: "You already have a post with this title" });
        } else {
          toast.error(data.error || "Failed to create post");
        }
      }
    } catch (error) {
      console.error("Error creating post:", error);
      toast.error("Network error. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleTitleChange = (e) => {
    setTitle(e.target.value);
    if (errors.title) {
      setErrors(prev => ({ ...prev, title: "" }));
    }
  };

  const handleContentChange = (e) => {
    setContent(e.target.value);
    if (errors.content) {
      setErrors(prev => ({ ...prev, content: "" }));
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-6 bg-white shadow rounded mt-10">
      <h2 className="text-2xl font-bold mb-6">Create a New Post</h2>
      
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Title Input */}
        <div>
          <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-2">
            Title *
          </label>
          <input
            id="title"
            type="text"
            placeholder="Enter your post title..."
            className={`w-full p-3 border rounded-lg ${errors.title ? 'border-red-500' : 'border-gray-300'} focus:ring-2 focus:ring-indigo-500 focus:border-transparent`}
            value={title}
            onChange={handleTitleChange}
            disabled={isSubmitting}
            maxLength={200}
            required
          />
          <div className="flex justify-between items-center mt-1">
            {errors.title && (
              <p className="text-red-500 text-sm">{errors.title}</p>
            )}
            <p className="text-sm text-gray-500 ml-auto">
              {title.length}/200 characters
            </p>
          </div>
        </div>

        {/* Content Input */}
        <div>
          <label htmlFor="content" className="block text-sm font-medium text-gray-700 mb-2">
            Content *
          </label>
          <textarea
            id="content"
            placeholder="Write your post content here..."
            className={`w-full p-3 border rounded-lg h-48 resize-vertical ${errors.content ? 'border-red-500' : 'border-gray-300'} focus:ring-2 focus:ring-indigo-500 focus:border-transparent`}
            value={content}
            onChange={handleContentChange}
            disabled={isSubmitting}
            required
          />
          {errors.content && (
            <p className="text-red-500 text-sm mt-1">{errors.content}</p>
          )}
          <p className="text-sm text-gray-500 mt-1">
            {content.length} characters
          </p>
        </div>

        {/* Tags Input */}
        <div>
          <label htmlFor="tags" className="block text-sm font-medium text-gray-700 mb-2">
            Tags (optional)
          </label>
          <input
            id="tags"
            type="text"
            placeholder="e.g. technology, programming, tutorial"
            className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            disabled={isSubmitting}
          />
          <p className="text-sm text-gray-500 mt-1">
            Separate multiple tags with commas
          </p>
        </div>

        {/* Submit Button */}
        <div className="flex gap-4">
          <button
            type="submit"
            disabled={isSubmitting || !title.trim() || !content.trim()}
            className="flex-1 bg-indigo-600 text-white py-3 px-6 rounded-lg hover:bg-indigo-700 disabled:bg-gray-400 disabled:cursor-not-allowed font-medium"
          >
            {isSubmitting ? (
              <span className="flex items-center justify-center">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Publishing...
              </span>
            ) : (
              "Publish Post"
            )}
          </button>
          
          <button
            type="button"
            onClick={() => navigate("/")}
            disabled={isSubmitting}
            className="px-6 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
          >
            Cancel
          </button>
        </div>
      </form>

      {/* Help Text */}
      <div className="mt-6 p-4 bg-blue-50 rounded-lg">
        <h3 className="text-sm font-medium text-blue-800 mb-2">💡 Writing Tips</h3>
        <ul className="text-sm text-blue-700 space-y-1">
          <li>• Write a clear, descriptive title</li>
          <li>• Make your content engaging and well-structured</li>
          <li>• Use tags to help others discover your post</li>
          <li>• Preview your post before publishing</li>
        </ul>
      </div>
    </div>
  );
};

export default AddPost;