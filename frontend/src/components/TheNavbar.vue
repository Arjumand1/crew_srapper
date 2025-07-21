<template>
  <nav class="w-100 bg-primary">
    <div class="d-flex justify-space-between w-100 px-4">
      <router-link :to="{ name: 'home' }" class="text-md-h4 text-h5 font-weight-bold my-6 text-white text-decoration-none">
        Crew Scraper
      </router-link>

      <div v-if="authStore.isAuthenticated" class="d-flex align-center" style="gap: 1.5rem;">
        <router-link :to="{ name: 'crewSheets' }" class="text-body-1 text-grey-lighten-3 text-decoration-none">
          Crew Sheets
        </router-link>
        <router-link :to="{ name: 'upload' }" class="text-body-1 text-grey-lighten-3 text-decoration-none">
          Upload
        </router-link>
        <button
          @click="logout"
          class="bg-transparent text-grey-lighten-3 border rounded px-4 py-2 text-body-1"
          style="border-color: #ecf0f1; transition: all 0.2s;"
          @mouseover="(e) => { e.target.style.backgroundColor = '#e74c3c'; e.target.style.color = 'white'; e.target.style.borderColor = '#e74c3c'; }"
          @mouseleave="(e) => { e.target.style.backgroundColor = 'transparent'; e.target.style.color = '#ecf0f1'; e.target.style.borderColor = '#ecf0f1'; }"
        >
          Logout
        </button>
      </div>

      <div v-else class="d-flex align-center" style="gap: 1.5rem;">
        <router-link :to="{ name: 'login' }" class="text-body-1 text-grey-lighten-3 text-decoration-none">
          Login
        </router-link>
        <router-link :to="{ name: 'register' }" class="text-body-1 text-grey-lighten-3 text-decoration-none">
          Register
        </router-link>
      </div>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';

const router = useRouter();
const authStore = useAuthStore();

const logout = () => {
    authStore.logout();
    router.push({ name: 'login' });
};
</script>
