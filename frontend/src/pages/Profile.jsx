import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import AvatarUploader from "../components/AvatarUploader";
import toast from "react-hot-toast"; 

const Profile = () => {
  const { user, logout } = useAuth();
  const [profile, setProfile] = useState(null);

  useEffect(() => {
    fetch("/api/auth/me", {
      headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
    })
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load profile");
        return res.json();
      })
      .then(setProfile)
      .catch(() => toast.error("Failed to load profile"));
  }, []);

  const handleDelete = async () => {
    const confirm = window.confirm("Are you sure you want to delete your account?");
    if (!confirm) return;

    const res = await fetch(`/api/users/${user.id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
    });

    if (res.ok) {
      toast.success("Account deleted");
      logout();
    } else {
      toast.error("Failed to delete account");
    }
  };

  if (!profile) return <p className="text-center p-6">Loading profile...</p>;

  return (
    <div className="max-w-lg mx-auto p-6 bg-white shadow rounded mt-10">
      <h2 className="text-2xl font-bold mb-4 text-center">Your Profile</h2>
      <p className="mb-2"><strong>Username:</strong> {profile.username}</p>
      <p className="mb-2"><strong>Email:</strong> {profile.email}</p>
      <p className="mb-4 text-sm text-gray-500">
        Joined: {new Date(profile.created_at).toLocaleDateString()}
      </p>

      <AvatarUploader />

      <button
        onClick={handleDelete}
        className="mt-6 bg-red-600 text-white py-2 px-4 rounded hover:bg-red-700 w-full"
      >
        Delete Account
      </button>
    </div>
  );
};

export default Profile;
