<template>
    <div class="crew-sheet-detail">
        <div class="header">
            <h1>{{ currentSheet?.name || 'Crew Sheet Details' }}</h1>
            <div class="status-badge" :class="statusClass">
                {{ currentSheet?.status }}
            </div>
        </div>

        <div v-if="loading" class="loading">
            Loading crew sheet data...
        </div>

        <div v-if="error" class="error-message">
            {{ error }}
        </div>

        <div v-if="currentSheet && !loading" class="crew-sheet-container">
            <!-- Image and Metadata -->
            <div class="sheet-section">
                <h2>Original Image</h2>
                <div class="image-container">
                    <img :src="currentSheet.image" alt="Crew Sheet" />
                </div>
                <div class="metadata">
                    <p><strong>Uploaded:</strong> {{ formatDate(currentSheet.date_uploaded) }}</p>
                    <p v-if="currentSheet.date_processed"><strong>Processed:</strong> {{
                        formatDate(currentSheet.date_processed) }}</p>
                </div>
            </div>

            <!-- Actions -->
            <div class="actions">
                <button v-if="currentSheet.status === 'pending'" @click="processCrewSheet" class="btn-process"
                    :disabled="processing">
                    {{ processing ? 'Starting Process...' : 'Process Sheet' }}
                </button>

                <button @click="goBack" class="btn-secondary">
                    Back to List
                </button>
            </div>

            <!-- Processing Error -->
            <div v-if="currentSheet.status === 'failed'" class="error-container">
                <h3>Processing Error</h3>
                <p>{{ currentSheet.error_message }}</p>
                <button @click="processCrewSheet" class="btn-retry" :disabled="processing">
                    {{ processing ? 'Retrying...' : 'Retry Processing' }}
                </button>
            </div>

            <!-- Extracted Data -->
            <div v-if="currentSheet.status === 'completed' && currentSheet.extracted_data" class="extracted-data">
                <h2>Extracted Data</h2>

                <!-- Header Info -->
                <div v-if="headerInfo" class="header-info">
                    <h3>Sheet Information</h3>
                    <div class="info-grid">
                        <div v-for="(value, key) in headerInfo" :key="key" class="info-item">
                            <span class="info-label">{{ formatLabel(key) }}:</span>
                            <span class="info-value">{{ value }}</span>
                        </div>
                    </div>
                </div>

                <!-- Employee Data Table -->
                <div v-if="employees && employees.length" class="employee-table">
                    <h3>Employee Data</h3>
                    <table>
                        <thead>
                            <tr>
                                <th v-for="header in tableHeaders" :key="header">{{ formatLabel(header) }}</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="(employee, index) in employees" :key="index">
                                <td v-for="header in tableHeaders" :key="`${index}-${header}`">
                                    <span :class="{ 'uncertain': isUncertain(employee, header) }">
                                        {{ getEmployeeValue(employee, header) }}
                                    </span>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>

                <!-- Summary Data -->
                <div v-if="summaryInfo" class="summary-info">
                    <h3>Summary</h3>
                    <div class="info-grid">
                        <div v-for="(value, key) in summaryInfo" :key="key" class="info-item">
                            <span class="info-label">{{ formatLabel(key) }}:</span>
                            <span class="info-value">{{ value }}</span>
                        </div>
                    </div>
                </div>

                <!-- Raw JSON -->
                <div class="raw-json">
                    <details>
                        <summary>View Raw JSON Data</summary>
                        <pre>{{ JSON.stringify(currentSheet.extracted_data, null, 2) }}</pre>
                    </details>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useCrewSheetStore } from '../stores/crewSheets';
import type { CrewSheet } from '../stores/crewSheets';

const route = useRoute();
const router = useRouter();
const crewSheetStore = useCrewSheetStore();

const loading = ref(true);
const processing = ref(false);
const error = ref<string | null>(null);
const sheetId = computed(() => route.params.id as string);

const currentSheet = computed<CrewSheet | null>(() => crewSheetStore.currentCrewSheet);

const statusClass = computed(() => {
    if (!currentSheet.value) return '';
    return `status-${currentSheet.value.status}`;
});

// Extracted data computed properties
const headerInfo = computed(() => {
    if (!currentSheet.value?.extracted_data) return null;
    const data = currentSheet.value.extracted_data;

    // Filter out employee/table data and summary data
    const headerFields = Object.entries(data).filter(([key, value]) => {
        return key !== 'valid' &&
            key !== 'employees' &&
            key !== 'summary' &&
            key !== 'table_headers' &&
            typeof value !== 'object';
    });

    return Object.fromEntries(headerFields);
});

const employees = computed(() => {
    if (!currentSheet.value?.extracted_data) return [];
    return currentSheet.value.extracted_data.employees || [];
});

const summaryInfo = computed(() => {
    if (!currentSheet.value?.extracted_data?.summary) return null;
    return currentSheet.value.extracted_data.summary;
});

const tableHeaders = computed(() => {
    if (currentSheet.value?.extracted_data?.table_headers) {
        return currentSheet.value.extracted_data.table_headers;
    }

    // If no explicit headers, derive from employee data
    if (employees.value && employees.value.length > 0) {
        const allKeys = new Set<string>();
        employees.value.forEach(emp => {
            Object.keys(emp).forEach(key => allKeys.add(key));
        });
        return Array.from(allKeys);
    }

    return [];
});

