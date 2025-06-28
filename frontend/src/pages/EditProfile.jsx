import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import toast from "react-hot-toast";

const API_URL = import.meta.env.VITE_API_URL || "https://mindthread-1.onrender.com";

const EditProfile = () => {
  const { user, token, loading } = useAuth();
  const navigate = useNavigate();
  
  // Profile form state
  const [profileData, setProfileData] = useState({
    username: "",
    email: "",
  });
  
  // Password form state
  const [passwordData, setPasswordData] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });
  
  // UI state
  const [isUpdatingProfile, setIsUpdatingProfile] = useState(false);
  const [isUpdatingPassword, setIsUpdatingPassword] = useState(false);
  const [showPasswordForm, setShowPasswordForm] = useState(false);
  const [errors, setErrors] = useState({});
  const [hasChanges, setHasChanges] = useState(false);

  // Initialize form with user data
  useEffect(() => {
    if (user) {
      setProfileData({
        username: user.username || "",
        email: user.email || "",
      });
    }
  }, [user]);

  // Redirect if not authenticated
  useEffect(() => {
    if (!loading && !token && !user) {
      navigate("/login");
    }
  }, [token, loading, user, navigate]);

  // Check for changes
  useEffect(() => {
    if (user) {
      const hasProfileChanges = 
        profileData.username !== user.username ||
        profileData.email !== user.email;
      setHasChanges(hasProfileChanges);
    }
  }, [profileData, user]);

  const handleApiResponse = async (response, errorMessage = "API request failed") => {
    if (!response.ok) {
      let errorText = errorMessage;
      try {
        const errorData = await response.json();
        errorText = errorData.error || errorData.message || errorMessage;
      } catch {
        if (response.status === 404) {
          errorText = `Endpoint not found: ${response.url}`;
        } else if (response.status === 403) {
          errorText = "Access denied";
        } else if (response.status === 401) {
          errorText = "Authentication required";
        } else {
          errorText = `${errorMessage} (${response.status})`;
        }
      }
      throw new Error(errorText);
    }

    const contentType = response.headers.get("content-type");
    if (!contentType || !contentType.includes("application/json")) {
      throw new Error("Server returned non-JSON response");
    }

    return response.json();
  };

  const makeAuthenticatedRequest = async (url, options = {}) => {
    try {
      const response = await fetch(url, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
          ...options.headers,
        },
        credentials: "include",
      });
      return response;
    } catch (error) {
      console.error("Network error:", error);
      throw new Error("Network error. Please check your connection.");
    }
  };

  const validateProfileForm = () => {
    const newErrors = {};

    // Username validation
    if (!profileData.username.trim()) {
      newErrors.username = "Username is required";
    } else if (profileData.username.trim().length < 3) {
      newErrors.username = "Username must be at least 3 characters";
    } else if (profileData.username.trim().length > 20) {
      newErrors.username = "Username must be less than 20 characters";
    } else if (!/^[a-zA-Z0-9_]+$/.test(profileData.username.trim())) {
      newErrors.username = "Username can only contain letters, numbers, and underscores";
    }

    // Email validation
    if (!profileData.email.trim()) {
      newErrors.email = "Email is required";
    } else if (!/^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(profileData.email.trim())) {
      newErrors.email = "Please enter a valid email address";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const validatePasswordForm = () => {
    const newErrors = {};

    // Current password validation
    if (!passwordData.current_password) {
      newErrors.current_password = "Current password is required";
    }

    // New password validation
    if (!passwordData.new_password) {
      newErrors.new_password = "New password is required";
    } else if (passwordData.new_password.length < 6) {
      newErrors.new_password = "Password must be at least 6 characters";
    } else if (passwordData.new_password.length > 100) {
      newErrors.new_password = "Password must be less than 100 characters";
    }

    // Confirm password validation
    if (!passwordData.confirm_password) {
      newErrors.confirm_password = "Please confirm your new password";
    } else if (passwordData.new_password !== passwordData.confirm_password) {
      newErrors.confirm_password = "Passwords do not match";
    }

    // Check if new password is different from current
    if (passwordData.current_password === passwordData.new_password) {
      newErrors.new_password = "New password must be different from current password";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleProfileSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateProfileForm()) {
      return;
    }

    if (!hasChanges) {
      toast.info("No changes to save");
      return;
    }

    setIsUpdatingProfile(true);

    try {
      console.log("Updating profile:", { ...profileData });

      const response = await makeAuthenticatedRequest(`${API_URL}/api/users/me`, {
        method: "PATCH",
        body: JSON.stringify({
          username: profileData.username.trim(),
          email: profileData.email.trim().toLowerCase(),
        }),
      });

      const result = await handleApiResponse(response, "Failed to update profile");
      
      console.log("Profile update success:", result);
      toast.success("Profile updated successfully!");
      
      // Navigate back to profile page
      navigate("/profile");

    } catch (error) {
      console.error("Profile update error:", error);
      
      if (error.message.includes("Username already exists")) {
        setErrors({ username: "This username is already taken" });
      } else if (error.message.includes("Email already exists")) {
        setErrors({ email: "This email is already taken" });
      } else if (error.message.includes("401") || error.message.includes("Authentication")) {
        toast.error("Authentication expired. Please log in again.");
        navigate("/login");
      } else {
        toast.error(`Failed to update profile: ${error.message}`);
      }
    } finally {
      setIsUpdatingProfile(false);
    }
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    
    if (!validatePasswordForm()) {
      return;
    }

    setIsUpdatingPassword(true);

    try {
      console.log("Updating password");

      const response = await makeAuthenticatedRequest(`${API_URL}/api/users/me`, {
        method: "PATCH",
        body: JSON.stringify({
          current_password: passwordData.current_password,
          new_password: passwordData.new_password,
        }),
      });

      const result = await handleApiResponse(response, "Failed to update password");
      
      console.log("Password update success:", result);
      toast.success("Password updated successfully!");
      
      // Reset password form
      setPasswordData({
        current_password: "",
        new_password: "",
        confirm_password: "",
      });
      setShowPasswordForm(false);

    } catch (error) {
      console.error("Password update error:", error);
      
      if (error.message.includes("Current password is incorrect")) {
        setErrors({ current_password: "Current password is incorrect" });
      } else if (error.message.includes("401") || error.message.includes("Authentication")) {
        toast.error("Authentication expired. Please log in again.");
        navigate("/login");
      } else {
        toast.error(`Failed to update password: ${error.message}`);
      }
    } finally {
      setIsUpdatingPassword(false);
    }
  };

  const handleProfileChange = (e) => {
    const { name, value } = e.target;
    setProfileData(prev => ({
      ...prev,
      [name]: value
    }));
    
    // Clear field-specific errors when user starts typing
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ""
      }));
    }
  };

  const handlePasswordChange = (e) => {
    const { name, value } = e.target;
    setPasswordData(prev => ({
      ...prev,
      [name]: value
    }));
    
    // Clear field-specific errors when user starts typing
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ""
      }));
    }
  };

  const handleCancel = () => {
    navigate("/profile");
  };

  const resetProfileForm = () => {
    if (user) {
      setProfileData({
        username: user.username || "",
        email: user.email || "",
      });
      setErrors({});
    }
  };

  const resetPasswordForm = () => {
    setPasswordData({
      current_password: "",
      new_password: "",
      confirm_password: "",
    });
    setShowPasswordForm(false);
    setErrors({});
  };

  if (loading) {
    return (
      <div className="max-w-2xl mx-auto p-6 bg-white shadow-lg rounded-lg mt-10">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded mb-6"></div>
          <div className="space-y-4">
            <div className="h-10 bg-gray-200 rounded"></div>
            <div className="h-10 bg-gray-200 rounded"></div>
            <div className="h-10 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!user && !loading && !token) {
    return (
      <div className="max-w-2xl mx-auto p-6 text-center">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-yellow-800">Redirecting to login...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto p-6 bg-white shadow-lg rounded-lg mt-10">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">Edit Profile</h2>
          <p className="text-gray-600 mt-1">Update your account information</p>
        </div>
        <button
          onClick={handleCancel}
          className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
        >
          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
          Cancel
        </button>
      </div>

      {/* Profile Information Form */}
      <div className="bg-gray-50 rounded-lg p-6 mb-8">
        <h3 className="text-xl font-semibold text-gray-900 mb-4">Profile Information</h3>
        
        <form onSubmit={handleProfileSubmit} className="space-y-6">
          {/* Username Field */}
          <div>
            <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-2">
              Username
            </label>
            <input
              type="text"
              id="username"
              name="username"
              value={profileData.username}
              onChange={handleProfileChange}
              className={`block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                errors.username ? 'border-red-300 focus:border-red-500' : 'border-gray-300 focus:border-indigo-500'
              }`}
              placeholder="Enter your username"
            />
            {errors.username && (
              <p className="mt-1 text-sm text-red-600">{errors.username}</p>
            )}
            <p className="mt-1 text-sm text-gray-500">
              3-20 characters, letters, numbers, and underscores only
            </p>
          </div>

          {/* Email Field */}
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
              Email Address
            </label>
            <input
              type="email"
              id="email"
              name="email"
              value={profileData.email}
              onChange={handleProfileChange}
              className={`block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                errors.email ? 'border-red-300 focus:border-red-500' : 'border-gray-300 focus:border-indigo-500'
              }`}
              placeholder="Enter your email address"
            />
            {errors.email && (
              <p className="mt-1 text-sm text-red-600">{errors.email}</p>
            )}
          </div>

          {/* Form Actions */}
          <div className="flex items-center justify-between">
            <button
              type="button"
              onClick={resetProfileForm}
              className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              Reset Changes
            </button>
            
            <div className="flex items-center space-x-3">
              {hasChanges && (
                <span className="text-sm text-orange-600 font-medium">
                  You have unsaved changes
                </span>
              )}
              <button
                type="submit"
                disabled={isUpdatingProfile || !hasChanges}
                className="inline-flex items-center px-6 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                {isUpdatingProfile ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Updating...
                  </>
                ) : (
                  "Update Profile"
                )}
              </button>
            </div>
          </div>
        </form>
      </div>

      {/* Password Change Section */}
      <div className="bg-gray-50 rounded-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-xl font-semibold text-gray-900">Change Password</h3>
            <p className="text-gray-600 text-sm">Update your account password</p>
          </div>
          {!showPasswordForm && (
            <button
              onClick={() => setShowPasswordForm(true)}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-indigo-600 bg-indigo-100 hover:bg-indigo-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
            >
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
              </svg>
              Change Password
            </button>
          )}
        </div>

        {showPasswordForm && (
          <form onSubmit={handlePasswordSubmit} className="space-y-6">
            {/* Current Password */}
            <div>
              <label htmlFor="current_password" className="block text-sm font-medium text-gray-700 mb-2">
                Current Password
              </label>
              <input
                type="password"
                id="current_password"
                name="current_password"
                value={passwordData.current_password}
                onChange={handlePasswordChange}
                className={`block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                  errors.current_password ? 'border-red-300 focus:border-red-500' : 'border-gray-300 focus:border-indigo-500'
                }`}
                placeholder="Enter your current password"
              />
              {errors.current_password && (
                <p className="mt-1 text-sm text-red-600">{errors.current_password}</p>
              )}
            </div>

            {/* New Password */}
            <div>
              <label htmlFor="new_password" className="block text-sm font-medium text-gray-700 mb-2">
                New Password
              </label>
              <input
                type="password"
                id="new_password"
                name="new_password"
                value={passwordData.new_password}
                onChange={handlePasswordChange}
                className={`block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                  errors.new_password ? 'border-red-300 focus:border-red-500' : 'border-gray-300 focus:border-indigo-500'
                }`}
                placeholder="Enter your new password"
              />
              {errors.new_password && (
                <p className="mt-1 text-sm text-red-600">{errors.new_password}</p>
              )}
              <p className="mt-1 text-sm text-gray-500">
                Minimum 6 characters
              </p>
            </div>

            {/* Confirm New Password */}
            <div>
              <label htmlFor="confirm_password" className="block text-sm font-medium text-gray-700 mb-2">
                Confirm New Password
              </label>
              <input
                type="password"
                id="confirm_password"
                name="confirm_password"
                value={passwordData.confirm_password}
                onChange={handlePasswordChange}
                className={`block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                  errors.confirm_password ? 'border-red-300 focus:border-red-500' : 'border-gray-300 focus:border-indigo-500'
                }`}
                placeholder="Confirm your new password"
              />
              {errors.confirm_password && (
                <p className="mt-1 text-sm text-red-600">{errors.confirm_password}</p>
              )}
            </div>

            {/* Password Form Actions */}
            <div className="flex items-center justify-between">
              <button
                type="button"
                onClick={resetPasswordForm}
                className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"
              >
                Cancel
              </button>
              
              <button
                type="submit"
                disabled={isUpdatingPassword}
                className="inline-flex items-center px-6 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                {isUpdatingPassword ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Updating...
                  </>
                ) : (
                  "Update Password"
                )}
              </button>
            </div>
          </form>
        )}
      </div>

      {/* Debug Panel (Development Only) */}
      {import.meta.env.DEV && (
        <div className="fixed bottom-4 right-4 bg-gray-800 text-white p-4 rounded-lg text-xs max-w-sm z-50">
          <h4 className="font-bold mb-2">🔍 Edit Profile Debug</h4>
          <div className="space-y-1">
            <div>API: {API_URL}</div>
            <div>User: {user?.username}</div>
            <div>Token: {token ? "✅ Present" : "❌ Missing"}</div>
            <div>Has Changes: {hasChanges ? "✅" : "❌"}</div>
            <div>Errors: {Object.keys(errors).length}</div>
          </div>
          <button
            onClick={() => console.log({ profileData, passwordData, errors, hasChanges, user })}
            className="mt-2 text-xs bg-gray-700 px-2 py-1 rounded hover:bg-gray-600"
          >
            Log Debug Data
          </button>
        </div>
      )}
    </div>
  );
};

export default EditProfile;