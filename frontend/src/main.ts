import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './style.css'

// Create the app and Pinia instance
const app = createApp(App)
const pinia = createPinia()

// Install Pinia first
app.use(pinia)

// Then install router
app.use(router)

// Mount the app
app.mount('#app')
