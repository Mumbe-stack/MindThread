import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import toast from 'react-hot-toast';

const VITE_API_URL = import.meta.env.VITE_API_URL || "https://mindthread-1.onrender.com";

const LikeButton = ({ 
  type = 'post',
  id, 
  initialLikes = 0, 
  initialLiked = false,
  onLikeChange,
  size = 'normal',
  variant = 'default' 
}) => {
  const { user, token } = useAuth();
  const [likes, setLikes] = useState(initialLikes);
  const [isLiked, setIsLiked] = useState(initialLiked);
  const [isLoading, setIsLoading] = useState(false);


  useEffect(() => {
    if (user && token && id) {
      fetchLikeStatus();
    }
  }, [user, token, id, type]);

  const fetchLikeStatus = async () => {
    try {
      const endpoint = type === 'post' 
        ? `${VITE_API_URL}/api/posts/${id}`
        : `${VITE_API_URL}/api/comments/${id}`;

      const res = await fetch(endpoint, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        credentials: "include",
      });

      if (res.ok) {
        const data = await res.json();
        setLikes(data.likes_count || data.likes || 0);
        setIsLiked(data.liked_by_user || false);
      }
    } catch (error) {
      console.error(`Error fetching ${type} like status:`, error);
      
    }
  };

  const handleToggleLike = async () => {
    if (!user || !token) {
      toast.error(`Please log in to like ${type}s`);
      return;
    }

    if (isLoading) return; 

    setIsLoading(true);


    const wasLiked = isLiked;
    const previousLikes = likes;
    setIsLiked(!wasLiked);
    setLikes(wasLiked ? Math.max(0, previousLikes - 1) : previousLikes + 1);

    try {
      const endpoint = type === 'post' 
        ? `${VITE_API_URL}/api/posts/${id}/like`
        : `${VITE_API_URL}/api/comments/${id}/like`;

      const res = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        credentials: "include",
      });

      if (!res.ok) {
       
        setIsLiked(wasLiked);
        setLikes(previousLikes);

        const errorText = await res.text();
        let errorData;
        try {
          errorData = JSON.parse(errorText);
        } catch {
          errorData = { error: errorText };
        }
        
       
        if (res.status === 404) {
          toast.error(`${type.charAt(0).toUpperCase() + type.slice(1)} not found`);
        } else if (res.status === 401) {
          toast.error("Please log in again");
        } else if (res.status === 403) {
          toast.error("Access denied");
        } else {
          toast.error(errorData.error || `Failed to like ${type}`);
        }
        return;
      }

      const data = await res.json();

     
      const serverLikes = data.likes_count !== undefined ? data.likes_count : data.likes || 0;
      const serverLiked = data.liked_by_user !== undefined ? data.liked_by_user : !wasLiked;
      
      setLikes(serverLikes);
      setIsLiked(serverLiked);

      
      if (onLikeChange) {
        onLikeChange({
          id,
          type,
          likes: serverLikes,
          liked_by_user: serverLiked,
          isLiked: serverLiked
        });
      }

     
      const action = serverLiked ? 'liked' : 'unliked';
      toast.success(data.message || `${type.charAt(0).toUpperCase() + type.slice(1)} ${action}!`);

    } catch (error) {
    
      setIsLiked(wasLiked);
      setLikes(previousLikes);
      
      console.error(`Error toggling ${type} like:`, error);
      
     
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        toast.error("Network error - please check your connection");
      } else if (error.message.includes('Failed to fetch')) {
        toast.error("Unable to connect to server");
      } else {
        toast.error(`Network error while liking ${type}`);
      }
    } finally {
      setIsLoading(false);
    }
  };


  const sizeClasses = {
    small: {
      button: 'px-2 py-1 text-xs',
      icon: 'w-3 h-3',
      text: 'text-xs'
    },
    normal: {
      button: 'px-3 py-1 text-sm',
      icon: 'w-4 h-4',
      text: 'text-sm'
    },
    large: {
      button: 'px-4 py-2 text-base',
      icon: 'w-5 h-5',
      text: 'text-base'
    }
  };


  const getVariantClasses = () => {
    const base = 'inline-flex items-center gap-1 rounded-lg font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed';
    
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
    
    
    return `${base} ${
      isLiked 
        ? 'bg-red-100 text-red-600 border border-red-300 hover:bg-red-200' 
        : 'bg-gray-100 text-gray-700 border border-gray-300 hover:bg-gray-200'
    }`;
  };

  const currentSize = sizeClasses[size];

  return (
    <div className="flex items-center">
      {user ? (
        <button
          onClick={handleToggleLike}
          disabled={isLoading}
          className={`${getVariantClasses()} ${currentSize.button}`}
          aria-label={`${isLiked ? 'Unlike' : 'Like'} this ${type}`}
          title={`${isLiked ? 'Unlike' : 'Like'} this ${type}`}
        >
          {isLoading ? (
            <div className={`animate-spin rounded-full border-b-2 border-current ${currentSize.icon}`}></div>
          ) : (
            <svg
              className={`${currentSize.icon} ${isLiked ? 'fill-current' : ''}`}
              fill={isLiked ? 'currentColor' : 'none'}
              stroke="currentColor"
              viewBox="0 0 24 24"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"
              />
            </svg>
          )}
          
          {size !== 'small' && (
            <span className={currentSize.text}>
              {isLiked ? "Liked" : "Like"}
            </span>
          )}
          
          <span className={`font-semibold ${currentSize.text}`}>
            {likes}
          </span>
        </button>
      ) : (
        <div className={`flex items-center gap-1 text-gray-500 ${currentSize.text}`}>
          <svg
            className={`${currentSize.icon}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"
            />
          </svg>
          
          {size !== 'small' && (
            <span>Like</span>
          )}
          
          <span className="font-semibold">
            {likes}
          </span>
          
          {likes > 0 && size !== 'small' && (
            <span className="text-xs ml-1">
              • <span className="text-indigo-600 cursor-pointer hover:underline">Login to like</span>
            </span>
          )}
        </div>
      )}
    </div>
  );
};

export default LikeButton;