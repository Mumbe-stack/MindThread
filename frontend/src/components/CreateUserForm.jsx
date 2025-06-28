import { useState } from "react";
import toast from "react-hot-toast";

const CreateUserForm = ({ onClose }) => {
  const [form, setForm] = useState({
    username: "",
    email: "",
    password: "",
    is_admin: false,
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    const token = localStorage.getItem("token");

    const res = await fetch(`${VITE_API_URL}/api/users`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(form),
    });

    if (res.ok) {
      toast.success("User created");
      onClose();
    } else {
      const data = await res.json();
      toast.error(data.error || "Creation failed");
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <input
        type="text"
        placeholder="Username"
        className="w-full p-2 border rounded"
        value={form.username}
        onChange={(e) => setForm({ ...form, username: e.target.value })}
        required
      />
      <input
        type="email"
        placeholder="Email"
        className="w-full p-2 border rounded"
        value={form.email}
        onChange={(e) => setForm({ ...form, email: e.target.value })}
        required
      />
      <input
        type="password"
        placeholder="Password"
        className="w-full p-2 border rounded"
        value={form.password}
        onChange={(e) => setForm({ ...form, password: e.target.value })}
        required
      />
      <label className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={form.is_admin}
          onChange={(e) => setForm({ ...form, is_admin: e.target.checked })}
        />
        Make Admin
      </label>
      <button type="submit" className="bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700">
        Create
      </button>
    </form>
  );
};

export default CreateUserForm;