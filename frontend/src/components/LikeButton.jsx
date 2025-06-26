import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";

const VITE_API_URL = import.meta.env.VITE_API_URL;

const LikeButton = ({ type, id }) => {
  const { token } = useAuth();
  const [liked, setLiked] = useState(false);
  const [likeCount, setLikeCount] = useState(0);
  const [vote, setVote] = useState(null); 

  
  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(`${VITE_API_URL}/api/${type}s/${id}`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (res.ok) {
          const data = await res.json();

          
          setLikeCount(data.likes?.length || data.likes || 0);

         
          if (data.liked_by?.some((u) => u.id === user.id)) {
            setLiked(true);
          }

         
          if (data.user_vote === 1) setVote(1);
          else if (data.user_vote === -1) setVote(-1);
        }
      } catch (err) {
        console.error("Failed to fetch data:", err);
      }
    };

    fetchData();
  }, [id, token, type]);

  const toggleLike = async () => {
    try {
      const res = await fetch(`${VITE_API_URL}/api/${type}s/${id}/like`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (res.ok) {
        setLiked(!liked);
        setLikeCount((prev) => (liked ? prev - 1 : prev + 1));
      } else {
        console.error("Failed to toggle like");
      }
    } catch (err) {
      console.error("Error toggling like:", err);
    }
  };

  const castVote = async (value) => {
    try {
      const res = await fetch(`${VITE_API_URL}/api/votes/${type}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          [`${type}_id`]: id,
          value,
        }),
      });

      if (res.ok) {
        setVote(value);
      } else {
        console.error("Failed to cast vote");
      }
    } catch (err) {
      console.error("Error voting:", err);
    }
  };

  return (
    <div className="flex gap-3 items-center text-sm">
      <button
        onClick={toggleLike}
        className="text-indigo-600 hover:underline cursor-pointer"
      >
        {liked ? "Unlike" : "Like"} ({likeCount})
      </button>
      <button
        onClick={() => castVote(1)}
        className={`px-2 text-lg ${
          vote === 1 ? "text-green-600 font-bold" : "text-gray-400"
        }`}
      >
        ⬆
      </button>
      <button
        onClick={() => castVote(-1)}
        className={`px-2 text-lg ${
          vote === -1 ? "text-red-600 font-bold" : "text-gray-400"
        }`}
      >
        ⬇
      </button>
    </div>
  );
};

export default LikeButton;
