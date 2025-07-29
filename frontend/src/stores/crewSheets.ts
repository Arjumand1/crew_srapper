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

    async startSession(id: string) {
      try {
        const authStore = useAuthStore();
        const response = await axios.post(
          `${API_URL}/crew-sheets/${id}/start_session/`,
          {},
          {
            headers: {
              Authorization: `Bearer ${authStore.accessToken}`,
            },
          }
        );
        return response.data;
      } catch (error: any) {
        console.error("Error starting session:", error);
        throw error;
      }
    },

    async endSession(sessionId: string, outcome: string) {
      try {
        const authStore = useAuthStore();
        const response = await axios.post(
          `${API_URL}/crew-sheets/end_session/`,
          {
            session_id: sessionId,
            outcome: outcome,
          },
          {
            headers: {
              Authorization: `Bearer ${authStore.accessToken}`,
            },
          }
        );
        return response.data;
      } catch (error: any) {
        console.error("Error ending session:", error);
        throw error;
      }
    },

    async trackEdit(
      sessionId: string,
      fieldName: string,
      originalValue: any,
      newValue: any,
      employeeIndex: number | null = null,
      editTimeSeconds: number
    ) {
      try {
        const authStore = useAuthStore();
        const response = await axios.post(
          `${API_URL}/track_edit/`,
          {
            session_id: sessionId,
            field_name: fieldName,
            original_value: originalValue,
            new_value: newValue,
            employee_index: employeeIndex,
            edit_time_seconds: editTimeSeconds,
          },
          {
            headers: {
              Authorization: `Bearer ${authStore.accessToken}`,
            },
          }
        );
        return response.data;
      } catch (error: any) {
        console.error("Error tracking edit:", error);
        throw error;
      }
    },

    // AI Enhancement Methods
    async getTemplateSuggestions() {
      this.loading = true;
      this.error = null;

      try {
        const authStore = useAuthStore();
        const response = await axios.get(`${API_URL}/template_suggestions/`, {
          headers: {
            Authorization: `Bearer ${authStore.accessToken}`,
          },
        });
        return response.data.suggestions || [];
      } catch (error: any) {
        this.error =
          error.response?.data?.detail || "Failed to get template suggestions";
        console.error("Error getting template suggestions:", error);
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async processWithTemplate(id: string, templateId: string) {
      this.loading = true;
      this.error = null;

      try {
        const authStore = useAuthStore();
        const response = await axios.post(
          `${API_URL}/crew-sheets/${id}/process_with_template/`,
          { template_id: templateId },
          {
            headers: {
              Authorization: `Bearer ${authStore.accessToken}`,
            },
          }
        );

        // Update the processed sheet
        const processedSheet = response.data;
        const index = this.crewSheets.findIndex((sheet) => sheet.id === id);
        if (index !== -1) {
          this.crewSheets[index] = processedSheet;
        }
        if (this.currentCrewSheet?.id === id) {
          this.currentCrewSheet = processedSheet;
        }

        return processedSheet;
      } catch (error: any) {
        this.error =
          error.response?.data?.detail || "Failed to process with template";
        console.error("Error processing with template:", error);
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async processWithAI(id: string) {
      this.loading = true;
      this.error = null;

      try {
        const authStore = useAuthStore();
        const response = await axios.post(
          `${API_URL}/crew-sheets/${id}/process_with_template/`,
          { use_rag: true },
          {
            headers: {
              Authorization: `Bearer ${authStore.accessToken}`,
            },
          }
        );

        // Update the processed sheet
        const processedSheet = response.data;
        const index = this.crewSheets.findIndex((sheet) => sheet.id === id);
        if (index !== -1) {
          this.crewSheets[index] = processedSheet;
        }
        if (this.currentCrewSheet?.id === id) {
          this.currentCrewSheet = processedSheet;
        }

        return processedSheet;
      } catch (error: any) {
        this.error =
          error.response?.data?.detail || "Failed to process with AI";
        console.error("Error processing with AI:", error);
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async getReviewQueue() {
      try {
        const authStore = useAuthStore();
        const response = await axios.get(
          `${API_URL}/crew-sheets/review_queue/`,
          {
            headers: {
              Authorization: `Bearer ${authStore.accessToken}`,
            },
          }
        );
        return response.data;
      } catch (error: any) {
        console.error("Error getting review queue:", error);
        throw error;
      }
    },

    async getLearningInsights() {
      try {
        const authStore = useAuthStore();
        const response = await axios.get(
          `${API_URL}/crew-sheets/learning_insights/`,
          {
            headers: {
              Authorization: `Bearer ${authStore.accessToken}`,
            },
          }
        );
        return response.data;
      } catch (error: any) {
        console.error("Error getting learning insights:", error);
        throw error;
      }
    },

    // Company Learning Profile Methods
    async getCompanyLearningProfile() {
      try {
        const authStore = useAuthStore();
        const response = await axios.get(
          `${API_URL}/crew-sheets/company_learning_profile/`,
          {
            headers: {
              Authorization: `Bearer ${authStore.accessToken}`,
            },
          }
        );
        return response.data;
      } catch (error: any) {
        console.error("Error getting company learning profile:", error);
        throw error;
      }
    },

    async addCostCenter(costCenter: string) {
      try {
        const authStore = useAuthStore();
        const response = await axios.post(
          `${API_URL}/crew-sheets/add_cost_center/`,
          { cost_center: costCenter },
          {
            headers: {
              Authorization: `Bearer ${authStore.accessToken}`,
            },
          }
        );
        return response.data;
      } catch (error: any) {
        console.error("Error adding cost center:", error);
        throw error;
      }
    },

    async addTask(task: string) {
      try {
        const authStore = useAuthStore();
        const response = await axios.post(
          `${API_URL}/crew-sheets/add_task/`,
          { task: task },
          {
            headers: {
              Authorization: `Bearer ${authStore.accessToken}`,
            },
          }
        );
        return response.data;
      } catch (error: any) {
        console.error("Error adding task:", error);
        throw error;
      }
    },

    async removeCostCenter(costCenter: string) {
      try {
        const authStore = useAuthStore();
        const response = await axios.post(
          `${API_URL}/crew-sheets/remove_cost_center/`,
          { cost_center: costCenter },
          {
            headers: {
              Authorization: `Bearer ${authStore.accessToken}`,
            },
          }
        );
        return response.data;
      } catch (error: any) {
        console.error("Error removing cost center:", error);
        throw error;
      }
    },

    async removeTask(task: string) {
      try {
        const authStore = useAuthStore();
        const response = await axios.post(
          `${API_URL}/crew-sheets/remove_task/`,
          { task: task },
          {
            headers: {
              Authorization: `Bearer ${authStore.accessToken}`,
            },
          }
        );
        return response.data;
      } catch (error: any) {
        console.error("Error removing task:", error);
        throw error;
      }
    },

    // Crew Member Management Methods
    async addCrewMember(crewName: string) {
      try {
        const authStore = useAuthStore();
        const response = await axios.post(
          `${API_URL}/crew-sheets/add_crew_member/`,
          { crew_name: crewName },
          {
            headers: {
              Authorization: `Bearer ${authStore.accessToken}`,
            },
          }
        );
        return response.data;
      } catch (error: any) {
        console.error("Error adding crew member:", error);
        throw error;
      }
    },

    async removeCrewMember(crewName: string) {
      try {
        const authStore = useAuthStore();
        const response = await axios.post(
          `${API_URL}/crew-sheets/remove_crew_member/`,
          { crew_name: crewName },
          {
            headers: {
              Authorization: `Bearer ${authStore.accessToken}`,
            },
          }
        );
        return response.data;
      } catch (error: any) {
        console.error("Error removing crew member:", error);
        throw error;
      }
    },

    // Template Management Methods
    async getAllTemplates() {
      try {
        const authStore = useAuthStore();
        const response = await axios.get(`${API_URL}/templates/`, {
          headers: {
            Authorization: `Bearer ${authStore.accessToken}`,
          },
        });
        return response.data;
      } catch (error: any) {
        console.error("Error fetching templates:", error);
        throw error;
      }
    },

    async createTemplate(formData: FormData) {
      try {
        const authStore = useAuthStore();
        const response = await axios.post(`${API_URL}/templates/`, formData, {
          headers: {
            Authorization: `Bearer ${authStore.accessToken}`,
            "Content-Type": "multipart/form-data",
          },
        });
        return response.data;
      } catch (error: any) {
        console.error("Error creating template:", error);
        throw error;
      }
    },

    async updateTemplate(id: number, data: any) {
      try {
        const authStore = useAuthStore();
        const response = await axios.put(
          `${API_URL}/crew-sheets/templates/${id}/`,
          data,
          {
            headers: {
              Authorization: `Bearer ${authStore.accessToken}`,
            },
          }
        );
        return response.data;
      } catch (error: any) {
        console.error("Error updating template:", error);
        throw error;
      }
    },

    async deleteTemplate(id: number) {
      try {
        const authStore = useAuthStore();
        const response = await axios.delete(
          `${API_URL}/crew-sheets/templates/${id}/`,
          {
            headers: {
              Authorization: `Bearer ${authStore.accessToken}`,
            },
          }
        );
        return response.data;
      } catch (error: any) {
        console.error("Error deleting template:", error);
        throw error;
      }
    },
  },
});
