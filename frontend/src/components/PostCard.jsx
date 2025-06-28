import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { usePosts } from "../context/PostContext";
import toast from "react-hot-toast";

const PostCard = ({ post, showActions = true, showFullContent = false }) => {
  const { user, token } = useAuth();
  const { deletePost, likePost } = usePosts();
  const [showMenu, setShowMenu] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isLiking, setIsLiking] = useState(false);

  // FIXED: Ensure consistent data access for likes
  const likesCount = post?.likes_count || post?.likes || 0;
  const likedByUser = post?.liked_by_user || false;
  const author = post?.author || { username: "Unknown", id: null };
  const isOwner = user && post?.author?.id === user.id;
  const isAdmin = user?.is_admin;

  const handleDelete = async () => {
    if (!window.confirm("Are you sure you want to delete this post?")) return;
    
    setIsDeleting(true);
    try {
      const result = await deletePost(post.id, token);
      if (result.success) {
        toast.success("Post deleted successfully");
      }
    } catch (error) {
      toast.error("Failed to delete post");
    } finally {
      setIsDeleting(false);
      setShowMenu(false);
    }
  };

  // FIXED: Handle like action consistently
  const handleLike = async () => {
    if (!user) {
      toast.error("Please log in to like posts");
      return;
    }

    if (isLiking) return;

    setIsLiking(true);
    try {
      await likePost(post.id, token);
    } catch (error) {
      toast.error("Failed to toggle like");
    } finally {
      setIsLiking(false);
    }
  };

  const truncateContent = (content, maxLength = 200) => {
    if (!content) return "";
    if (content.length <= maxLength) return content;
    return content.substring(0, maxLength) + "...";
  };

  const formatDate = (dateString) => {
    if (!dateString) return "Unknown date";
    
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit"
      });
    } catch (error) {
      return "Invalid date";
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md border border-gray-200 p-4 sm:p-6 hover:shadow-lg transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1 min-w-0">
          <Link 
            to={`/posts/${post.id}`}
            className="block group"
          >
            <h2 className="text-lg sm:text-xl font-bold text-gray-900 group-hover:text-indigo-600 transition-colors line-clamp-2">
              {post.title}
            </h2>
          </Link>
          
          {/* FIXED: Display username properly */}
          <div className="flex items-center gap-2 mt-2 text-sm text-gray-500">
            <span className="font-medium text-indigo-600">
              {author.username}
            </span>
            <span>•</span>
            <time dateTime={post.created_at}>
              {formatDate(post.created_at)}
            </time>
            
            {/* Status badges */}
            <div className="flex gap-1 ml-2">
              {post.is_flagged && (
                <span className="px-2 py-1 text-xs bg-red-100 text-red-800 rounded-full">
                  🚩 Flagged
                </span>
              )}
              {!post.is_approved && (
                <span className="px-2 py-1 text-xs bg-yellow-100 text-yellow-800 rounded-full">
                  ⏳ Pending
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Actions Menu */}
        {showActions && user && (isOwner || isAdmin) && (
          <div className="relative ml-4">
            <button
              onClick={() => setShowMenu(!showMenu)}
              className="p-2 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100"
              aria-label="Post options"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
              </svg>
            </button>

            {showMenu && (
              <div className="absolute right-0 top-full mt-1 w-48 bg-white border border-gray-200 rounded-lg shadow-lg z-10">
                {isOwner && (
                  <Link
                    to={`/posts/${post.id}/edit`}
                    className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                    onClick={() => setShowMenu(false)}
                  >
                    ✏️ Edit Post
                  </Link>
                )}
                
                {(isOwner || isAdmin) && (
                  <button
                    onClick={handleDelete}
                    disabled={isDeleting}
                    className="w-full text-left px-4 py-2 text-sm text-red-700 hover:bg-red-50 disabled:opacity-50"
                  >
                    {isDeleting ? "🔄 Deleting..." : "🗑️ Delete Post"}
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Content */}
      <div className="mb-4">
        <p className="text-gray-700 leading-relaxed">
          {showFullContent ? post.content : truncateContent(post.content)}
        </p>
        
        {!showFullContent && post.content && post.content.length > 200 && (
          <Link 
            to={`/posts/${post.id}`}
            className="text-indigo-600 hover:text-indigo-800 text-sm font-medium mt-2 inline-block"
          >
            Read more →
          </Link>
        )}
      </div>

      {/* Tags */}
      {post.tags && (
        <div className="mb-4">
          <div className="flex flex-wrap gap-2">
            {post.tags.split(',').map((tag, index) => (
              <span
                key={index}
                className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded-full"
              >
                #{tag.trim()}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* FIXED: Consistent Like and Vote Display */}
      <div className="border-t border-gray-100 pt-4">
        <div className="flex items-center gap-4 flex-wrap">
          {/* Voting Section */}
          <div className="flex items-center gap-1">
            <span className="text-xs text-gray-500">Vote:</span>
            <span className="text-sm font-medium text-gray-700">
              {post.vote_score || 0}
            </span>
            <span className="text-xs text-gray-400">
              ({post.upvotes || 0}↑ {post.downvotes || 0}↓)
            </span>
          </div>

          {/* Like Section - FIXED */}
          <button
            onClick={handleLike}
            disabled={isLiking || !user}
            className={`flex items-center gap-1 px-3 py-1 rounded-full text-sm transition-colors disabled:opacity-50 ${
              likedByUser
                ? "bg-pink-100 text-pink-700 hover:bg-pink-200"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
            title={likedByUser ? "Unlike" : "Like"}
          >
            <span>{likedByUser ? "❤️" : "🤍"}</span>
            <span>Like ({likesCount})</span>
          </button>

          {/* Comments Count */}
          <div className="flex items-center gap-1 text-sm text-gray-500">
            <span>💬</span>
            <span>{post.comments_count || 0} Comments</span>
          </div>
        </div>
      </div>

      {/* Admin info */}
      {isAdmin && (
        <div className="mt-3 pt-3 border-t border-gray-100">
          <div className="text-xs text-gray-500 flex gap-4">
            <span>ID: {post.id}</span>
            <span>Approved: {post.is_approved ? "✅" : "❌"}</span>
            <span>Flagged: {post.is_flagged ? "🚩" : "✅"}</span>
            <span>Likes: {likesCount}</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default PostCard;