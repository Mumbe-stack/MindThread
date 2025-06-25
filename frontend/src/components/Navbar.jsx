import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const Navbar = () => {
  const { user, logout } = useAuth();

  return (
    <nav className="bg-gray-900 text-white shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo / Brand */}
          <div className="flex-shrink-0">
            <Link
              to="/"
              className="text-2xl font-semibold hover:text-indigo-400 transition cursor-pointer"
            >
              MindThread
            </Link>
          </div>

          {/* Navigation */}
          <div className="flex items-center justify-center gap-6">
            <Link
              to="/"
              className="hover:text-indigo-300 transition cursor-pointer"
            >
              Home
            </Link>

            {user ? (
              <>
                <Link
                  to="/posts"
                  className="hover:text-indigo-300 transition cursor-pointer"
                >
                  Posts
                </Link>

                {!user.is_admin && (
                  <Link
                    to="/create"
                    className="hover:text-indigo-300 transition cursor-pointer"
                  >
                    Create Post
                  </Link>
                )}

                <Link
                  to="/profile"
                  className="hover:text-indigo-300 transition cursor-pointer"
                >
                  Profile
                </Link>

                <span className="bg-slate-600 text-white px-3 py-1 rounded-full text-sm">
                  {user.username}
                </span>

                <button
                  onClick={logout}
                  className="bg-red-500 hover:bg-red-600 text-white px-3 py-1 rounded transition cursor-pointer"
                >
                  Logout
                </button>
              </>
            ) : (
              <>
                <Link
                  to="/login"
                  className="hover:text-indigo-300 transition cursor-pointer"
                >
                  Login
                </Link>
                <Link
                  to="/register"
                  className="hover:text-indigo-300 transition cursor-pointer"
                >
                  Register
                </Link>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
