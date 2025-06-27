import { useState, useRef, useEffect } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import toast from "react-hot-toast";

const Login = () => {
  const { login, isAuthenticated, loading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || "/";
  
  const [formData, setFormData] = useState({ email: "", password: "" });
  const [isLoading, setIsLoading] = useState(false);
  const [errors, setErrors] = useState({});
  const calledRef = useRef(false);

  // Redirect if already authenticated
  useEffect(() => {
    if (!loading && isAuthenticated) {
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, loading, navigate, from]);

  useEffect(() => {
    calledRef.current = false;
  }, [formData.email, formData.password]);

  const validateForm = () => {
    const newErrors = {};

    if (!formData.email.trim()) {
      newErrors.email = "Email is required";
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = "Please enter a valid email";
    }

    if (!formData.password.trim()) {
      newErrors.password = "Password is required";
    } else if (formData.password.length < 6) {
      newErrors.password = "Password must be at least 6 characters";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));

    // Clear specific field error when user starts typing
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: "" }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm() || isLoading || calledRef.current) return;

    setIsLoading(true);
    calledRef.current = true;

    try {
      // Call login with credentials object as expected by AuthContext
      const result = await login({
        email: formData.email.trim().toLowerCase(),
        password: formData.password
      });

      if (result.success) {
        // AuthContext already handles success toast and navigation
        // Just ensure we don't call this multiple times
        return;
      } else {
        // Handle login failure
        setErrors({ 
          general: result.error || "Login failed. Please check your credentials." 
        });
      }
    } catch (err) {
      console.error("Login error:", err);
      setErrors({ 
        general: "Network error. Please check your connection and try again." 
      });
      toast.error("Network error. Please try again.");
    } finally {
      setIsLoading(false);
      calledRef.current = false;
    }
  };

  // Show loading while checking authentication status
  if (loading) {
    return (
      <div className="max-w-md mx-auto p-6 mt-20 bg-white shadow rounded">
        <div className="flex justify-center items-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-2 text-gray-600">Loading...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-md mx-auto p-6 mt-20 bg-white shadow rounded">
      <h2 className="text-2xl font-bold mb-4 text-center text-gray-800">Sign In</h2>

      {errors.general && (
        <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
          {errors.general}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
            Email Address
          </label>
          <input
            id="email"
            type="email"
            name="email"
            placeholder="Enter your email"
            className={`w-full p-3 border rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              errors.email 
                ? "border-red-500 bg-red-50" 
                : "border-gray-300 hover:border-gray-400 focus:border-blue-500"
            }`}
            aria-invalid={!!errors.email}
            aria-describedby={errors.email ? "email-error" : undefined}
            value={formData.email}
            onChange={handleChange}
            disabled={isLoading}
            autoComplete="username"
            required
          />
          {errors.email && (
            <p id="email-error" className="text-red-500 text-sm mt-1" role="alert">
              {errors.email}
            </p>
          )}
        </div>

        <div>
          <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
            Password
          </label>
          <input
            id="password"
            type="password"
            name="password"
            placeholder="Enter your password"
            className={`w-full p-3 border rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              errors.password 
                ? "border-red-500 bg-red-50" 
                : "border-gray-300 hover:border-gray-400 focus:border-blue-500"
            }`}
            aria-invalid={!!errors.password}
            aria-describedby={errors.password ? "password-error" : undefined}
            value={formData.password}
            onChange={handleChange}
            disabled={isLoading}
            autoComplete="current-password"
            required
          />
          {errors.password && (
            <p id="password-error" className="text-red-500 text-sm mt-1" role="alert">
              {errors.password}
            </p>
          )}
        </div>

        <button
          type="submit"
          disabled={isLoading || !formData.email.trim() || !formData.password.trim()}
          className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-medium transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:bg-gray-400 disabled:cursor-not-allowed disabled:hover:bg-gray-400"
          aria-describedby="submit-help"
        >
          {isLoading ? (
            <span className="flex items-center justify-center">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              Signing in...
            </span>
          ) : (
            "Sign In"
          )}
        </button>
        
        <p id="submit-help" className="text-xs text-gray-500 text-center">
          Click to sign in to your account
        </p>
      </form>

      <div className="mt-6 text-center">
        <p className="text-sm text-gray-600">
          Don't have an account?{" "}
          <Link 
            to="/register" 
            className="text-blue-600 hover:text-blue-800 hover:underline font-medium focus:outline-none focus:underline"
          >
            Create one here
          </Link>
        </p>
      </div>

      {/* Optional: Add forgot password link */}
      <div className="mt-4 text-center">
        <Link 
          to="/forgot-password" 
          className="text-sm text-gray-500 hover:text-gray-700 hover:underline focus:outline-none focus:underline"
        >
          Forgot your password?
        </Link>
      </div>
    </div>
  );
};

export default Login;