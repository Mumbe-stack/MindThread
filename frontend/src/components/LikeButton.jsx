import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import toast from "react-hot-toast";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";

const LikeButton = ({ type, id }) => {
  const { token } = useAuth();
  const [liked, setLiked] = useState(false);
  const [likeCount, setLikeCount] = useState(0);
  const [vote, setVote] = useState(null); // upvote = 1, downvote = -1

  // Fetch like and vote status
  useEffect(() => {
    if (!token) return;

    const fetchStatus = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/${type}s/${id}/status`, {
          headers: {
            Authorization: `Bearer ${token}`
          }
        });
        if (res.ok) {
          const data = await res.json();
          setLiked(data.liked);
          setLikeCount(data.like_count);
          setVote(data.vote);
        }
      } catch (err) {
        console.error("Error fetching like/vote status:", err);
      }
    };

    fetchStatus();
  }, [token, type, id]);

  // Toggle Like
  const toggleLike = async () => {
    if (!token) return toast.error("Login required");

    try {
      const res = await fetch(`${API_BASE_URL}/api/${type}s/${id}/like`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`
        }
      });

      if (res.ok) {
        const result = await res.json();
        setLiked((prev) => !prev);
        setLikeCount((prev) => (liked ? prev - 1 : prev + 1));
      } else {
        const error = await res.json();
        toast.error(error?.error || "Could not like");
      }
    } catch {
      toast.error("Network error");
    }
  };

  // Cast vote
  const castVote = async (value) => {
    if (!token) return toast.error("Login required");

    try {
      const res = await fetch(`${API_BASE_URL}/api/votes/${type}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          [`${type}_id`]: id,
          value
        })
      });

      if (res.ok) {
        setVote(value);
      } else {
        const error = await res.json();
        toast.error(error?.error || "Failed to vote");
      }
    } catch {
      toast.error("Vote failed");
    }
  };

  return (
    <div className="flex gap-2 items-center text-sm">
      <button onClick={toggleLike} className="text-indigo-600 hover:underline">
        {liked ? "Unlike" : "Like"} ({likeCount})
      </button>
      <button
        onClick={() => castVote(1)}
        className={`px-1 ${vote === 1 ? "text-green-600 font-bold" : "text-gray-500"}`}
      >
        ⬆
      </button>
      <button
        onClick={() => castVote(-1)}
        className={`px-1 ${vote === -1 ? "text-red-600 font-bold" : "text-gray-500"}`}
      >
        ⬇
      </button>
    </div>
  );
};

export default LikeButton;
