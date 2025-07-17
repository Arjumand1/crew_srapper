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

        // Ensure extracted_data is properly parsed if it's a string
        const crewSheet = response.data;
        if (
          crewSheet.extracted_data &&
          typeof crewSheet.extracted_data === "string"
        ) {
          try {
            crewSheet.extracted_data = JSON.parse(crewSheet.extracted_data);
          } catch (parseError) {
            console.error("Error parsing extracted_data JSON:", parseError);
            // Keep as string if parsing fails
          }
        }

        this.currentCrewSheet = crewSheet;
      } catch (error: any) {
        this.error =
          error.response?.data?.detail || `Failed to fetch crew sheet #${id}`;
        console.error(`Error fetching crew sheet #${id}:`, error);
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
        const response = await axios.post(
          `${API_URL}/crew-sheets/${id}/process/`,
          {},
          {
            headers: {
              Authorization: `Bearer ${authStore.accessToken}`,
            },
          }
        );

        // Update the processed sheet with the returned data
        const processedSheet = response.data;

        // Update status in the local list
        const index = this.crewSheets.findIndex((sheet) => sheet.id === id);
        if (index !== -1) {
          this.crewSheets[index] = processedSheet;
        }

        // Update current crew sheet if it's the one being processed
        if (this.currentCrewSheet?.id === id) {
          this.currentCrewSheet = processedSheet;
        }

        return processedSheet;
      } catch (error: any) {
        this.error =
          error.response?.data?.detail || "Failed to process crew sheet";
        console.error("Error processing crew sheet:", error);
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async updateCrewSheetData(id: string, extractedData: any) {
      this.loading = true;
      this.error = null;

      try {
        const authStore = useAuthStore();

        // Prepare the payload with just the extracted data
        const payload = {
          extracted_data: extractedData,
        };

        // Send a PATCH request to update just the extracted data
        const response = await axios.patch(
          `${API_URL}/crew-sheets/${id}/`,
          payload,
          {
            headers: {
              Authorization: `Bearer ${authStore.accessToken}`,
              "Content-Type": "application/json",
            },
          }
        );

        // Update the sheet with the returned data
        const updatedSheet = response.data;

        // Update in the local list
        const index = this.crewSheets.findIndex((sheet) => sheet.id === id);
        if (index !== -1) {
          this.crewSheets[index] = updatedSheet;
        }

        // Update current crew sheet if it's the one being updated
        if (this.currentCrewSheet?.id === id) {
          this.currentCrewSheet = updatedSheet;
        }

        return updatedSheet;
      } catch (error: any) {
        this.error =
          error.response?.data?.detail || "Failed to update crew sheet data";
        console.error("Error updating crew sheet data:", error);
        throw error;
      } finally {
        this.loading = false;
      }
    },
  },
});
