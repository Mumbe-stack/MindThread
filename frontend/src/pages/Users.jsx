import { useEffect, useState } from "react";
import toast from "react-hot-toast";


const Users = () => {
  const [users, setUsers] = useState([]);

  useEffect(() => {
    fetch(`${VITE_API_URL}/api/users`, {
      headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
    })
      .then((res) => res.json())
      .then(setUsers)
      .catch(() => toast.error("Failed to load users"));
  }, []);

  const toggleBlock = async (id, block) => {
    try {
      await fetch(`${VITE_API_URL}/api/users/${id}/${block ? "block" : "unblock"}`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
      });

      const updated = users.map((u) =>
        u.id === id ? { ...u, is_blocked: block } : u
      );
      setUsers(updated);

      toast.success(`User ${block ? "blocked" : "unblocked"}`);
    } catch {
      toast.error("Operation failed");
    }
  };

  return (
    <div className="max-w-5xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6 text-indigo-800">All Users</h1>
      {users.length === 0 ? (
        <p className="text-gray-500">No users found.</p>
      ) : (
        users.map((user) => (
          <div
            key={user.id}
            className="flex justify-between items-center p-4 border-b"
          >
            <div>
              <p className="font-medium">{user.username}</p>
              <p className="text-sm text-gray-500">{user.email}</p>
            </div>
            <button
              onClick={() => toggleBlock(user.id, !user.is_blocked)}
              className={`px-3 py-1 rounded text-white ${
                user.is_blocked
                  ? "bg-yellow-500 hover:bg-yellow-600"
                  : "bg-red-600 hover:bg-red-700"
              }`}
            >
              {user.is_blocked ? "Unblock" : "Block"}
            </button>
          </div>
        ))
      )}
    </div>
  );
};

export default Users;
