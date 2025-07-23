<template>
    <v-container fluid class="pa-6">
        <v-row class="mb-6">
            <v-col cols="12">
                <div class="d-flex align-center justify-space-between">
                    <div>
                        <h1 class="text-h4 mb-2">Analytics Dashboard</h1>
                        <p class="text-subtitle-1 text-medium-emphasis">
                            Monitor extraction quality and user behavior patterns
                        </p>
                    </div>
                    <v-btn color="primary" @click="fetchData" :loading="loading">
                        <v-icon start>mdi-refresh</v-icon>
                        Refresh Data
                    </v-btn>
                </div>
            </v-col>
        </v-row>

        <!-- Loading State -->
        <v-row v-if="loading" class="justify-center">
            <v-col cols="12" class="text-center">
                <v-progress-circular size="64" indeterminate color="primary"></v-progress-circular>
                <p class="mt-4">Loading analytics data...</p>
            </v-col>
        </v-row>

        <!-- Error State -->
        <v-alert v-if="error" type="error" class="mb-6">
            {{ error }}
        </v-alert>

        <!-- Dashboard Content -->
        <div v-if="!loading && !error">
            <!-- Quality Metrics Row -->
            <v-row class="mb-6">
                <v-col cols="12">
                    <h2 class="text-h5 mb-4">Quality Metrics</h2>
                </v-col>
                <v-col cols="12" md="3">
                    <v-card>
                        <v-card-text class="text-center">
                            <div class="text-h3 mb-2" :class="getConfidenceColor(qualityMetrics.avg_confidence_score)">
                                {{ formatPercentage(qualityMetrics.avg_confidence_score) }}%
                            </div>
                            <div class="text-subtitle-1">Average Confidence</div>
                            <v-progress-linear :model-value="getProgressValue(qualityMetrics.avg_confidence_score)"
                                :color="getConfidenceColor(qualityMetrics.avg_confidence_score)" height="4"
                                class="mt-2"></v-progress-linear>
                        </v-card-text>
                    </v-card>
                </v-col>
                <v-col cols="12" md="3">
                    <v-card>
                        <v-card-text class="text-center">
                            <div class="text-h3 mb-2 text-primary">
                                {{ formatNumber(qualityMetrics.total_sheets_processed) }}
                            </div>
                            <div class="text-subtitle-1">Sheets Processed</div>
                            <div class="text-caption text-medium-emphasis">Last 30 days</div>
                        </v-card-text>
                    </v-card>
                </v-col>
                <v-col cols="12" md="3">
                    <v-card>
                        <v-card-text class="text-center">
                            <div class="text-h3 mb-2"
                                :class="formatNumber(qualityMetrics.sheets_needing_review) > 0 ? 'text-warning' : 'text-success'">
                                {{ formatNumber(qualityMetrics.sheets_needing_review) }}
                            </div>
                            <div class="text-subtitle-1">Need Review</div>
                            <div class="text-caption text-medium-emphasis">
                                {{ getErrorPercentage(qualityMetrics.sheets_needing_review,
                                    qualityMetrics.total_sheets_processed) }}% of total
                            </div>
                        </v-card-text>
                    </v-card>
                </v-col>
                <v-col cols="12" md="3">
                    <v-card>
                        <v-card-text class="text-center">
                            <div class="text-h3 mb-2 text-success">
                                {{ formatPercentage(qualityMetrics.processing_success_rate) }}%
                            </div>
                            <div class="text-subtitle-1">Success Rate</div>
                            <div class="text-caption text-medium-emphasis">Processing completion</div>
                        </v-card-text>
                    </v-card>
                </v-col>
            </v-row>

            <!-- Charts Row -->
            <v-row class="mb-6">
                <v-col cols="12" md="4">
                    <v-card>
                        <v-card-title class="text-h6">
                            Sheet Status Distribution
                        </v-card-title>
                        <v-card-text>
                            <div v-if="qualityMetrics.sheets_by_status">
                                <div v-for="(count, status) in qualityMetrics.sheets_by_status" :key="status"
                                    class="d-flex justify-space-between align-center mb-2">
                                    <div class="d-flex align-center">
                                        <v-chip :color="getStatusColor(status)" size="small" class="mr-2">
                                            {{ status }}
                                        </v-chip>
                                    </div>
                                    <div>{{ count }}</div>
                                </div>
                            </div>
                            <div v-else class="text-center py-4">
                                <p class="text-medium-emphasis">No status data available</p>
                            </div>
                        </v-card-text>
                    </v-card>
                </v-col>

                <v-col cols="12" md="4">
                    <v-card>
                        <v-card-title class="text-h6">
                            User Activity
                        </v-card-title>
                        <v-card-text>
                            <div v-if="userInsights">
                                <div class="text-subtitle-2 mb-2">Your Activity</div>
                                <div class="d-flex justify-space-between">
                                    <span>Total Sheets:</span>
                                    <span class="font-weight-medium">{{ formatNumber(userInsights.total_sheets)
                                    }}</span>
                                </div>
                                <div class="d-flex justify-space-between">
                                    <span>Total Edits:</span>
                                    <span class="font-weight-medium">{{ formatNumber(userInsights.total_edits) }}</span>
                                </div>
                                <div class="d-flex justify-space-between">
                                    <span>Avg Edits/Sheet:</span>
                                    <span class="font-weight-medium">{{ formatNumber(userInsights.avg_edits_per_sheet)
                                    }}</span>
                                </div>
                                <div class="d-flex justify-space-between">
                                    <span>Completion Rate:</span>
                                    <span class="font-weight-medium text-success">{{
                                        formatPercentage(userInsights.completion_rate) }}%</span>
                                </div>
                            </div>
                        </v-card-text>
                    </v-card>
                </v-col>
                <v-col cols="12" md="4">
                    <v-card>
                        <v-card-title class="text-h6">
                            Most Edited Fields
                        </v-card-title>
                        <v-card-text>
                            <v-list density="compact">
                                <v-list-item
                                    v-for="([field, count], index) in Object.entries(userInsights.most_edited_fields || {}).slice(0, 5)"
                                    :key="field">
                                    <v-list-item-title>
                                        <div class="d-flex justify-space-between align-center">
                                            <div>{{ field }}</div>
                                            <div class="text-medium-emphasis">{{ count }}</div>
                                        </div>
                                    </v-list-item-title>
                                </v-list-item>
                            </v-list>
                        </v-card-text>
                    </v-card>
                </v-col>
            </v-row>

            <!-- Most Edited Fields -->
            <v-row class="mb-6">
                <v-col cols="12" md="6">
                    <v-card>
                        <v-card-title>
                            <v-icon start>mdi-pencil</v-icon>
                            Most Frequently Edited Fields
                        </v-card-title>
                        <v-card-text>
                            <v-list density="compact">
                                <v-list-item
                                    v-for="([field, count], index) in Object.entries(userInsights.most_edited_fields || {}).slice(0, 5)"
                                    :key="field">
                                    <v-list-item-title>
                                        <div class="d-flex justify-space-between align-center">
                                            <span>{{ formatFieldName(field) }}</span>
                                            <v-chip size="small" color="warning">{{ formatNumber(count) }}</v-chip>
                                        </div>
                                    </v-list-item-title>
                                </v-list-item>
                            </v-list>
                        </v-card-text>
                    </v-card>
                </v-col>
                <v-col cols="12" md="6">
                    <v-card>
                        <v-card-title>
                            <v-icon start>mdi-lightbulb</v-icon>
                            Improvement Suggestions
                        </v-card-title>
                        <v-card-text>
                            <v-list density="compact" v-if="suggestions.recommendations?.length">
                                <v-list-item v-for="(recommendation, index) in suggestions.recommendations"
                                    :key="index">
                                    <v-list-item-title>
                                        <div class="d-flex align-start">
                                            <v-icon :color="recommendation.priority === 'high' ? 'error' : 'info'"
                                                class="me-2">
                                                mdi-lightbulb
                                            </v-icon>
                                            <div>{{ recommendation.description }}</div>
                                        </div>
                                    </v-list-item-title>
                                </v-list-item>
                            </v-list>
                            <div v-else class="text-center text-medium-emphasis">
                                <v-icon size="large" class="mb-2">mdi-check-circle</v-icon>
                                <p>System is performing well!</p>
                            </div>
                        </v-card-text>
                    </v-card>
                </v-col>
            </v-row>

            <!-- Common Issues -->
            <v-row v-if="suggestions.most_common_issues?.length" class="mb-6">
                <v-col cols="12">
                    <v-card>
                        <v-card-title>
                            <v-icon start>mdi-alert-circle</v-icon>
                            Common Extraction Issues
                        </v-card-title>
                        <v-card-text>
                            <v-chip-group>
                                <v-chip v-for="[issue, count] in suggestions.most_common_issues.slice(0, 10)"
                                    :key="issue" color="warning" variant="outlined">
                                    {{ issue }} ({{ formatNumber(count) }})
                                </v-chip>
                            </v-chip-group>
                        </v-card-text>
                    </v-card>
                </v-col>
            </v-row>
        </div>
    </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, onUnmounted, nextTick } from 'vue';
