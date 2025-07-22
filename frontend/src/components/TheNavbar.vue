<template>
  <div>
    <v-app-bar color="primary" class="elevation-2 px-4" dark flat app>
      <!-- Hamburger menu button: only on sm and down -->
      <v-btn icon class="me-2 d-flex d-sm-none" @click="drawer = true">
        <v-icon>mdi-menu</v-icon>
      </v-btn>
      <router-link :to="{ name: 'home' }" class="text-md-h4 text-h5 font-weight-bold text-white text-decoration-none">
        Crew Scraper
      </router-link>
      <!-- Right nav links: only on md and up -->
      <div class="d-none d-sm-flex align-center ms-auto" style="gap: 1.5rem;">
        <template v-if="authStore.isAuthenticated">
          <router-link :to="{ name: 'home' }" class="text-body-1 text-grey-lighten-3 text-decoration-none">
            Home
          </router-link>
          <router-link :to="{ name: 'crewSheets' }" class="text-body-1 text-grey-lighten-3 text-decoration-none">
            Crew Sheets
          </router-link>
          <router-link :to="{ name: 'upload' }" class="text-body-1 text-grey-lighten-3 text-decoration-none">
            Upload
          </router-link>
          <v-btn @click="logout" color="error" variant="outlined" size="small" class="text-body-1 bg-white">
            Logout
          </v-btn>
        </template>
        <template v-else>
          <router-link :to="{ name: 'login' }" class="text-body-1 text-grey-lighten-3 text-decoration-none">
            Login
          </router-link>
          <router-link :to="{ name: 'register' }" class="text-body-1 text-grey-lighten-3 text-decoration-none">
            Register
          </router-link>
        </template>
      </div>
    </v-app-bar>

    <v-navigation-drawer
      v-model="drawer"
      app
      temporary
      width="240"
      class="d-flex d-md-none"
    >
      <v-list nav>
        <v-list-item>
          <v-list-item-title class="font-weight-bold">Menu</v-list-item-title>
        </v-list-item>
        <v-divider class="mb-2" />
        <template v-if="authStore.isAuthenticated">
          <v-list-item @click="goTo('home')">
            <v-list-item-title>Home</v-list-item-title>
          </v-list-item>
          <v-list-item @click="goTo('crewSheets')">
            <v-list-item-title>Crew Sheets</v-list-item-title>
          </v-list-item>
          <v-list-item @click="goTo('upload')">
            <v-list-item-title>Upload</v-list-item-title>
          </v-list-item>
          <v-list-item @click="logout">
            <v-list-item-title class="text-error">Logout</v-list-item-title>
          </v-list-item>
        </template>
        <template v-else>
          <v-list-item @click="goTo('login')">
            <v-list-item-title>Login</v-list-item-title>
          </v-list-item>
          <v-list-item @click="goTo('register')">
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

function goTo(name: string) {
  drawer.value = false;
  router.push({ name });
}
</script>
