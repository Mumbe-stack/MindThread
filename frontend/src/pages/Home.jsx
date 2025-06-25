import { Link } from "react-router-dom";

const Home = () => {
  return (
    <div className="min-h-screen flex flex-col justify-center items-center bg-gray-50 px-4">
      <div className="max-w-2xl text-center">
        <h1 className="text-4xl sm:text-5xl font-extrabold text-indigo-700 mb-4">
          Welcome to MindThread
        </h1>
        <p className="text-gray-600 text-lg sm:text-xl mb-8">
          A modern blogging platform to share ideas, stories, and insights with the world.
        </p>
        <Link
          to="/posts"
          className="inline-block bg-indigo-600 hover:bg-indigo-700 text-white text-lg font-medium px-6 py-3 rounded-md transition duration-200"
        >
          Explore Posts
        </Link>
      </div>
    </div>
  );
};

export default Home;
