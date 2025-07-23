import { defineStore } from "pinia";
import axios from "axios";
import { useAuthStore } from "./auth";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

export interface QualityMetrics {
  confidence_score_avg: number;
  sheets_completed: number;
  sheets_needs_review: number;
  total_sheets: number;
  sheets_by_status?: Record<string, number>;
  avg_confidence_score?: number;
  total_sheets_processed?: number;
  sheets_needing_review?: number;
  processing_success_rate?: number;
}

export interface UserInsights {
  avg_edit_time: number;
  avg_session_duration: number;
  common_edits: Array<{ field_name: string; count: number }>;
  total_edits: number;
  total_sessions: number;
  total_sheets?: number;
  avg_edits_per_sheet?: number;
  completion_rate?: number;
  most_edited_fields?: Record<string, number>;
}

export interface ImprovementSuggestion {
  recommendations?: Array<{
    description: string;
    priority: string;
    category: string;
  }>;
  most_common_issues?: Array<[string, number]>;
}

// Default initial states with all required properties
const defaultQualityMetrics: QualityMetrics = {
  confidence_score_avg: 0,
  sheets_completed: 0,
  sheets_needs_review: 0,
  total_sheets: 0,
  avg_confidence_score: 0,
  total_sheets_processed: 0,
  sheets_needing_review: 0,
  processing_success_rate: 0,
  sheets_by_status: {},
};

const defaultUserInsights: UserInsights = {
  avg_edit_time: 0,
  avg_session_duration: 0,
  common_edits: [],
  total_edits: 0,
  total_sessions: 0,
  total_sheets: 0,
  avg_edits_per_sheet: 0,
  completion_rate: 0,
  most_edited_fields: {},
};

const defaultSuggestions: ImprovementSuggestion = {
  recommendations: [],
  most_common_issues: [],
};

export const useAnalyticsStore = defineStore("analytics", {
  state: () => ({
    qualityMetrics: { ...defaultQualityMetrics },
    userInsights: { ...defaultUserInsights },
    suggestions: { ...defaultSuggestions },
    loading: false,
    error: null as string | null,
  }),

  actions: {
    async fetchQualityMetrics() {
      this.loading = true;
      this.error = null;

      try {
        const authStore = useAuthStore();
        const response = await axios.get(`${API_URL}/crew-sheets/quality_metrics/`, {
          headers: {
            Authorization: `Bearer ${authStore.accessToken}`,
          },
        });

        this.qualityMetrics = { ...defaultQualityMetrics, ...response.data };
        return response.data;
      } catch (error: any) {
        this.error =
          error.response?.data?.detail || "Failed to fetch quality metrics";
        console.error("Error fetching quality metrics:", error);
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async fetchUserInsights() {
      this.loading = true;
      this.error = null;

      try {
        const authStore = useAuthStore();
        const response = await axios.get(`${API_URL}/crew-sheets/user_insights/`, {
          headers: {
            Authorization: `Bearer ${authStore.accessToken}`,
          },
        });

        this.userInsights = { ...defaultUserInsights, ...response.data };
        return response.data;
      } catch (error: any) {
        this.error =
          error.response?.data?.detail || "Failed to fetch user insights";
        console.error("Error fetching user insights:", error);
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async fetchImprovementSuggestions() {
      this.loading = true;
      this.error = null;

      try {
        const authStore = useAuthStore();
        const response = await axios.get(`${API_URL}/crew-sheets/improvement_suggestions/`, {
          headers: {
            Authorization: `Bearer ${authStore.accessToken}`,
          },
        });

        this.suggestions = { ...defaultSuggestions, ...response.data };
        return response.data;
      } catch (error: any) {
        // Only staff can access suggestions, so handle errors quietly
        if (error.response?.status === 403) {
          console.log("Access to improvement suggestions restricted");
          return defaultSuggestions;
        }

        this.error =
          error.response?.data?.detail || "Failed to fetch improvement suggestions";
        console.error("Error fetching improvement suggestions:", error);
        throw error;
      } finally {
        this.loading = false;
      }
    },

    // Method to fetch all analytics data at once
    async fetchAllAnalytics() {
      this.loading = true;
      this.error = null;

      try {
        await Promise.all([
          this.fetchQualityMetrics(),
          this.fetchUserInsights(),
          this.fetchImprovementSuggestions(),
        ]);
      } catch (error: any) {
        this.error = "Some analytics data could not be loaded";
        console.error("Error fetching analytics data:", error);
      } finally {
        this.loading = false;
      }
    },
  },
});
