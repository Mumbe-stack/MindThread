import { Link } from "react-router-dom";
import LikeButton from "./LikeButton";

const PostCard = ({ 
  post, 
  showAuthorControls = false, 
  showAdminControls = false, 
  onApprove, 
  onFlag, 
  onDelete,
  onVote 
}) => {
  const formatDate = (dateString) => {
    try {
      return new Date(dateString).toLocaleDateString();
    } catch {
      return "Unknown date";
    }
  };

  const getAuthorName = () => {
    return post.author?.username || post.username || "Unknown";
  };

  const getAuthorAvatar = () => {
    return post.author?.avatar_url || null;
  };

  const handleVote = (value) => {
    if (onVote) {
      onVote(post.id, value);
    }
  };

  const VoteButtons = () => (
    <div className="flex flex-col items-center space-y-1 mr-3">
      {/* Upvote */}
      <button
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          handleVote(1);
        }}
        className={`p-1.5 rounded transition-colors ${
          post.userVote === 1
            ? "bg-green-100 text-green-700 border border-green-300"
            : "bg-gray-100 text-gray-600 hover:bg-green-50 hover:text-green-600"
        } cursor-pointer`}
        title="Upvote"
      >
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M3.293 9.707a1 1 0 010-1.414l6-6a1 1 0 011.414 0l6 6a1 1 0 01-1.414 1.414L11 5.414V17a1 1 0 11-2 0V5.414L4.707 9.707a1 1 0 01-1.414 0z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {/* Score */}
      <div className="text-center">
        <span
          className={`font-bold text-sm ${
            post.vote_score > 0
              ? "text-green-600"
              : post.vote_score < 0
              ? "text-red-600"
              : "text-gray-600"
          }`}
        >
          {post.vote_score || 0}
        </span>
        <div className="text-xs text-gray-500">
          {post.upvotes || 0}↑ {post.downvotes || 0}↓
        </div>
      </div>

      {/* Downvote */}
      <button
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          handleVote(-1);
        }}
        className={`p-1.5 rounded transition-colors ${
          post.userVote === -1
            ? "bg-red-100 text-red-700 border border-red-300"
            : "bg-gray-100 text-gray-600 hover:bg-red-50 hover:text-red-600"
        } cursor-pointer`}
        title="Downvote"
      >
        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path
            fillRule="evenodd"
            d="M16.707 10.293a1 1 0 010 1.414l-6 6a1 1 0 01-1.414 0l-6-6a1 1 0 111.414-1.414L9 14.586V3a1 1 0 012 0v11.586l4.293-4.293a1 1 0 011.414 0z"
            clipRule="evenodd"
          />
        </svg>
      </button>
    </div>
  );

  return (
    <div className={`border rounded-lg shadow hover:shadow-lg transition-shadow bg-white ${
      !post.is_approved ? "border-orange-300 bg-orange-50" : ""
    } ${post.is_flagged ? "border-red-300 bg-red-50" : ""}`}>
      
      <div className="p-4 flex space-x-3">
        {/* Vote Buttons */}
        {onVote && <VoteButtons />}
        
        <div className="flex-1">
          {/* Post Header */}
          <div className="flex items-start justify-between mb-3">
            <Link to={`/posts/${post.id}`} className="flex-1">
              <h2 className="text-xl font-semibold text-indigo-700 hover:text-indigo-600 transition-colors mb-2">
                {post.title}
                {!post.is_approved && (
                  <span className="ml-2 text-xs text-orange-700 font-semibold bg-orange-100 px-2 py-0.5 rounded-full">
                    ⏳ Pending
                  </span>
                )}
                {post.is_flagged && (
                  <span className="ml-2 text-xs text-red-700 font-semibold bg-red-100 px-2 py-0.5 rounded-full">
                    🚩 Flagged
                  </span>
                )}
              </h2>
            </Link>
          </div>

          {/* Post Content */}
          <Link to={`/posts/${post.id}`}>
            <p className="text-gray-700 mb-4 line-clamp-3">
              {post.content?.length > 150
                ? `${post.content.slice(0, 150)}...`
                : post.content || "No content"}
            </p>
          </Link>

          {/* Author Info */}
          <div className="flex items-center mb-4">
            {getAuthorAvatar() && (
              <img 
                src={getAuthorAvatar()} 
                alt={`${getAuthorName()}'s avatar`}
                className="w-6 h-6 rounded-full mr-2"
                onError={(e) => {
                  e.target.style.display = 'none';
                }}
              />
            )}
            <div className="text-sm text-gray-500">
              <span className="font-medium text-gray-700">
                By {getAuthorName()}
              </span>
              <span className="mx-2">•</span>
              <span>{formatDate(post.created_at)}</span>
            </div>
          </div>

          {/* Post Stats */}
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4 text-sm text-gray-500">
              {/* Vote Score */}
              {post.vote_score !== undefined && (
                <span className={`font-medium ${
                  post.vote_score > 0 ? "text-green-600" : 
                  post.vote_score < 0 ? "text-red-600" : "text-gray-600"
                }`}>
                  {post.vote_score > 0 ? "+" : ""}{post.vote_score} {Math.abs(post.vote_score) === 1 ? "vote" : "votes"}
                </span>
              )}

              {/* Likes Count */}
              {(post.likes_count > 0 || post.likes > 0) && (
                <span className="text-pink-600 font-medium">
                  {post.likes_count || post.likes} {(post.likes_count || post.likes) === 1 ? "like" : "likes"}
                </span>
              )}

              {/* Comments Count */}
              {post.comments_count > 0 && (
                <span className="text-blue-600 font-medium">
                  {post.comments_count} {post.comments_count === 1 ? "comment" : "comments"}
                </span>
              )}
            </div>

            {/* Action Buttons */}
            <div className="flex items-center space-x-2">
              {/* Like Button */}
              <LikeButton 
                type="post" 
                id={post.id} 
                initialLiked={post.liked_by_user || false}
                initialCount={post.likes_count || post.likes || 0}
              />

              {/* Author Controls */}
              {showAuthorControls && (
                <div className="flex items-center space-x-2">
                  <Link
                    to={`/posts/${post.id}/edit`}
                    className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded hover:bg-blue-200 transition-colors"
                  >
                    Edit
                  </Link>
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      if (onDelete && window.confirm("Delete this post? This action cannot be undone.")) {
                        onDelete(post.id);
                      }
                    }}
                    className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded hover:bg-red-200 transition-colors"
                  >
                    Delete
                  </button>
                </div>
              )}

              {/* Admin Controls */}
              {showAdminControls && (
                <div className="flex items-center space-x-2">
                  {!post.is_approved ? (
                    <>
                      <button
                        onClick={(e) => {
                          e.preventDefault();
                          if (onApprove) onApprove(post.id, true);
                        }}
                        className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded hover:bg-green-200 transition-colors"
                      >
                        ✓ Approve
                      </button>
                      <button
                        onClick={(e) => {
                          e.preventDefault();
                          if (onApprove && window.confirm("Reject this post?")) {
                            onApprove(post.id, false);
                          }
                        }}
                        className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded hover:bg-red-200 transition-colors"
                      >
                        ✗ Reject
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        if (onApprove && window.confirm("Remove approval from this post?")) {
                          onApprove(post.id, false);
                        }
                      }}
                      className="text-xs bg-orange-100 text-orange-700 px-2 py-1 rounded hover:bg-orange-200 transition-colors"
                    >
                      Unapprove
                    </button>
                  )}
                  
                  <button
                    onClick={(e) => {
                      e.preventDefault();
                      if (onFlag) {
                        const action = post.is_flagged ? "Unflag" : "Flag";
                        if (window.confirm(`${action} this post?`)) {
                          onFlag(post.id, !post.is_flagged);
                        }
                      }
                    }}
                    className={`text-xs px-2 py-1 rounded transition-colors ${
                      post.is_flagged
                        ? "bg-yellow-100 text-yellow-700 hover:bg-yellow-200"
                        : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                    }`}
                  >
                    {post.is_flagged ? "🚩 Unflag" : "🚩 Flag"}
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Tags */}
          {post.tags && (
            <div className="mt-3 pt-3 border-t border-gray-100">
              <div className="flex flex-wrap gap-1">
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
        </div>
      </div>
    </div>
  );
};

export default PostCard;