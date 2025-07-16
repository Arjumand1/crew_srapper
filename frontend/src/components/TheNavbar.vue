<template>
    <nav class="navbar">
        <div class="container">
            <router-link :to="{ name: 'home' }" class="logo">
                Crew Scraper
            </router-link>

            <div v-if="authStore.isAuthenticated" class="nav-links">
                <router-link :to="{ name: 'crewSheets' }" class="nav-link">
                    Crew Sheets
                </router-link>
                <router-link :to="{ name: 'upload' }" class="nav-link">
                    Upload
                </router-link>
                <button @click="logout" class="logout-button">
                    Logout
                </button>
            </div>

            <div v-else class="nav-links">
                <router-link :to="{ name: 'login' }" class="nav-link">
                    Login
                </router-link>
                <router-link :to="{ name: 'register' }" class="nav-link">
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

<style scoped>
.navbar {
    background-color: #2c3e50;
    color: white;
    padding: 1rem 0;
}

.container {
    display: flex;
    justify-content: space-between;
    align-items: center;
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 1rem;
}

.logo {
    font-size: 1.5rem;
    font-weight: bold;
    color: white;
    text-decoration: none;
}

.nav-links {
    display: flex;
    align-items: center;
    gap: 1.5rem;
}

.nav-link {
    color: #ecf0f1;
    text-decoration: none;
    font-size: 1rem;
    transition: color 0.2s;
}

.nav-link:hover,
.nav-link.router-link-active {
    color: #3498db;
}

.logout-button {
    background-color: transparent;
    color: #ecf0f1;
    border: 1px solid #ecf0f1;
    border-radius: 4px;
    padding: 0.4rem 1rem;
    font-size: 1rem;
    cursor: pointer;
    transition: all 0.2s;
}

.logout-button:hover {
    background-color: #e74c3c;
    color: white;
    border-color: #e74c3c;
}
</style>
