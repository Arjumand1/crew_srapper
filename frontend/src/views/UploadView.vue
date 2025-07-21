<template>
    <div class="upload-container">
        <h1>Upload Crew Sheet</h1>

        <div v-if="error" class="error-message">
            {{ error }}
        </div>

        <form @submit.prevent="handleSubmit" class="upload-form">
            <div class="form-group">
                <label for="name">Sheet Name (optional)</label>
                <input type="text" id="name" v-model="form.name" placeholder="Enter a name for this crew sheet">
            </div>

            <div class="form-group">
                <label for="image">Crew Sheet Image</label>
                <input type="file" id="image" @change="handleFileChange" accept="image/*" required>
                <small>Supported formats: JPEG, PNG, GIF, BMP</small>
            </div>

            <div v-if="imagePreview" class="image-preview">
                <img :src="imagePreview" alt="Preview">
            </div>

            <button type="submit" class="btn-submit" :disabled="loading">
                <span v-if="loading">Uploading...</span>
                <span v-else>Upload Crew Sheet</span>
            </button>
        </form>
    </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue';
import { useRouter } from 'vue-router';
import { useCrewSheetStore } from '../stores/crewSheets';

const router = useRouter();
const crewSheetStore = useCrewSheetStore();

const form = reactive({
    name: '',
    image: null as File | null
});

const imagePreview = ref<string | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);

const handleFileChange = (event: Event) => {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
        form.image = input.files[0];

        // Create a preview
        const reader = new FileReader();
        reader.onload = (e) => {
            imagePreview.value = e.target?.result as string;
        };
        reader.readAsDataURL(form.image);
    }
};

const handleSubmit = async () => {
    if (!form.image) {
        error.value = 'Please select an image file';
        return;
    }

    loading.value = true;
    error.value = null;

    try {
        const formData = new FormData();
        formData.append('image', form.image);

        if (form.name) {
            formData.append('name', form.name);
        }

        const response = await crewSheetStore.uploadCrewSheet(formData);

        // Navigate to the sheet detail page
        router.push({ name: 'crewSheet', params: { id: response.id } });
    } catch (e) {
        if (e instanceof Error) {
            error.value = e.message;
        } else {
            error.value = 'An error occurred during upload';
        }
    } finally {
        loading.value = false;
    }
};
</script>

<style scoped>
.upload-container {
    max-width: 800px;
    /* margin: 0 auto; */
    padding: 2rem;
}

.error-message {
    background-color: #fee;
    color: #c00;
    padding: 1rem;
    margin-bottom: 1rem;
    border-radius: 4px;
}

.upload-form {
    background-color: #f9f9f9;
    padding: 2rem;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.form-group {
    margin-bottom: 1.5rem;
}

label {
    display: block;
    font-weight: bold;
    margin-bottom: 0.5rem;
}

input[type="text"] {
    width: 100%;
    padding: 0.75rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 1rem;
}

input[type="file"] {
    display: block;
    margin-top: 0.5rem;
}

small {
    display: block;
    color: #666;
    margin-top: 0.25rem;
}

.image-preview {
    margin-top: 1rem;
    margin-bottom: 1rem;
    border: 1px dashed #ccc;
    padding: 1rem;
    text-align: center;
}

.image-preview img {
    max-width: 100%;
    max-height: 300px;
    object-fit: contain;
}

.btn-submit {
    background-color: #4caf50;
    color: white;
    border: none;
    padding: 0.75rem 1.5rem;
    font-size: 1rem;
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.3s;
}

.btn-submit:hover {
    background-color: #45a049;
}

.btn-submit:disabled {
    background-color: #ccc;
    cursor: not-allowed;
}
</style>
