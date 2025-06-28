import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import toast from "react-hot-toast";
import LikeButton from "./LikeButton";

const VITE_API_URL = import.meta.env.VITE_API_URL || "https://mindthread-1.onrender.com";

const CommentBox = ({ postId, onCommentSubmit, comments = [] }) => {
  const { user, token } = useAuth();
  const [content, setContent] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!user || !token) {
      toast.error("Please log in to comment");
      return;
    }

    if (!content.trim()) {
      toast.error("Comment cannot be empty");
      return;
    }

    setIsSubmitting(true);

    try {
      // Use the correct endpoint for posting comments
      const res = await fetch(`${VITE_API_URL}/api/posts/${postId}/comments`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        credentials: "include",
        body: JSON.stringify({ content: content.trim() })
      });

      if (res.ok) {
        const data = await res.json();
        
        // Check if comment was approved or pending
        if (data.is_approved) {
          toast.success("Comment posted successfully");
        } else {
          toast.success(data.message || "Comment submitted for approval");
        }
        
        setContent("");
        
        // Call parent callback to refresh comments
        if (onCommentSubmit) {
          onCommentSubmit(data);
        }
      } else {
        const errorData = await res.json().catch(() => ({ error: "Failed to add comment" }));
        
        if (res.status === 401) {
          toast.error("Please log in again");
        } else if (res.status === 403) {
          toast.error("Access denied");
        } else if (res.status === 404) {
          toast.error("Post not found");
        } else {
          toast.error(errorData.error || "Failed to add comment");
        }
      }
    } catch (error) {
      console.error("Error submitting comment:", error);
      
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        toast.error("Network error - please check your connection");
      } else {
        toast.error("Network error while posting comment");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const formatDate = (dateString) => {
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return "Unknown date";
    }
  };

  if (!user) {
    return (
      <div className="bg-gray-50 rounded-lg p-6 text-center">
        <p className="text-gray-600 mb-4">
          Please log in to post a comment
        </p>
        <div className="text-sm text-gray-500">
          {comments.length > 0 && (
            <span>{comments.length} comment{comments.length !== 1 ? 's' : ''} below</span>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Comment Form */}
      <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-4">
        <div className="flex items-start space-x-3">
          {/* User Avatar */}
          <div className="flex-shrink-0">
            {user.avatar_url ? (
              <img 
                src={user.avatar_url} 
                alt={`${user.username}'s avatar`}
                className="w-8 h-8 rounded-full"
                onError={(e) => {
                  e.target.style.display = 'none';
                }}
              />
            ) : (
              <div className="w-8 h-8 bg-indigo-100 rounded-full flex items-center justify-center">
                <span className="text-indigo-600 font-medium text-sm">
                  {user.username?.[0]?.toUpperCase() || 'U'}
                </span>
              </div>
            )}
          </div>

          {/* Comment Input */}
          <div className="flex-1">
            <div className="mb-2">
              <span className="text-sm font-medium text-gray-700">
                Commenting as {user.username}
              </span>
            </div>
            
            <textarea
              placeholder="Write a comment..."
              className="w-full border border-gray-300 rounded-lg p-3 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 resize-none"
              rows="3"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              disabled={isSubmitting}
              maxLength={1000}
              required
            />
            
            <div className="flex items-center justify-between mt-3">
              <div className="text-xs text-gray-500">
                {content.length}/1000 characters
                {!user.is_admin && (
                  <span className="ml-2 text-orange-600">
                    • Comments require admin approval
                  </span>
                )}
              </div>
              
              <button
                type="submit"
                disabled={isSubmitting || !content.trim()}
                className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isSubmitting ? (
                  <div className="flex items-center space-x-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    <span>Posting...</span>
                  </div>
                ) : (
                  "Post Comment"
                )}
              </button>
            </div>
          </div>
        </div>
      </form>

      {/* Comments List */}
      {comments.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900">
            Comments ({comments.length})
          </h3>
          
          {comments.map((comment) => (
            <div key={comment.id} className={`bg-white rounded-lg shadow p-4 ${
              !comment.is_approved ? "border-l-4 border-orange-400 bg-orange-50" : ""
            }`}>
              <div className="flex items-start space-x-3">
                {/* Commenter Avatar */}
                <div className="flex-shrink-0">
                  {comment.author?.avatar_url ? (
                    <img 
                      src={comment.author.avatar_url} 
                      alt={`${comment.author.username}'s avatar`}
                      className="w-8 h-8 rounded-full"
                      onError={(e) => {
                        e.target.style.display = 'none';
                      }}
                    />
                  ) : (
                    <div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center">
                      <span className="text-gray-600 font-medium text-sm">
                        {comment.author?.username?.[0]?.toUpperCase() || 'U'}
                      </span>
                    </div>
                  )}
                </div>

                <div className="flex-1">
                  {/* Comment Header */}
                  <div className="flex items-center space-x-2 mb-2">
                    <span className="font-medium text-gray-900">
                      {comment.author?.username || comment.username || "Unknown"}
                    </span>
                    <span className="text-sm text-gray-500">
                      {formatDate(comment.created_at)}
                    </span>
                    {!comment.is_approved && (
                      <span className="text-xs bg-orange-100 text-orange-700 px-2 py-1 rounded">
                        Pending Approval
                      </span>
                    )}
                    {comment.is_flagged && (
                      <span className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded">
                        Flagged
                      </span>
                    )}
                  </div>

                  {/* Comment Content */}
                  <p className="text-gray-800 mb-3 whitespace-pre-wrap">
                    {comment.content}
                  </p>

                  {/* Comment Actions */}
                  <div className="flex items-center space-x-4">
                    <LikeButton 
                      type="comment" 
                      id={comment.id}
                      initialLikes={comment.likes_count || 0}
                      initialLiked={comment.liked_by_user || false}
                      size="small"
                      variant="minimal"
                    />
                    
                    {comment.vote_score !== undefined && (
                      <div className="flex items-center space-x-1 text-sm text-gray-500">
                        <span className={`font-medium ${
                          comment.vote_score > 0 ? "text-green-600" : 
                          comment.vote_score < 0 ? "text-red-600" : "text-gray-600"
                        }`}>
                          {comment.vote_score > 0 ? '+' : ''}{comment.vote_score || 0}
                        </span>
                        <span>votes</span>
                      </div>
                    )}

                    {(comment.upvotes > 0 || comment.downvotes > 0) && (
                      <div className="flex items-center space-x-2 text-xs text-gray-500">
                        {comment.upvotes > 0 && (
                          <span className="text-green-600">
                            {comment.upvotes} ↑
                          </span>
                        )}
                        {comment.downvotes > 0 && (
                          <span className="text-red-600">
                            {comment.downvotes} ↓
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      
      {comments.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <p>No comments yet. Be the first to comment!</p>
        </div>
      )}
    </div>
  );
};

export default CommentBox;