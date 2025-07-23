<template>
  <div>
    <v-app-bar color="primary" class="elevation-2 px-4 px-md-12" dark flat app>
      <!-- Hamburger menu button: only on sm and down -->
      <v-btn icon class="me-2 d-flex d-sm-none" @click="drawer = true">
        <v-icon>mdi-menu</v-icon>
      </v-btn>
      <!-- App title with direct navigation -->
      <a @click="navigateTo('home')" class="text-md-h4 text-h5 font-weight-bold text-white text-decoration-none cursor-pointer">
        Crew Scraper
      </a>
      
      <!-- Right nav links: only on md and up -->
      <div class="d-none d-sm-flex align-center ms-auto" style="gap: 1.5rem;">
        <template v-if="authStore.isAuthenticated">
          <a @click="navigateTo('home')" class="text-body-1 text-grey-lighten-3 text-decoration-none cursor-pointer">
            Home
          </a>
          <a @click="navigateTo('crewSheets')" class="text-body-1 text-grey-lighten-3 text-decoration-none cursor-pointer">
            Crew Sheets
          </a>
          <a @click="navigateTo('upload')" class="text-body-1 text-grey-lighten-3 text-decoration-none cursor-pointer">
            Upload
          </a>
          <a @click="navigateTo('analytics')" class="text-body-1 text-grey-lighten-3 text-decoration-none cursor-pointer">
            <v-icon size="small" class="mr-1">mdi-chart-line</v-icon>
            Analytics
          </a>
          <v-btn @click="logout" color="error" variant="outlined" size="small" class="text-body-1 bg-white">
            Logout
          </v-btn>
        </template>
        <template v-else>
          <a @click="navigateTo('login')" class="text-body-1 text-grey-lighten-3 text-decoration-none cursor-pointer">
            Login
          </a>
          <a @click="navigateTo('register')" class="text-body-1 text-grey-lighten-3 text-decoration-none cursor-pointer">
            Register
          </a>
        </template>
      </div>
    </v-app-bar>

    <v-navigation-drawer v-model="drawer" app temporary width="240" class="d-flex d-md-none">
      <v-list nav>
        <v-list-item>
          <v-list-item-title class="font-weight-bold">Menu</v-list-item-title>
        </v-list-item>
        <v-divider class="mb-2" />
        <template v-if="authStore.isAuthenticated">
          <v-list-item @click="navigateTo('home')">
            <v-list-item-title>Home</v-list-item-title>
          </v-list-item>
          <v-list-item @click="navigateTo('crewSheets')">
            <v-list-item-title>Crew Sheets</v-list-item-title>
          </v-list-item>
          <v-list-item @click="navigateTo('upload')">
            <v-list-item-title>Upload</v-list-item-title>
          </v-list-item>
          <v-list-item @click="navigateTo('analytics')">
            <v-list-item-title>
              <v-icon size="small" class="mr-2">mdi-chart-line</v-icon>
              Analytics
            </v-list-item-title>
          </v-list-item>
          <v-list-item @click="logout">
            <v-list-item-title class="text-error">Logout</v-list-item-title>
          </v-list-item>
        </template>
        <template v-else>
          <v-list-item @click="navigateTo('login')">
            <v-list-item-title>Login</v-list-item-title>
          </v-list-item>
          <v-list-item @click="navigateTo('register')">
            <v-list-item-title>Register</v-list-item-title>
          </v-list-item>
        </template>
      </v-list>
    </v-navigation-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';

const router = useRouter();
const authStore = useAuthStore();
const drawer = ref(false);

const logout = () => {
  drawer.value = false;
  authStore.logout();
  router.push({ name: 'login' });
};

// Direct navigation handler with forced re-route
const navigateTo = (name: string) => {
  drawer.value = false;
  
  // When coming from analytics or going to analytics, use window.location for hard navigation
  const currentRoute = router.currentRoute.value;
  if (currentRoute.name === 'analytics' || name === 'analytics') {
    // Force hard navigation for analytics routes
    const path = name === 'home' ? '/' : `/${name === 'crewSheets' ? 'crew-sheets' : name}`;
    window.location.href = path;
  } else {
    // Use router for normal navigation
    router.push({ name });
  }
};
</script>

<style scoped>
.cursor-pointer {
  cursor: pointer;
}
</style>