onMounted(async () => {
    try {
        await crewSheetStore.fetchCrewSheet(sheetId.value);
    } catch (e) {
        if (e instanceof Error) {
            error.value = e.message;
        } else {
            error.value = 'Error loading crew sheet';
        }
    } finally {
        loading.value = false;
    }
});

// Methods
const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }).format(date);
};

const formatLabel = (key: string) => {
    return key
        .replace(/_/g, ' ')
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
};

const isUncertain = (employee: any, field: string) => {
    return employee[field]?.uncertain === true;
};

const getEmployeeValue = (employee: any, field: string) => {
    const value = employee[field];
    if (value === null || value === undefined) return '';
    if (typeof value === 'object' && 'value' in value) {
        return value.value;
    }
    return value;
};

const processCrewSheet = async () => {
    processing.value = true;
    try {
        await crewSheetStore.processCrewSheet(sheetId.value);
        // Refresh data after processing is initiated
        await crewSheetStore.fetchCrewSheet(sheetId.value);
    } catch (e) {
        if (e instanceof Error) {
            error.value = e.message;
        } else {
            error.value = 'Error processing crew sheet';
        }
    } finally {
        processing.value = false;
    }
};

const goBack = () => {
    router.push({ name: 'crewSheets' });
};
</script>

<style scoped>
.crew-sheet-detail {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
}

.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2rem;
}

.status-badge {
    padding: 0.5rem 1rem;
    border-radius: 20px;
    font-weight: bold;
    text-transform: uppercase;
    font-size: 0.8rem;
}

.status-pending {
    background-color: #fff3cd;
    color: #856404;
}

.status-processing {
    background-color: #cce5ff;
    color: #004085;
}

.status-completed {
    background-color: #d4edda;
    color: #155724;
}

.status-failed {
    background-color: #f8d7da;
    color: #721c24;
}

.loading {
    text-align: center;
    padding: 2rem;
    font-size: 1.2rem;
    color: #666;
}

.error-message {
    background-color: #f8d7da;
    color: #721c24;
    padding: 1rem;
    border-radius: 4px;
    margin-bottom: 1rem;
}

.crew-sheet-container {
    display: flex;
    flex-direction: column;
    gap: 2rem;
}

.sheet-section {
    margin-bottom: 1rem;
}

.image-container {
    background-color: #f8f9fa;
    padding: 1rem;
    border-radius: 8px;
    text-align: center;
}

.image-container img {
    max-width: 100%;
    max-height: 600px;
    object-fit: contain;
}

.metadata {
    display: flex;
    gap: 2rem;
    margin-top: 1rem;
}

.actions {
    display: flex;
    gap: 1rem;
    margin: 1rem 0;
}

.btn-process {
    background-color: #4caf50;
    color: white;
    border: none;
    padding: 0.75rem 1.5rem;
    font-size: 1rem;
    border-radius: 4px;
    cursor: pointer;
}

.btn-process:disabled {
    background-color: #a5d6a7;
    cursor: not-allowed;
}

.btn-secondary {
    background-color: #6c757d;
    color: white;
    border: none;
    padding: 0.75rem 1.5rem;
    font-size: 1rem;
    border-radius: 4px;
    cursor: pointer;
}

.error-container {
    background-color: #f8d7da;
    padding: 1rem;
    border-radius: 8px;
    margin: 1rem 0;
}

.extracted-data {
    background-color: #f9f9f9;
    padding: 2rem;
    border-radius: 8px;
    margin-top: 2rem;
}

.header-info,
.summary-info {
    margin-bottom: 2rem;
}

.info-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1rem;
}

.info-item {
    display: flex;
    gap: 0.5rem;
}

.info-label {
    font-weight: bold;
}

.employee-table {
    margin: 2rem 0;
    overflow-x: auto;
}

table {
    width: 100%;
    border-collapse: collapse;
}

th,
td {
    border: 1px solid #ddd;
    padding: 0.75rem;
    text-align: left;
}

th {
    background-color: #f2f2f2;
    font-weight: bold;
}

tr:nth-child(even) {
    background-color: #f9f9f9;
}

.uncertain {
    color: #d32f2f;
    font-style: italic;
    position: relative;
}

.uncertain::after {
    content: "*";
    color: #d32f2f;
    font-weight: bold;
    margin-left: 2px;
}

.raw-json {
    margin-top: 2rem;
    border-top: 1px solid #ddd;
    padding-top: 2rem;
}

.raw-json summary {
    cursor: pointer;
    color: #007bff;
    font-weight: bold;
    margin-bottom: 1rem;
}

.raw-json pre {
    background-color: #f8f9fa;
    padding: 1rem;
    border-radius: 4px;
    overflow-x: auto;
    font-size: 0.9rem;
}

.btn-retry {
    background-color: #4caf50;
    color: white;
    border: none;
    padding: 0.75rem 1.5rem;
    font-size: 1rem;
    border-radius: 4px;
    cursor: pointer;
}

.btn-retry:disabled {
    background-color: #a5d6a7;
    cursor: not-allowed;
}
</style>
