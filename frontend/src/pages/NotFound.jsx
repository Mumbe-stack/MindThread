import { Link } from "react-router-dom";

const NotFound = () => {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-100 p-6">
      <h1 className="text-6xl font-bold text-indigo-600 mb-4">404</h1>
      <p className="text-xl text-gray-700 mb-6">Oops! Page not found.</p>
      <Link
        to="/"
        className="text-white bg-indigo-600 hover:bg-indigo-700 px-6 py-2 rounded shadow"
      >
        Return to Home
      </Link>
    </div>
  );
};

export default NotFound;
