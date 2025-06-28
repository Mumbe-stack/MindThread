import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { usePosts } from "../context/PostContext";
import toast from "react-hot-toast";

const LikeButton = ({ 
  post, 
  size = "sm", 
  showCount = true, 
  className = "",
  onLikeChange = null 
}) => {
  const { user, token } = useAuth();
  const { likePost } = usePosts();
  const [isLiking, setIsLiking] = useState(false);

  // FIXED: Ensure consistent data access for likes
  const likesCount = post?.likes_count || post?.likes || 0;
  const likedByUser = post?.liked_by_user || false;

  const handleLike = async () => {
    if (!user) {
      toast.error("Please log in to like posts");
      return;
    }

    if (isLiking) return;

    setIsLiking(true);
    try {
      const result = await likePost(post.id, token);
      if (result.success && onLikeChange) {
        onLikeChange(result.data);
      }
    } catch (error) {
      toast.error("Failed to toggle like");
    } finally {
      setIsLiking(false);
    }
  };

  // Size configurations
  const sizeConfig = {
    xs: {
      button: "px-1 py-0.5 text-xs",
      icon: "text-xs",
      text: "text-xs"
    },
    sm: {
      button: "px-2 py-1 text-sm",
      icon: "text-sm",
      text: "text-sm"
    },
    md: {
      button: "px-3 py-1.5 text-base",
      icon: "text-base",
      text: "text-base"
    },
    lg: {
      button: "px-4 py-2 text-lg",
      icon: "text-lg",
      text: "text-lg"
    }
  };

  const config = sizeConfig[size] || sizeConfig.sm;

  return (
    <button
      onClick={handleLike}
      disabled={isLiking || !user}
      className={`${config.button} rounded-full transition-colors disabled:opacity-50 flex items-center gap-1 ${
        likedByUser
          ? "bg-pink-100 text-pink-700 hover:bg-pink-200"
          : "bg-gray-100 text-gray-600 hover:bg-gray-200"
      } ${className}`}
      title={user ? (likedByUser ? "Unlike" : "Like") : "Please log in to like"}
    >
      {isLiking ? (
        <span className={`${config.icon} animate-pulse`}>⏳</span>
      ) : (
        <span className={config.icon}>
          {likedByUser ? "❤️" : "🤍"}
        </span>
      )}
      
      {showCount && (
        <span className={config.text}>
          {likesCount}
        </span>
      )}
    </button>
  );
};

export default LikeButton;