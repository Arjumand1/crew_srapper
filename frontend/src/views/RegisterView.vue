<template>
  <v-container class="d-flex align-center justify-center fill-height" fluid>
    <v-card elevation="4" class="pa-6 mt-md-6 mt-4 w-lg-25 w-md-50 w-sm-75 w-100">
      <v-card-title class="text-h4 font-weight-bold text-center">Register</v-card-title>
      <v-alert v-if="authStore.error" type="error" class="mb-4" dense>{{ authStore.error }}</v-alert>
      <v-form ref="formRef" @submit.prevent="handleRegister">
        <v-text-field
          v-model="name"
          label="Full Name"
          type="text"
          required
          placeholder="Enter your full name"
          class="mb-4 mt-8"
          autocomplete="name"
          :rules="[v => !!v || 'Full name is required']"
          :disabled="authStore.loading"
        />
        <v-text-field
          v-model="email"
          label="Email"
          type="email"
          required
          placeholder="Enter your email"
          class="mb-4"
          autocomplete="email"
          :rules="[v => !!v || 'Email is required', v => /.+@.+\..+/.test(v) || 'E-mail must be valid']"
          :disabled="authStore.loading"
        />
        <v-text-field
          v-model="password"
          label="Password"
          type="password"
          required
          placeholder="Enter your password"
          class="mb-4"
          autocomplete="new-password"
          :rules="[v => !!v || 'Password is required', v => v.length >= 8 || 'Password must be at least 8 characters']"
          :disabled="authStore.loading"
        />
        <v-text-field
          v-model="password2"
          label="Confirm Password"
          type="password"
          required
          placeholder="Confirm your password"
          class="mb-4"
          autocomplete="new-password"
          :rules="[v => !!v || 'Confirmation is required', v => v === password || 'Passwords must match']"
          :disabled="authStore.loading"
        />
        <v-btn
          type="submit"
          :loading="authStore.loading"
          :disabled="authStore.loading"
          color="primary"
          block
          class="mt-2 font-weight-bold"
        >
          Register
        </v-btn>
      </v-form>
      <div class="text-center mt-6">
        <span>Already have an account?</span>
        <router-link to="/login" class="text-primary ms-1">Login</router-link>
      </div>
    </v-card>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

onMounted(() => {
  authStore.error = null;
})

const router = useRouter()
const authStore = useAuthStore()

const email = ref('')
const username = ref('')
const name = ref('')
const password = ref('')
const password2 = ref('')

const formRef = ref();

const handleRegister = async () => {
    // Validate form before sending request
    const form = formRef.value;
    if (form && typeof form.validate === 'function') {
        const result = await form.validate();
        // Vuetify 3 returns { valid: boolean }
        if (!result.valid) return;
    }
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

<style>
.v-messages__message{
  text-align: left !important;
  font-size: 14px;
}

</style>