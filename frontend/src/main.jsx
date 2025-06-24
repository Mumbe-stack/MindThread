import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { PostProvider } from "./context/PostContext"; 
import { UserProvider } from "./context/UserContext"; 
import App from "./App";
import "./index.css";
import 'react-quill/dist/quill.snow.css';


createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <PostProvider>
          <UserProvider>
          <App />
        </UserProvider>
        </PostProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>
);
