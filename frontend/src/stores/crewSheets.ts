import { defineStore } from "pinia";
import axios from "axios";
import { useAuthStore } from "./auth";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

export interface CrewSheet {
  id: string;
  name: string;
  image: string;
  date_uploaded: string;
  status: "pending" | "processing" | "completed" | "failed";
  date_processed?: string;
  error_message?: string;
  extracted_data?: any;
}

export const useCrewSheetStore = defineStore("crewSheets", {
  state: () => ({
    crewSheets: [] as CrewSheet[],
    currentCrewSheet: null as CrewSheet | null,
    loading: false,
    error: null as string | null,
  }),

  actions: {
    async fetchCrewSheets() {
      this.loading = true;
      this.error = null;

      try {
        const authStore = useAuthStore();
        const response = await axios.get(`${API_URL}/crew-sheets/`, {
          headers: {
            Authorization: `Bearer ${authStore.accessToken}`,
          },
        });

        this.crewSheets = response.data;
      } catch (error: any) {
        this.error =
          error.response?.data?.detail || "Failed to fetch crew sheets";
        console.error("Error fetching crew sheets:", error);
      } finally {
        this.loading = false;
      }
    },

    async fetchCrewSheet(id: string) {
      this.loading = true;
      this.error = null;

      try {
        const authStore = useAuthStore();
        const response = await axios.get(`${API_URL}/crew-sheets/${id}/`, {
          headers: {
            Authorization: `Bearer ${authStore.accessToken}`,
          },
        });

        this.currentCrewSheet = response.data;
      } catch (error: any) {
        this.error =
          error.response?.data?.detail || "Failed to fetch crew sheet";
        console.error("Error fetching crew sheet:", error);
      } finally {
        this.loading = false;
      }
    },

    async uploadCrewSheet(formData: FormData) {
      this.loading = true;
      this.error = null;

      try {
        const authStore = useAuthStore();
        const response = await axios.post(`${API_URL}/crew-sheets/`, formData, {
          headers: {
            Authorization: `Bearer ${authStore.accessToken}`,
            "Content-Type": "multipart/form-data",
          },
        });

        this.crewSheets = [response.data, ...this.crewSheets];
        return response.data;
      } catch (error: any) {
        this.error =
          error.response?.data?.detail || "Failed to upload crew sheet";
        console.error("Error uploading crew sheet:", error);
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async processCrewSheet(id: string) {
      this.loading = true;
      this.error = null;

      try {
        const authStore = useAuthStore();
        await axios.post(
          `${API_URL}/crew-sheets/${id}/process/`,
          {},
          {
            headers: {
              Authorization: `Bearer ${authStore.accessToken}`,
            },
          }
        );

        // Update status in the local list
        const index = this.crewSheets.findIndex((sheet) => sheet.id === id);
        if (index !== -1) {
          this.crewSheets[index].status = "processing";
        }

        if (this.currentCrewSheet?.id === id) {
          this.currentCrewSheet.status = "processing";
        }
      } catch (error: any) {
        this.error =
          error.response?.data?.detail || "Failed to process crew sheet";
        console.error("Error processing crew sheet:", error);
      } finally {
        this.loading = false;
      }
    },
  },
});
