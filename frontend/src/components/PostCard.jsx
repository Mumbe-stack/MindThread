import { Link } from "react-router-dom";
import { MessageSquare } from "lucide-react";
import VoteButton from "./VoteButton";
import LikeButton from "./LikeButton";

const PostCard = ({ post }) => {
  const {
    id,
    title,
    content,
    author,
    created_at,
    vote_score,
    user_vote,
    likes_count,
    liked_by_user,
    comments_count,
  } = post;

  const displayDate = new Date(created_at).toLocaleDateString();

  return (
    <div className="border rounded p-4 bg-white shadow hover:shadow-lg transition">
      <Link to={`/posts/${id}`}>
        <h2 className="text-xl font-semibold text-indigo-700 hover:underline">
          {title}
        </h2>
      </Link>

      <p className="text-gray-700 mt-2">
        {content.length > 100 ? `${content.slice(0, 100)}...` : content}
      </p>

      <div className="flex items-center text-sm text-gray-500 mt-2 space-x-2">
        <span>By {author?.username || "Unknown"}</span>
        <span>•</span>
        <span>{displayDate}</span>
      </div>

      <div className="flex items-center space-x-6 mt-4">
        {/* Voting */}
        <div className="flex items-center space-x-1">
          <VoteButton
            type="post"
            id={id}
            currentVote={user_vote}
            className="w-5 h-5"
          />
          <span className="text-gray-700">{vote_score}</span>
        </div>

        {/* Likes */}
        <div className="flex items-center space-x-1">
          <LikeButton
            type="post"
            id={id}
            liked={liked_by_user}
            className="w-5 h-5"
          />
          <span className="text-gray-700">{likes_count}</span>
        </div>

        {/* Comments */}
        <Link
          to={`/posts/${id}#comments`}
          className="flex items-center space-x-1 text-gray-600 hover:text-gray-800"
        >
          <MessageSquare size={16} />
          <span>{comments_count}</span>
        </Link>
      </div>
    </div>
  );
};

export default PostCard;