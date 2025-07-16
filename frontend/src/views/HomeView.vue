<template>
    <div class="home-container">
        <div class="home-content">
            <h1>Welcome to Crew Scraper</h1>

            <div v-if="authStore.user" class="user-info">
                <h2>User Information</h2>
                <p><strong>Name:</strong> {{ authStore.user.name }}</p>
                <p><strong>Email:</strong> {{ authStore.user.email }}</p>
                <p><strong>Username:</strong> {{ authStore.user.username }}</p>
            </div>
            <div v-else class="loading">
                <p>Loading user information...</p>
            </div>

            <div class="action-cards">
                <div class="card" @click="navigateTo('crewSheets')">
                    <h3>View Crew Sheets</h3>
                    <p>View and manage all your uploaded crew sheets</p>
                    <div class="icon">📋</div>
                </div>

                <div class="card" @click="navigateTo('upload')">
                    <h3>Upload New Sheet</h3>
                    <p>Upload a new crew sheet for AI processing</p>
                    <div class="icon">📎</div>
                </div>
            </div>

            <button @click="logout" class="logout-button">Logout</button>
        </div>
    </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

onMounted(async () => {
    try {
        if (!authStore.user && authStore.accessToken) {
            await authStore.fetchUser()
        }
    } catch (error) {
        console.error('Failed to fetch user:', error)
    }
})

const navigateTo = (routeName: string) => {
    router.push({ name: routeName })
}

const logout = () => {
    authStore.logout()
    router.push('/login')
}
</script>

<style scoped>
.home-container {
    display: flex;
    justify-content: center;
    padding: 2rem;
    min-height: 100vh;
    background-color: #f5f5f5;
}

.home-content {
    width: 100%;
    max-width: 800px;
    padding: 2rem;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

h1 {
    margin-bottom: 2rem;
    color: #2c3e50;
    text-align: center;
}

h2 {
    margin: 1.5rem 0 1rem;
    color: #2c3e50;
}

.user-info {
    margin: 2rem 0;
    padding: 1rem;
    background-color: #f8f9fa;
    border-radius: 8px;
    border-left: 4px solid #4c84ff;
}

.user-info p {
    margin: 0.5rem 0;
}

.loading {
    margin: 2rem 0;
    text-align: center;
    color: #666;
}

.action-cards {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5rem;
    margin: 2rem 0;
}

.card {
    padding: 1.5rem;
    background-color: #f8f9fa;
    border-radius: 8px;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
    cursor: pointer;
    transition: transform 0.2s, box-shadow 0.2s;
    text-align: center;
    position: relative;
    overflow: hidden;
}

.card:hover {
    transform: translateY(-5px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.card h3 {
    margin-top: 0;
    color: #2c3e50;
    font-size: 1.25rem;
}

.card p {
    color: #666;
    margin-bottom: 2.5rem;
}

.card .icon {
    position: absolute;
    bottom: 1rem;
    left: 0;
    right: 0;
    font-size: 1.5rem;
}

.logout-button {
    padding: 0.75rem 1.5rem;
    background-color: #e53935;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 1rem;
    margin-top: 1rem;
    width: 100%;
}

.logout-button:hover {
    background-color: #c62828;
}
</style>
