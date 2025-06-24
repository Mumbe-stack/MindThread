import { useState } from "react";

const AvatarUploader = () => {
  const [file, setFile] = useState(null);

  const handleChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleUpload = async () => {
    if (!file) return alert("Please select a file");

    const formData = new FormData();
    formData.append("avatar", file);

    const res = await fetch("/api/users/upload-avatar", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${localStorage.getItem("token")}`,
      },
      body: formData,
    });

    if (res.ok) {
      alert("Avatar uploaded successfully");
    } else {
      alert("Upload failed");
    }
  };

  return (
    <div className="mt-4">
      <input type="file" onChange={handleChange} className="mb-2" />
      <button
        onClick={handleUpload}
        className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700"
      >
        Upload Avatar
      </button>
    </div>
  );
};

export default AvatarUploader;
