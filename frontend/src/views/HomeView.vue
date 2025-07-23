<template>
  <v-container class="d-flex align-center justify-center fill-height" fluid>
    <v-card class="pa-8 elevation-3 mt-lg-8 mt-sm-6 mt-4 w-lg-50 w-md-75  w-100">
      <div class="text-h4 text-center"
        >Welcome to Crew Scraper</div
      >
      <div v-if="authStore.user" class="mb-8 mt-6">
        <v-card class="mb-6 pa-4" color="grey-lighten-4" flat>
          <div class="text-h6 mb-2">User Information</div>
          <div><strong>Name:</strong> {{ authStore.user.name }}</div>
          <div><strong>Email:</strong> {{ authStore.user.email }}</div>
          <div><strong>Username:</strong> {{ authStore.user.username }}</div>
        </v-card>
      </div>
      <div v-else class="mb-8">
        <v-alert type="info" class="mb-4" border="start" variant="tonal"
          >Loading user information...</v-alert
        >
      </div>
      <v-row class="mb-8" align="stretch" justify="center">
        <v-col cols="12" sm="6" md="4">
          <v-card
            class="pa-6 text-center d-flex flex-column justify-space-between cursor-pointer elevation-2"
            @click="navigateTo('crewSheets')"
          >
            <div>
              <div class="text-h6 mb-2">View Crew Sheets</div>
              <div class="mb-4">
                View and manage all your uploaded crew sheets
              </div>
            </div>
            <div class="text-h5">📋</div>
          </v-card>
        </v-col>
        <v-col cols="12" sm="6" md="4">
          <v-card
            class="pa-6 text-center fill-height d-flex flex-column justify-space-between cursor-pointer elevation-2"
            @click="navigateTo('upload')"
          >
            <div>
              <div class="text-h6 mb-2">Upload New Sheet</div>
              <div class="mb-4">Upload a new crew sheet for AI processing</div>
            </div>
            <div class="text-h5">📎</div>
          </v-card>
        </v-col>
        <v-col cols="12" sm="6" md="4">
          <v-card
            class="pa-6 text-center fill-height d-flex flex-column justify-space-between cursor-pointer elevation-2"
            @click="navigateTo('analytics')"
          >
            <div>
              <div class="text-h6 mb-2">Analytics Dashboard</div>
              <div class="mb-4">View extraction quality metrics and insights</div>
            </div>
            <div class="text-h5">📊</div>
          </v-card>
        </v-col>
      </v-row>
      <v-btn color="error" block class="font-weight-bold" @click="logout"
        >Logout</v-btn
      >
    </v-card>
  </v-container>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";

const router = useRouter();
const authStore = useAuthStore();

onMounted(async () => {
  try {
    if (!authStore.user && authStore.accessToken) {
      await authStore.fetchUser();
    }
  } catch (error) {
    console.error("Failed to fetch user:", error);
  }
});

const navigateTo = (routeName: string) => {
  router.push({ name: routeName });
};

const logout = () => {
  authStore.logout();
  router.push("/login");
};
</script>
