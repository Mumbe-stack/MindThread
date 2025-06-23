import { Toaster } from "react-hot-toast";

const ToastContainer = () => (
  <Toaster
    position="top-right"
    toastOptions={{
      style: {
        background: "#1f2937",
        color: "#fff",
        fontSize: "14px",
      },
    }}
  />
);

export default ToastContainer;