import { useRouter } from 'vue-router';
import { useAnalyticsStore } from '../stores/analytics';

// Initialize store and router
const analyticsStore = useAnalyticsStore();
const router = useRouter();

// Local state management
const localLoading = ref(false);
const localError = ref<string | null>(null);

// Use local state with fallback to store state
const loading = computed(() => localLoading.value || analyticsStore.loading);
const error = computed(() => localError.value || analyticsStore.error);

// Computed properties for store data
const qualityMetrics = computed(() => analyticsStore.qualityMetrics);
const userInsights = computed(() => analyticsStore.userInsights);
const suggestions = computed(() => analyticsStore.suggestions);

// Flag to prevent navigation issues
const isComponentMounted = ref(true);

// Helper functions
const getConfidenceColor = (score: number) => {
    if (score >= 0.85) return 'text-success';
    if (score >= 0.7) return 'text-info';
    if (score >= 0.5) return 'text-warning';
    return 'text-error';
};

const getStatusColor = (status: string) => {
    const statusMap: Record<string, string> = {
        'completed': 'success',
        'processing': 'info',
        'pending': 'warning',
        'failed': 'error'
    };
    return statusMap[status.toLowerCase()] || 'primary';
};

const formatNumber = (value: any): string => {
    if (value === null || value === undefined) return '0';
    if (typeof value === 'string') {
        value = parseInt(value);
    }
    if (isNaN(value)) return '0';
    return value.toString();
};

