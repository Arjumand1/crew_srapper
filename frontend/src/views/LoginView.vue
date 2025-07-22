<template>
  <v-container class="d-flex align-center justify-center fill-height" fluid>
    <v-card elevation="4" class="pa-6 mt-md-16 mt-8 w-lg-25 w-md-50 w-sm-75 w-100 ">
      <v-card-title class="text-h4 font-weight-bold text-center mb-12">Login</v-card-title>
      <v-alert v-if="authStore.error" type="error" class="mb-4" dense>{{ authStore.error }}</  v-alert>
      <v-form ref="formRef" @submit.prevent="handleLogin">
        <v-text-field
          v-model="email"
          label="Email"
          type="email"
          required
          placeholder="Enter your email"
          class="mb-4 mt-8"
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
          autocomplete="current-password"
          :rules="[v => !!v || 'Password is required', v => v.length >= 8 || 'Password must be at least 8 characters']"
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
          Login
        </v-btn>
      </v-form>
      <div class="text-center mt-6">
        <span>Don't have an account?</span>
        <router-link to="/register" class="text-primary ms-1">Register</router-link>
      </div>
    </v-card>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";

onMounted(() => {
  authStore.error = null;
})

const router = useRouter();
const authStore = useAuthStore();

const email = ref("");
const password = ref("");

const formRef = ref();

const handleLogin = async () => {
  // Validate form before sending request
  const form = formRef.value;
  if (form && typeof form.validate === 'function') {
    const result = await form.validate();
    // Vuetify 3 returns { valid: boolean }
    if (!result.valid) return;
  }
  try {
    const success = await authStore.login(email.value, password.value);
    if (success) {
      router.push("/");
    }
  } catch (error) {
    console.error("Login error:", error);
  }
};
</script>

<style>
.v-messages__message{
  text-align: left !important;
  font-size: 14px;
}

</style>