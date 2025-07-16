<template>
    <div class="register-container">
        <div class="register-form">
            <h1>Register</h1>
            <div v-if="authStore.error" class="error">{{ authStore.error }}</div>

            <form @submit.prevent="handleRegister">
                <div class="form-group">
                    <label for="email">Email</label>
                    <input id="email" v-model="email" type="email" required placeholder="Enter your email" />
                </div>

                <div class="form-group">
                    <label for="username">Username</label>
                    <input id="username" v-model="username" type="text" required placeholder="Enter your username" />
                </div>

                <div class="form-group">
                    <label for="name">Full Name</label>
                    <input id="name" v-model="name" type="text" required placeholder="Enter your full name" />
                </div>

                <div class="form-group">
                    <label for="password">Password</label>
                    <input id="password" v-model="password" type="password" required
                        placeholder="Enter your password" />
                </div>

                <div class="form-group">
                    <label for="password2">Confirm Password</label>
                    <input id="password2" v-model="password2" type="password" required
                        placeholder="Confirm your password" />
                </div>

                <button type="submit" :disabled="authStore.loading">
                    {{ authStore.loading ? 'Registering...' : 'Register' }}
                </button>
            </form>

            <div class="login-link">
                Already have an account? <router-link to="/login">Login</router-link>
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
const username = ref('')
const name = ref('')
const password = ref('')
const password2 = ref('')

const handleRegister = async () => {
    try {
        const success = await authStore.register(
            email.value,
            username.value,
            name.value,
            password.value,
            password2.value
        )

        if (success) {
            router.push('/')
        }
    } catch (error) {
        console.error('Registration error:', error)
    }
}
</script>

<style scoped>
.register-container {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    padding: 2rem 0;
    background-color: #f5f5f5;
}

.register-form {
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

.login-link {
    margin-top: 1.5rem;
    text-align: center;
    font-size: 14px;
}

.login-link a {
    color: #4c84ff;
    text-decoration: none;
}

.login-link a:hover {
    text-decoration: underline;
}
</style>
