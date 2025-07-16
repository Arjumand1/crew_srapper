import { defineStore } from "pinia";
import axios from "axios";

interface User {
  id: number;
  email: string;
  name: string;
  username: string;
}

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  loading: boolean;
  error: string | null;
}

// Use a helper function to safely access localStorage
const getStorageItem = (key: string): string | null => {
  try {
    return localStorage.getItem(key);
  } catch (e) {
    console.error(`Error accessing localStorage for key ${key}:`, e);
    return null;
  }
};

// Define the store using the composition API style (recommended)
export const useAuthStore = defineStore("auth", {
  state: () => ({
    user: null as User | null,
    accessToken: getStorageItem("accessToken"),
    refreshToken: getStorageItem("refreshToken"),
    loading: false,
    error: null as string | null,
  }),

  getters: {
    isAuthenticated: (state) => !!state.accessToken,
  },

  actions: {
    async register(
      email: string,
      username: string,
      name: string,
      password: string,
      password2: string
    ) {
      this.loading = true;
      this.error = null;

      try {
        const apiUrl =
          import.meta.env.VITE_API_URL || "http://localhost:8000/api";
        await axios.post(`${apiUrl}/auth/register/`, {
          email,
          username,
          name,
          password,
          password2,
        });

        // Automatically log in after registration
        return await this.login(email, password);
      } catch (error: any) {
        this.error =
          error.response?.data?.detail ||
          (error.response?.data
            ? JSON.stringify(error.response.data)
            : "Registration failed");
        console.error("Registration error:", error);
        return false;
      } finally {
        this.loading = false;
      }
    },

    async login(email: string, password: string) {
      this.loading = true;
      this.error = null;

      try {
        const apiUrl =
          import.meta.env.VITE_API_URL || "http://localhost:8000/api";
        const response = await axios.post(`${apiUrl}/auth/token/`, {
          email,
          password,
        });

        this.accessToken = response.data.access;
        this.refreshToken = response.data.refresh;

        try {
          localStorage.setItem("accessToken", response.data.access);
          localStorage.setItem("refreshToken", response.data.refresh);
        } catch (e) {
          console.error("Failed to save tokens to localStorage:", e);
        }

        await this.fetchUser();
        return true;
      } catch (error: any) {
        this.error = error.response?.data?.detail || "Login failed";
        console.error("Login error:", error);
        return false;
      } finally {
        this.loading = false;
      }
    },

    async fetchUser() {
      if (!this.accessToken) return;

      this.loading = true;

      try {
        const apiUrl =
          import.meta.env.VITE_API_URL || "http://localhost:8000/api";
        // Configure axios with the access token
        const response = await axios.get(`${apiUrl}/auth/me/`, {
          headers: {
            Authorization: `Bearer ${this.accessToken}`,
          },
        });

        this.user = response.data;
      } catch (error: any) {
        console.error("Error fetching user:", error);
        if (error.response?.status === 401) {
          // If unauthorized, clear tokens
          this.logout();
        }
      } finally {
        this.loading = false;
      }
    },

    logout() {
      this.user = null;
      this.accessToken = null;
      this.refreshToken = null;

      try {
        localStorage.removeItem("accessToken");
        localStorage.removeItem("refreshToken");
      } catch (e) {
        console.error("Failed to remove tokens from localStorage:", e);
      }
    },
  },
});
