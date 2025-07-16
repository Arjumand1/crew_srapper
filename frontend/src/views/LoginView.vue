<template>
    <div class="login-container">
        <div class="login-form">
            <h1>Login</h1>
            <div v-if="authStore.error" class="error">{{ authStore.error }}</div>

            <form @submit.prevent="handleLogin">
                <div class="form-group">
                    <label for="email">Email</label>
                    <input id="email" v-model="email" type="email" required placeholder="Enter your email" />
                </div>

                <div class="form-group">
                    <label for="password">Password</label>
                    <input id="password" v-model="password" type="password" required
                        placeholder="Enter your password" />
                </div>

                <button type="submit" :disabled="authStore.loading">
                    {{ authStore.loading ? 'Logging in...' : 'Login' }}
                </button>
            </form>

            <div class="register-link">
                Don't have an account? <router-link to="/register">Register</router-link>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const email = ref('')
const password = ref('')

const handleLogin = async () => {
    try {
        const success = await authStore.login(email.value, password.value)
        if (success) {
            router.push('/')
        }
    } catch (error) {
        console.error('Login error:', error)
    }
}
</script>

<style scoped>
.login-container {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 100vh;
    background-color: #f5f5f5;
}

.login-form {
    width: 100%;
    max-width: 400px;
    padding: 2rem;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

h1 {
    margin-bottom: 1.5rem;
    text-align: center;
    color: #2c3e50;
}

.form-group {
    margin-bottom: 1rem;
}

label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
}

input {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 16px;
    transition: border-color 0.2s;
}

input:focus {
    outline: none;
    border-color: #4c84ff;
}

button {
    width: 100%;
    padding: 0.75rem;
    margin-top: 1rem;
    background-color: #4c84ff;
    color: white;
    border: none;
    border-radius: 4px;
    font-size: 16px;
    cursor: pointer;
    transition: background-color 0.2s;
}

button:hover {
    background-color: #3a70e0;
}

button:disabled {
    background-color: #a0a0a0;
    cursor: not-allowed;
}

.error {
    margin-bottom: 1rem;
    padding: 0.5rem;
    background-color: #ffebee;
    color: #d32f2f;
    border-radius: 4px;
    font-size: 14px;
}

.register-link {
    margin-top: 1.5rem;
    text-align: center;
    font-size: 14px;
}

.register-link a {
    color: #4c84ff;
    text-decoration: none;
}

.register-link a:hover {
    text-decoration: underline;
}
</style>
