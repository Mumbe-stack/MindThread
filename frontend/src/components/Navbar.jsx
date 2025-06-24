import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const Navbar = () => {
  const { user, logout } = useAuth();

  return (
    <nav className="bg-gray-800 text-white p-4 flex justify-between items-center">
      <Link to="/" className="text-xl font-bold text-white">MyBlog</Link>
      <div className="flex items-center gap-4">
        <Link to="/" className="hover:underline">Home</Link>
        {user ? (
          <>
            <Link to="/profile" className="hover:underline">Profile</Link>
            {user.is_admin && <Link to="/admin" className="hover:underline">Admin</Link>}
            <button onClick={logout} className="bg-red-500 px-3 py-1 rounded hover:bg-red-600">Logout</button>
          </>
        ) : (
          <>
            <Link to="/login" className="hover:underline">Login</Link>
            <Link to="/register" className="hover:underline">Register</Link>
          </>
        )}
      </div>
    </nav>
  );
};

export default Navbar;
