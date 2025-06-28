import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import toast from "react-hot-toast";
import LikeButton from "./LikeButton";

const VITE_API_URL = import.meta.env.VITE_API_URL || "https://mindthread-1.onrender.com";

const CommentBox = ({ postId, onCommentSubmit, comments = [] }) => {
  const { user, token } = useAuth();
  const [content, setContent] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [processingComments, setProcessingComments] = useState(new Set());

  const handleSubmit = async () => {
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
        
        // Show appropriate success message
        if (data.is_approved) {
          toast.success("Comment posted and approved");
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

  const handleApproveComment = async (commentId, isApproved) => {
    if (!user?.is_admin || !token) {
      toast.error("Admin access required");
      return;
    }

    // Prevent multiple simultaneous operations on the same comment
    if (processingComments.has(commentId)) {
      return;
    }

    setProcessingComments(prev => new Set(prev).add(commentId));

    try {
      const res = await fetch(`${VITE_API_URL}/api/admin/comments/${commentId}/approve`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        credentials: "include",
        body: JSON.stringify({ is_approved: isApproved }),
      });

      const data = await res.json();

      if (res.ok) {
        toast.success(data.message || (isApproved ? "Comment approved" : "Comment disapproved"));
        // Refresh comments to show updated status
        if (onCommentSubmit) {
          onCommentSubmit();
        }
      } else {
        if (res.status === 400 && data.error?.includes("no changes detected")) {
          toast.error("Cannot approve unchanged comment");
        } else {
          toast.error(data.error || "Failed to update comment approval");
        }
      }
    } catch (err) {
      console.error("Approval error:", err);
      toast.error("Network error while updating comment approval");
    } finally {
      setProcessingComments(prev => {
        const newSet = new Set(prev);
        newSet.delete(commentId);
        return newSet;
      });
    }
  };

  const handleFlagComment = async (commentId, isFlagged) => {
    if (!user?.is_admin || !token) {
      toast.error("Admin access required");
      return;
    }

    if (processingComments.has(commentId)) {
      return;
    }

    setProcessingComments(prev => new Set(prev).add(commentId));

    try {
      const res = await fetch(`${VITE_API_URL}/api/admin/comments/${commentId}/flag`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        credentials: "include",
        body: JSON.stringify({ is_flagged: isFlagged }),
      });

      const data = await res.json();

      if (res.ok) {
        toast.success(data.message || (isFlagged ? "Comment flagged" : "Comment unflagged"));
        // Refresh comments to show updated status
        if (onCommentSubmit) {
          onCommentSubmit();
        }
      } else {
        toast.error(data.error || "Failed to update comment flag");
      }
    } catch (err) {
      console.error("Flag error:", err);
      toast.error("Network error while updating comment flag");
    } finally {
      setProcessingComments(prev => {
        const newSet = new Set(prev);
        newSet.delete(commentId);
        return newSet;
      });
    }
  };

  const formatDate = (dateString) => {
    try {
      return new Date(dateString).toLocaleString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return "Unknown date";
    }
  };

  const getApprovalStatusBadge = (comment) => {
    // Priority order: Flagged > Pending > Needs Re-approval > Approved
    if (comment.is_flagged) {
      return (
        <span className="inline-flex items-center text-xs bg-red-100 text-red-700 px-2 py-1 rounded-full border border-red-200 font-medium">
          <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M3 6a3 3 0 013-3h10a1 1 0 01.8 1.6L14.25 8l2.55 3.4A1 1 0 0116 13H6a1 1 0 00-1 1v3a1 1 0 11-2 0V6z" clipRule="evenodd" />
          </svg>
          Flagged
        </span>
      );
    }

    if (!comment.is_approved) {
      return (
        <span className="inline-flex items-center text-xs bg-orange-100 text-orange-700 px-2 py-1 rounded-full border border-orange-200 font-medium">
          <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
          </svg>
          Pending Approval
        </span>
      );
    }

    if (comment.requires_reapproval || comment.has_content_changed) {
      return (
        <span className="inline-flex items-center text-xs bg-yellow-100 text-yellow-700 px-2 py-1 rounded-full border border-yellow-200 font-medium">
          <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          Needs Re-approval
        </span>
      );
    }

    if (comment.approved_at) {
      return (
        <span className="inline-flex items-center text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full border border-green-200 font-medium">
          <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
          Approved
        </span>
      );
    }

    return null;
  };

  const getCommentBorderClass = (comment) => {
    if (comment.is_flagged) {
      return "border-l-4 border-red-400 bg-red-50/30";
    }
    if (!comment.is_approved) {
      return "border-l-4 border-orange-400 bg-orange-50/30";
    }
    if (comment.requires_reapproval || comment.has_content_changed) {
      return "border-l-4 border-yellow-400 bg-yellow-50/30";
    }
    return "";
  };

  if (!user) {
    return (
      <div className="bg-gray-50 rounded-xl p-6 text-center border border-gray-200">
        <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg className="w-8 h-8 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2">Join the Conversation</h3>
        <p className="text-gray-600 mb-4">
          Please log in to post a comment and engage with the community
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
      <div className="bg-white rounded-xl shadow-lg border border-gray-200 p-6">
        <div className="flex items-start space-x-4">
          {/* User Avatar */}
          <div className="flex-shrink-0">
            {user.avatar_url ? (
              <img 
                src={user.avatar_url} 
                alt={`${user.username}'s avatar`}
                className="w-10 h-10 rounded-full ring-2 ring-gray-200"
                onError={(e) => {
                  e.target.style.display = 'none';
                }}
              />
            ) : (
              <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-full flex items-center justify-center ring-2 ring-gray-200">
                <span className="text-white font-bold text-sm">
                  {user.username?.[0]?.toUpperCase() || 'U'}
                </span>
              </div>
            )}
          </div>

          {/* Comment Input */}
          <div className="flex-1">
            <div className="mb-3">
              <div className="flex items-center space-x-2">
                <span className="text-sm font-semibold text-gray-800">
                  Commenting as {user.username}
                </span>
                {user.is_admin && (
                  <span className="inline-flex items-center text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded-full border border-purple-200 font-medium">
                    <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z" clipRule="evenodd" />
                    </svg>
                    Admin
                  </span>
                )}
              </div>
            </div>
            
            <textarea
              placeholder="Write a comment... (Ctrl+Enter to submit)"
              className="w-full border border-gray-300 rounded-lg p-4 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 resize-none transition-colors"
              rows="4"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && e.ctrlKey && !isSubmitting && content.trim()) {
                  handleSubmit();
                }
              }}
              disabled={isSubmitting}
              maxLength={1000}
            />
            
            <div className="flex items-center justify-between mt-4">
              <div className="flex flex-col space-y-1">
                <div className="text-xs text-gray-500">
                  <span className={content.length > 900 ? "text-red-600 font-medium" : ""}>
                    {content.length}/1000 characters
                  </span>
                </div>
                <div className="text-xs">
                  {!user.is_admin ? (
                    <span className="text-orange-600 font-medium">
                      • Comments require admin approval before being visible to others
                    </span>
                  ) : (
                    <span className="text-green-600 font-medium">
                      • Your comments are automatically approved
                    </span>
                  )}
                </div>
              </div>
              
              <button
                onClick={handleSubmit}
                disabled={isSubmitting || !content.trim()}
                className="inline-flex items-center bg-gradient-to-r from-indigo-600 to-purple-600 text-white px-6 py-2 rounded-lg hover:from-indigo-700 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 transform hover:scale-105 shadow-lg"
              >
                {isSubmitting ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    <span>Posting...</span>
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                    </svg>
                    Post Comment
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Comments List */}
      {comments.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-bold text-gray-900 flex items-center">
              <svg className="w-5 h-5 mr-2 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
              Comments ({comments.length})
            </h3>
            
            {user?.is_admin && (
              <div className="text-xs text-gray-500">
                Admin View: All comments visible
              </div>
            )}
          </div>
          
          {comments.map((comment) => (
            <div 
              key={comment.id} 
              className={`bg-white rounded-xl shadow-lg border transition-all duration-200 hover:shadow-xl ${getCommentBorderClass(comment)}`}
            >
              <div className="p-6">
                <div className="flex items-start space-x-4">
                  {/* Commenter Avatar */}
                  <div className="flex-shrink-0">
                    {comment.author?.avatar_url ? (
                      <img 
                        src={comment.author.avatar_url} 
                        alt={`${comment.author.username}'s avatar`}
                        className="w-10 h-10 rounded-full ring-2 ring-gray-200"
                        onError={(e) => {
                          e.target.style.display = 'none';
                        }}
                      />
                    ) : (
                      <div className="w-10 h-10 bg-gradient-to-br from-gray-400 to-gray-600 rounded-full flex items-center justify-center ring-2 ring-gray-200">
                        <span className="text-white font-bold text-sm">
                          {comment.author?.username?.[0]?.toUpperCase() || 'U'}
                        </span>
                      </div>
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    {/* Comment Header */}
                    <div className="flex items-center flex-wrap gap-3 mb-3">
                      <div className="flex items-center space-x-2">
                        <span className="font-semibold text-gray-900">
                          {comment.author?.username || comment.username || "Unknown"}
                        </span>
                        <span className="text-sm text-gray-500">
                          {formatDate(comment.created_at)}
                        </span>
                      </div>
                      
                      {/* Status Badge */}
                      {getApprovalStatusBadge(comment)}

                      {/* Updated Indicator */}
                      {comment.updated_at && comment.updated_at !== comment.created_at && (
                        <span className="text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded border border-amber-200">
                          Edited {formatDate(comment.updated_at)}
                        </span>
                      )}

                      {/* Admin Info */}
                      {user?.is_admin && comment.approved_at && comment.approved_by && (
                        <span className="text-xs text-green-600">
                          Approved {formatDate(comment.approved_at)}
                          {comment.approved_by.username && ` by ${comment.approved_by.username}`}
                        </span>
                      )}
                    </div>

                    {/* Comment Content */}
                    <div className="mb-4">
                      <p className="text-gray-800 leading-relaxed whitespace-pre-wrap">
                        {comment.content}
                      </p>
                    </div>

                    {/* Comment Actions */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-6">
                        {/* Like Button */}
                        <LikeButton 
                          type="comment" 
                          id={comment.id}
                          initialLikes={comment.likes_count || 0}
                          initialLiked={comment.liked_by_user || false}
                          size="small"
                          variant="minimal"
                        />
                        
                        {/* Reply Count */}
                        {comment.replies_count > 0 && (
                          <div className="flex items-center space-x-1 text-sm text-gray-500">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                            </svg>
                            <span>{comment.replies_count} {comment.replies_count === 1 ? 'reply' : 'replies'}</span>
                          </div>
                        )}
                      </div>

                      {/* Admin Controls */}
                      {user?.is_admin && (
                        <div className="flex items-center space-x-2">
                          {!comment.is_approved ? (
                            <button
                              onClick={() => handleApproveComment(comment.id, true)}
                              disabled={processingComments.has(comment.id)}
                              className="inline-flex items-center text-xs bg-green-600 text-white px-3 py-1.5 rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
                            >
                              {processingComments.has(comment.id) ? (
                                <div className="animate-spin rounded-full h-3 w-3 border-b border-white mr-1"></div>
                              ) : (
                                <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                              )}
                              Approve
                            </button>
                          ) : (
                            <button
                              onClick={() => handleApproveComment(comment.id, false)}
                              disabled={processingComments.has(comment.id)}
                              className="inline-flex items-center text-xs bg-orange-600 text-white px-3 py-1.5 rounded-lg hover:bg-orange-700 disabled:opacity-50 transition-colors"
                            >
                              {processingComments.has(comment.id) ? (
                                <div className="animate-spin rounded-full h-3 w-3 border-b border-white mr-1"></div>
                              ) : (
                                <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728L5.636 5.636m12.728 12.728L18.364 5.636M5.636 18.364l12.728-12.728" />
                                </svg>
                              )}
                              Disapprove
                            </button>
                          )}
                          
                          <button
                            onClick={() => handleFlagComment(comment.id, !comment.is_flagged)}
                            disabled={processingComments.has(comment.id)}
                            className={`inline-flex items-center text-xs px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50 ${
                              comment.is_flagged 
                                ? "bg-gray-600 text-white hover:bg-gray-700" 
                                : "bg-red-600 text-white hover:bg-red-700"
                            }`}
                          >
                            {processingComments.has(comment.id) ? (
                              <div className="animate-spin rounded-full h-3 w-3 border-b border-white mr-1"></div>
                            ) : (
                              <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M3 6a3 3 0 013-3h10a1 1 0 01.8 1.6L14.25 8l2.55 3.4A1 1 0 0116 13H6a1 1 0 00-1 1v3a1 1 0 11-2 0V6z" clipRule="evenodd" />
                              </svg>
                            )}
                            {comment.is_flagged ? "Unflag" : "Flag"}
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      
      {/* Empty State */}
      {comments.length === 0 && (
        <div className="text-center py-12 bg-gray-50 rounded-xl border-2 border-dashed border-gray-300">
          <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No comments yet</h3>
          <p className="text-gray-600 mb-4">Be the first to share your thoughts on this post!</p>
          {!user.is_admin && (
            <p className="text-sm text-orange-600 font-medium">
              Remember: Comments require admin approval before being visible to others
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export default CommentBox;