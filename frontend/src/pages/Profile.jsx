import { useContext, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { UserContext } from "../context/UserContext";
import AvatarUploader from "../components/AvatarUploader";

const Profile = () => {
  const { currentUser, delete_profile } = useContext(UserContext);
  const navigate = useNavigate();

  useEffect(() => {
    if (!currentUser) {
      navigate("/login");
    }
  }, [currentUser, navigate]);

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
        onClick={delete_profile}
        className="mt-6 bg-red-600 text-white py-2 px-4 rounded hover:bg-red-700 w-full"
      >
        Delete Account
      </button>
    </div>
  );
};

export default Profile;
