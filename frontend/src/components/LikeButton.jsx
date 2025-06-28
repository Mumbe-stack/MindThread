import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import toast from 'react-hot-toast';

const VITE_API_URL = import.meta.env.VITE_API_URL || "https://mindthread-1.onrender.com";

const LikeButton = ({ 
  itemType = 'post', // 'post' or 'comment'
  itemId, 
  initialLikes = 0, 
  initialLikedBy = [], 
  onLikeChange,
  size = 'normal', // 'small', 'normal', 'large'
  variant = 'default' // 'default', 'minimal', 'outlined'
}) => {
  const { user, token } = useAuth();
  const [likes, setLikes] = useState(initialLikes);
  const [likedBy, setLikedBy] = useState(initialLikedBy);
  const [isLoading, setIsLoading] = useState(false);

  const isLiked = user && likedBy.includes(user.id);

  const handleToggleLike = async () => {
    if (!user || !token) {
      toast.error(`Please log in to like ${itemType}s`);
      return;
    }

    if (isLoading) return; // Prevent double clicks

    setIsLoading(true);

    try {
      const endpoint = itemType === 'post' 
        ? `${VITE_API_URL}/api/posts/${itemId}/like`
        : `${VITE_API_URL}/api/comments/${itemId}/like`;

      console.log(`Attempting to like ${itemType}:`, itemId);

      const res = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        credentials: "include",
      });

      console.log(`${itemType} like response status:`, res.status);

      if (!res.ok) {
        const errorText = await res.text();
        console.error(`${itemType} like error:`, errorText);
        
        let errorData;
        try {
          errorData = JSON.parse(errorText);
        } catch {
          errorData = { error: errorText };
        }
        
        // Handle specific error cases
        if (res.status === 404) {
          toast.error(`${itemType.charAt(0).toUpperCase() + itemType.slice(1)} not found`);
        } else if (res.status === 401) {
          toast.error("Please log in again");
        } else if (res.status === 403) {
          toast.error("Access denied");
        } else {
          toast.error(errorData.error || `Failed to like ${itemType}`);
        }
        return;
      }

      const data = await res.json();
      console.log(`${itemType} like success:`, data);

      // Update local state
      const newLikes = data.likes || 0;
      const newLikedBy = data.liked_by || [];
      
      setLikes(newLikes);
      setLikedBy(newLikedBy);

      // Call parent callback if provided
      if (onLikeChange) {
        onLikeChange({
          itemId,
          itemType,
          likes: newLikes,
          liked_by: newLikedBy,
          isLiked: newLikedBy.includes(user.id)
        });
      }

      // Show success message
      const action = newLikedBy.includes(user.id) ? 'liked' : 'unliked';
      toast.success(`${itemType.charAt(0).toUpperCase() + itemType.slice(1)} ${action}!`);

    } catch (error) {
      console.error(`Error toggling ${itemType} like:`, error);
      toast.error(`Network error while liking ${itemType}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Size variants
  const sizeClasses = {
    small: {
      button: 'px-2 py-1 text-xs',
      icon: 'text-sm',
      text: 'text-xs'
    },
    normal: {
      button: 'px-3 py-1 text-sm',
      icon: 'text-base',
      text: 'text-sm'
    },
    large: {
      button: 'px-4 py-2 text-base',
      icon: 'text-lg',
      text: 'text-base'
    }
  };

  // Style variants
  const getVariantClasses = () => {
    const base = 'inline-flex items-center gap-1 rounded-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed';
    
    if (variant === 'minimal') {
      return `${base} hover:bg-gray-100 ${isLiked ? 'text-red-600' : 'text-gray-600'}`;
    }
    
    if (variant === 'outlined') {
      return `${base} border ${
        isLiked 
          ? 'border-red-300 bg-red-50 text-red-600 hover:bg-red-100' 
          : 'border-gray-300 bg-white text-gray-600 hover:bg-gray-50'
      }`;
    }
    
    // Default variant
    return `${base} ${
      isLiked 
        ? 'bg-red-100 text-red-600 border border-red-300 hover:bg-red-200' 
        : 'bg-gray-100 text-gray-700 border border-gray-300 hover:bg-gray-200'
    }`;
  };

  const currentSize = sizeClasses[size];

  return (
    <div className="flex items-center gap-2">
      {user ? (
        <button
          onClick={handleToggleLike}
          disabled={isLoading}
          className={`${getVariantClasses()} ${currentSize.button}`}
          aria-label={`${isLiked ? 'Unlike' : 'Like'} this ${itemType}`}
        >
          {isLoading ? (
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current"></div>
          ) : (
            <span className={currentSize.icon}>
              {isLiked ? "♥" : "♡"}
            </span>
          )}
          <span className={currentSize.text}>
            {isLiked ? "Unlike" : "Like"}
          </span>
          <span className={`font-semibold ${currentSize.text}`}>
            ({likes})
          </span>
        </button>
      ) : (
        <div className={`flex items-center gap-1 text-gray-500 ${currentSize.text}`}>
          <span className={currentSize.icon}>♡</span>
          <span>({likes})</span>
          {likes > 0 && size !== 'small' && (
            <span className="text-xs">
              • <span className="text-indigo-600 cursor-pointer hover:underline">Login to like</span>
            </span>
          )}
        </div>
      )}
    </div>
  );
};

export default LikeButton;