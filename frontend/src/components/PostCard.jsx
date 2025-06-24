import { Link } from "react-router-dom";

const PostCard = ({ post }) => {
  return (
    <div className="border rounded p-4 bg-white shadow hover:shadow-lg transition">
      <Link to={`/posts/${post.id}`}>
        <h2 className="text-xl font-semibold text-indigo-700 hover:underline">{post.title}</h2>
      </Link>
      <p className="text-gray-700 mt-2">{post.content.slice(0, 100)}...</p>
      <p className="text-sm text-gray-500 mt-2">By User #{post.user_id} • {new Date(post.created_at).toLocaleDateString()}</p>
    </div>
  );
};

export default PostCard;
