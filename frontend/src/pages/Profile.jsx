import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import AvatarUploader from "../components/AvatarUploader";
import { toast } from "react-hot-toast";

const Profile = () => {
  const { currentUser, deleteUser, token } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!token) {
      navigate("/login");
    }
  }, [token, navigate]);

  const handleDelete = async () => {
    const confirm = window.confirm("Are you sure you want to delete your account?");
    if (!confirm) return;

    try {
      await deleteUser(currentUser?.id); // This assumes the id is in currentUser
      toast.success("Your account has been deleted.");
      navigate("/login");
    } catch (error) {
      console.error(error);
      toast.error("Failed to delete account.");
    }
  };

  if (!currentUser) return <p className="text-center p-6">Loading profile...</p>;

  return (
    <div className="max-w-lg mx-auto p-6 bg-white shadow rounded mt-10">
      <h2 className="text-2xl font-bold mb-4 text-center">Your Profile</h2>
      <p className="mb-2"><strong>Username:</strong> {currentUser.username}</p>
      <p className="mb-2"><strong>Email:</strong> {currentUser.email}</p>
      <p className="mb-4 text-sm text-gray-500">
        Joined: {new Date(currentUser.created_at).toLocaleDateString()}
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
