import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import CommentBox from "../components/CommentBox";
import toast from "react-hot-toast"; 

const SinglePost = () => {
  const { id } = useParams();
  const [post, setPost] = useState(null);
  const [comments, setComments] = useState([]);

  useEffect(() => {
    fetch(`/api/posts/${id}`)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch post");
        return res.json();
      })
      .then(setPost)
      .catch(() => toast.error("Failed to load post"));

    fetch(`/api/comments?post_id=${id}`)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch comments");
        return res.json();
      })
      .then(setComments)
      .catch(() => toast.error("Failed to load comments"));
  }, [id]);

  const refreshComments = () => {
    fetch(`/api/comments?post_id=${id}`)
      .then((res) => res.json())
      .then(setComments)
      .catch(() => toast.error("Failed to refresh comments"));
  };

  if (!post) return <p className="text-center p-4">Loading post...</p>;

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold text-indigo-800 mb-2">{post.title}</h1>
      <p className="text-gray-700 mb-6">{post.content}</p>

      <hr className="my-6" />

      <h2 className="text-xl font-semibold mb-4">Comments</h2>
      <CommentBox postId={post.id} onCommentSubmit={refreshComments} />

      <div className="mt-4 space-y-3">
        {comments.length === 0 ? (
          <p className="text-gray-500">No comments yet.</p>
        ) : (
          comments.map((c) => (
            <div key={c.id} className="border p-3 rounded bg-gray-50">
              <p className="text-gray-800">{c.content}</p>
              <p className="text-xs text-gray-500 mt-1">By User #{c.user_id}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default SinglePost;
