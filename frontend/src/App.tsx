import { RouterProvider } from "react-router-dom";
import { AuthProvider } from "@/features/auth/context";
import { router } from "@/routes";

export function App() {
  return (
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  );
}
