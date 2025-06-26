import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";

const LikeButton = ({ type, id }) => {
  const { token } = useAuth();
  const [liked, setLiked] = useState(false);
  const [likeCount, setLikeCount] = useState(0);
  const [vote, setVote] = useState(null); // 1 = upvote, -1 = downvote

  // Fetch like count and vote status
  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/${type}s/${id}`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (res.ok) {
          const data = await res.json();

          // Assuming backend returns `likes` as array of users or count directly
          setLikeCount(data.likes?.length || data.likes || 0);

          // Check if current user liked
          if (data.liked_by?.some((u) => u.id === user.id)) {
            setLiked(true);
          }

          // If the backend returns vote info, set it here too
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
      const res = await fetch(`${API_BASE_URL}/api/${type}s/${id}/like`, {
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
      const res = await fetch(`${API_BASE_URL}/api/votes/${type}`, {
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
