import { useState } from "react";
import toast from "react-hot-toast";
import LikeButton from "./LikeButton";
const CommentBox = ({ postId, onCommentSubmit }) => {
  const [content, setContent] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    const token = localStorage.getItem("token");

    const res = await fetch(`${VITE_API_URL}/api/comments`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      },
      body: JSON.stringify({ post_id: postId, content })
    });

    if (res.ok) {
      toast.success("Comment added");
      setContent("");
      onCommentSubmit();
    } else {
      toast.error("Failed to add comment");
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      <textarea
        placeholder="Write a comment..."
        className="w-full border p-2 rounded"
        value={content}
        onChange={(e) => setContent(e.target.value)}
        required
      />
      <button
        type="submit"
        className="bg-indigo-600 text-white px-4 py-1 rounded hover:bg-indigo-700"
      >
        Submit Comment
      </button>
    </form>
  );
};

export default CommentBox;
