<template>
    <div class="crew-sheets-list">
        <div class="header">
            <h1>Crew Sheets</h1>
            <button @click="navigateToUpload" class="btn-primary">
                Upload New Sheet
            </button>
        </div>

        <div v-if="loading" class="loading">
            Loading crew sheets...
        </div>

        <div v-if="error" class="error-message">
            {{ error }}
        </div>

        <div v-if="!loading && crewSheets.length === 0" class="empty-state">
            <p>No crew sheets found. Upload your first crew sheet to get started!</p>
            <button @click="navigateToUpload" class="btn-primary">
                Upload Crew Sheet
            </button>
        </div>

        <div v-if="crewSheets.length > 0" class="crew-sheets-grid">
            <div v-for="sheet in crewSheets" :key="sheet.id" class="crew-sheet-card" @click="viewSheet(sheet.id)">
                <div class="status-indicator" :class="`status-${sheet.status}`"></div>
                <div class="card-content">
                    <h3>{{ sheet.name || `Crew Sheet #${sheet.id}` }}</h3>
                    <div class="card-metadata">
                        <p>Uploaded: {{ formatDate(sheet.date_uploaded) }}</p>
                        <div class="status-badge" :class="`status-${sheet.status}`">
                            {{ sheet.status }}
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div v-if="crewSheets.length > 0" class="list-view">
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Upload Date</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="sheet in crewSheets" :key="sheet.id">
                        <td>{{ sheet.name || `Crew Sheet #${sheet.id}` }}</td>
                        <td>{{ formatDate(sheet.date_uploaded) }}</td>
                        <td>
                            <span class="status-badge" :class="`status-${sheet.status}`">
                                {{ sheet.status }}
                            </span>
                        </td>
                        <td>
                            <button @click.stop="viewSheet(sheet.id)" class="btn-view">View</button>
                            <button v-if="sheet.status === 'pending'" @click.stop="processSheet(sheet.id)"
                                class="btn-process">
                                Process
                            </button>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useCrewSheetStore } from '../stores/crewSheets';
import type { CrewSheet } from '../stores/crewSheets';

const router = useRouter();
const crewSheetStore = useCrewSheetStore();
const loading = ref(true);
const error = ref<string | null>(null);

// Computed property to get crew sheets from store
const crewSheets = ref<CrewSheet[]>([]);

// Load crew sheets when component is mounted
onMounted(async () => {
    try {
        await crewSheetStore.fetchCrewSheets();
        crewSheets.value = crewSheetStore.crewSheets;
    } catch (e) {
        if (e instanceof Error) {
            error.value = e.message;
        } else {
            error.value = 'Error loading crew sheets';
        }
    } finally {
        loading.value = false;
    }
});

// Format date to be more readable
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

// Navigation functions
const navigateToUpload = () => {
    router.push({ name: 'upload' });
};

const viewSheet = (id: number) => {
    router.push({ name: 'crewSheet', params: { id } });
};

const processSheet = async (id: number) => {
    try {
        await crewSheetStore.processCrewSheet(id);
        // Refresh the list after processing
        await crewSheetStore.fetchCrewSheets();
        crewSheets.value = crewSheetStore.crewSheets;
    } catch (e) {
        if (e instanceof Error) {
            error.value = e.message;
        } else {
            error.value = 'Error processing crew sheet';
        }
    }
};
</script>

<style scoped>
.crew-sheets-list {
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

.empty-state {
    text-align: center;
    padding: 3rem;
    background-color: #f9f9f9;
    border-radius: 8px;
}

.btn-primary {
    background-color: #4caf50;
    color: white;
    border: none;
    padding: 0.75rem 1.5rem;
    font-size: 1rem;
    border-radius: 4px;
    cursor: pointer;
}

.btn-view {
    background-color: #007bff;
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    font-size: 0.9rem;
    border-radius: 4px;
    cursor: pointer;
    margin-right: 0.5rem;
}

.btn-process {
    background-color: #4caf50;
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    font-size: 0.9rem;
    border-radius: 4px;
    cursor: pointer;
}

/* Grid layout for card view */
.crew-sheets-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1.5rem;
    margin-bottom: 2rem;
}

.crew-sheet-card {
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    overflow: hidden;
    cursor: pointer;
    transition: transform 0.2s;
    position: relative;
}

.crew-sheet-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.status-indicator {
    height: 5px;
    width: 100%;
}

.card-content {
    padding: 1.5rem;
}

.card-metadata {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 1rem;
}

/* Table layout for list view */
.list-view {
    margin-top: 2rem;
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

tr:hover {
    background-color: #f9f9f9;
}

/* Status styles */
.status-badge {
    padding: 0.25rem 0.5rem;
    border-radius: 20px;
    font-weight: bold;
    text-transform: uppercase;
    font-size: 0.7rem;
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
</style>
