import { Link } from "react-router-dom";

const Home = () => {
  return (
    <div className="max-w-3xl mx-auto p-8 text-center">
      <h1 className="text-4xl font-bold text-indigo-700 mb-4">Welcome to MindThread</h1>
      <p className="text-gray-600 text-lg mb-6">
        A modern blogging platform to share ideas, stories, and insights with the world.
      </p>
      <Link
        to="/posts"
        className="inline-block bg-indigo-600 text-white px-6 py-2 rounded hover:bg-indigo-700 transition"
      >
        Explore Posts
      </Link>
    </div>
  );
};

export default Home;
