<template>
  <v-container class="d-flex align-center text-center justify-center fill-height" fluid>
    <v-card class="pa-8 text-center elevation-3 mt-lg-8 mt-sm-6 mt-4 w-lg-50 w-md-75 w-100">
      <v-row class="align-center mb-4">
        <v-col cols="12" md="6" >
          <div class="text-h4 text-sm-left">Crew Sheets</div>
        </v-col>
        <v-col cols="12" md="6" class="d-flex justify-center justify-sm-end">
          <v-btn
            color="primary"
            @click="navigateToUpload"
            class="font-weight-bold"
          >
            Upload New Sheet
          </v-btn>
        </v-col>
      </v-row>

      <v-row class="mb-4">
        <v-col cols="12" class="d-flex justify-center justify-sm-end">
          <v-btn-toggle v-model="viewMode" color="secondary" mandatory>
            <v-btn
              value="grid"
              :variant="viewMode === 'grid' ? 'flat' : 'text'"
            >
              <v-icon icon="mdi-view-grid" /> Grid View
            </v-btn>
            <v-btn
              value="table"
              :variant="viewMode === 'table' ? 'flat' : 'text'"
            >
              <v-icon>mdi-table</v-icon> Table View
            </v-btn>
          </v-btn-toggle>
        </v-col>
      </v-row>

      <v-alert
        v-if="loading"
        type="info"
        class="mb-4"
        border="start"
        variant="tonal"
      >
        Loading crew sheets...
      </v-alert>
      <v-alert
        v-if="error"
        type="error"
        class="mb-4"
        border="start"
        variant="tonal"
      >
        {{ error }}
      </v-alert>

      <v-alert
        v-if="!loading && crewSheets.length === 0"
        type="info"
        class="mb-4"
        border="start"
        variant="tonal"
      >
        No crew sheets found. Upload your first crew sheet to get started!
        <v-btn color="primary" class="ml-4 mt-2" @click="navigateToUpload"
          >Upload Crew Sheet</v-btn
        >
      </v-alert>

      <!-- Grid View -->
      <v-row v-if="crewSheets.length > 0 && viewMode === 'grid'" class="g-4">
        <v-col
          v-for="sheet in crewSheets"
          :key="sheet.id"
          cols="12"
          sm="6"
          md="4"
          lg="3"
        >
          <v-card
            class="d-flex flex-column h-100 elevation-2"
            @click="viewSheet(sheet.id)"
            style="cursor: pointer"
          >
            <div
              :class="[
                'rounded-t',
                'pa-0',
                'overflow-hidden',
                'bg-grey-lighten-3',
              ]"
            >
              <v-img
                :src="sheet.image"
                :alt="sheet.name || `Crew Sheet #${sheet.id}`"
                height="180"
                cover
              />
            </div>
            <v-card-title class="text-h6 mt-2">{{
              sheet.name || `Crew Sheet #${sheet.id}`
            }}</v-card-title>
            <div class="text-caption mx-2"
              >Uploaded: {{ formatDate(sheet.date_uploaded) }}</div
            >
            <v-chip
              :color="statusColor(sheet.status)"
              class="text-uppercase mx-auto my-2"
              size="small"
              >{{ sheet.status }}</v-chip
            >
          </v-card>
        </v-col>
      </v-row>

      <!-- Table View -->
      <v-table
        v-if="crewSheets.length > 0 && viewMode === 'table'"
        class="mt-6 text-left"
        density="comfortable"
        fixed-header
        
      >
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
            <td>
              <v-img
                :src="sheet.image"
                :alt="sheet.name || `Crew Sheet #${sheet.id}`"
                height="60"
                width="60"
                cover
                class="rounded my-2"
              />
            </td>
            <td>{{ sheet.name || `Crew Sheet #${sheet.id}` }}</td>
            <td>{{ formatDate(sheet.date_uploaded) }}</td>
            <td>
              <v-chip
                :color="statusColor(sheet.status)"
                class="text-uppercase"
                size="small"
                >{{ sheet.status }}</v-chip
              >
            </td>
            <td>
              <v-btn
                size="small"
                color="primary"
                @click.stop="viewSheet(sheet.id)"
                >View</v-btn
              >
              <!-- <br>
              <v-btn
                v-if="sheet.status === 'pending'"
                size="small"
                color="success"
                class="mt-1"
                :loading="showButton"
                @click.stop="processSheet(sheet.id)"
                >Process</v-btn
              > -->
            </td>
          </tr>
        </tbody>
      </v-table>
    </v-card>
  </v-container>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useCrewSheetStore } from "../stores/crewSheets";
import type { CrewSheet } from "../stores/crewSheets";

const router = useRouter();
const crewSheetStore = useCrewSheetStore();
const loading = ref(true);
const error = ref<string | null>(null);
const viewMode = ref("grid"); // Default to grid view with images
// const showButton = ref(false)

// Computed property to get crew sheets from store
const crewSheets = ref<CrewSheet[]>([]);

onMounted(async () => {
  try {
    await crewSheetStore.fetchCrewSheets();
    crewSheets.value = crewSheetStore.crewSheets;
  } catch (e) {
    if (e instanceof Error) {
      error.value = e.message;
    } else {
      error.value = "Error loading crew sheets";
    }
  } finally {
    loading.value = false;
  }
});

const formatDate = (dateString: string) => {
  const date = new Date(dateString);
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
};

const statusColor = (status: string) => {
  switch (status) {
    case "pending":
      return "warning";
    case "processing":
      return "info";
    case "completed":
      return "success";
    case "failed":
      return "error";
    default:
      return "default";
  }
};

const navigateToUpload = () => {
  router.push({ name: "upload" });
};

const viewSheet = (id: string) => {
  router.push({ name: "crewSheet", params: { id } });
};

const processSheet = async (id: string) => {
  // showButton.value = true;
  try {
    await crewSheetStore.processCrewSheet(id);
    await crewSheetStore.fetchCrewSheets();
    crewSheets.value = crewSheetStore.crewSheets;
  } catch (e) {
    if (e instanceof Error) {
      error.value = e.message;
    } else {
      error.value = "Error processing crew sheet";
    }
  }
  alert("Processing completed");
  // showButton.value = false;
};
</script>
