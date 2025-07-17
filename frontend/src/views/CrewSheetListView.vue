<template>
    <div class="crew-sheets-list">
        <div class="header">
            <h1>Crew Sheets</h1>
            <button @click="navigateToUpload" class="btn-primary">
                Upload New Sheet
            </button>
        </div>

        <div class="view-toggle">
            <button @click="viewMode = 'grid'" :class="{ active: viewMode === 'grid' }" class="toggle-btn">
                <i class="fas fa-th-large"></i> Grid View
            </button>
            <button @click="viewMode = 'table'" :class="{ active: viewMode === 'table' }" class="toggle-btn">
                <i class="fas fa-list"></i> Table View
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

        <!-- Grid View with Image Thumbnails -->
        <div v-if="crewSheets.length > 0 && viewMode === 'grid'" class="crew-sheets-grid">
            <div v-for="sheet in crewSheets" :key="sheet.id" class="crew-sheet-card" @click="viewSheet(sheet.id)">
                <div class="status-indicator" :class="`status-${sheet.status}`"></div>

                <!-- Image Thumbnail -->
                <div class="card-image">
                    <img :src="sheet.image" :alt="sheet.name || `Crew Sheet #${sheet.id}`" />
                </div>

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

        <!-- Table View with Image Thumbnails -->
        <div v-if="crewSheets.length > 0 && viewMode === 'table'" class="list-view">
            <table>
                <thead>
                    <tr>
                        <th>Image</th>
                        <th>Name</th>
                        <th>Upload Date</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="sheet in crewSheets" :key="sheet.id">
                        <td class="thumbnail-cell">
                            <div class="image-container">
                                <img :src="sheet.image" :alt="sheet.name || `Crew Sheet #${sheet.id}`" class="table-thumbnail" />
                            </div>
                        </td>
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
const viewMode = ref('grid'); // Default to grid view with images

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

const viewSheet = (id: string) => {
    router.push({ name: 'crewSheet', params: { id } });
};

const processSheet = async (id: string) => {
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
    margin-bottom: 1rem;
}

.view-toggle {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 1.5rem;
}

.toggle-btn {
    background-color: #f5f5f5;
    border: 1px solid #ddd;
    padding: 0.5rem 1rem;
    margin-left: 0.5rem;
    border-radius: 4px;
    cursor: pointer;
}

.toggle-btn.active {
    background-color: #e0e0e0;
    font-weight: bold;
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
    height: 350px;
    display: flex;
    flex-direction: column;
}

.crew-sheet-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.status-indicator {
    height: 5px;
    width: 100%;
}

/* Card Image Thumbnail Styles */
.card-image {
    width: 100%;
    height: 200px;
    overflow: hidden;
    background-color: #f5f5f5;
    display: flex;
    align-items: center;
    justify-content: center;
}

.card-image img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.card-content {
    padding: 1.5rem;
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
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

/* Table Image Thumbnail Styles */
.thumbnail-cell {
    width: 100px;
    height: 80px;
    padding: 0.25rem;
}

.image-container {
    width: 100%;
    height: 100%;
    display: flex;
    justify-content: center;
    align-items: center;
    background-color: #f5f5f5;
    border-radius: 4px;
    padding: 2px;
    box-shadow: inset 0 0 2px rgba(0, 0, 0, 0.1);
}

.table-thumbnail {
    width: 80px;
    height: 80px;
    object-fit: contain;
    border-radius: 2px;
}

.thumbnail-cell {
    width: 100px;
    vertical-align: middle;
    padding: 8px;
}

/* Dark mode compatibility */
@media (prefers-color-scheme: dark) {
    .image-container {
        background-color: #333;
        box-shadow: inset 0 0 2px rgba(255, 255, 255, 0.1);
    }
    
    table.data-table {
        background-color: #222;
        color: #eee;
        border-color: #444;
    }
    
    table.data-table thead th {
        background-color: #333;
        color: #fff;
        border-color: #444;
    }
    
    table.data-table td {
        border-color: #444;
    }
    
    table.data-table tbody tr:nth-child(even) {
        background-color: #2a2a2a;
    }
    
    table.data-table tbody tr:hover {
        background-color: #444;
    }
    
    .status-badge {
        border: 1px solid #444;
    }
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