const formatPercentage = (value: any): string => {
    if (value === null || value === undefined) return '0.0';
    if (typeof value === 'string') {
        value = parseFloat(value);
    }
    if (isNaN(value)) return '0.0';
    return (value * 100).toFixed(1);
};

const getErrorPercentage = (needsReview: any, totalSheets: any) => {
    const nr = parseInt(needsReview?.toString() || '0');
    const ts = parseInt(totalSheets?.toString() || '0');
    
    if (ts === 0) return '0.0';
    return ((nr / ts) * 100).toFixed(1);
};

const getProgressValue = (value: any) => {
    if (value === null || value === undefined || isNaN(value)) return 0;
    return value * 100;
};

// Format a field name for display
const formatFieldName = (field: string): string => {
    return field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
};

// Data fetching with error handling
const fetchData = async () => {
    if (!isComponentMounted.value) return;
    
    localLoading.value = true;
    localError.value = null;
    
    try {
        await analyticsStore.fetchAllAnalytics();
        console.log('Analytics data loaded successfully');
    } catch (e: any) {
        console.error('Error fetching analytics data:', e);
        localError.value = e?.message || 'Failed to load analytics data';
    } finally {
        if (isComponentMounted.value) {
            localLoading.value = false;
        }
    }
};

// Clean up function to prevent state updates after component is unmounted
onUnmounted(() => {
    isComponentMounted.value = false;
});

// Initial data fetch with delayed execution to prevent blocking
onMounted(() => {
    // Use nextTick to ensure the component is fully mounted before fetching data
    nextTick(() => {
        if (isComponentMounted.value) {
            fetchData();
        }
    });
});
</script>

<style scoped>
.text-h3 {
    font-weight: 600;
}

.v-card {
    transition: all 0.3s ease;
}

.v-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}
</style>