<template>
  <v-container class="pa-6" max-width="800">
    <v-card class="pa-6 mt-lg-8 mt-sm-6 mt-4 mb-8 elevation-2">
      <v-row justify="center">
        <v-col cols="12">
          <div class="mb-6 text-h4">Upload Crew Sheet</div>
        </v-col>
        <v-col cols="12">
          <v-alert
            v-if="error"
            type="error"
            class="mb-4"
            border="start"
            variant="tonal"
          >
            {{ error }}
          </v-alert>
          <v-form @submit.prevent="handleSubmit">
            <v-row>
              <v-col cols="12" class="mb-4">
                <v-text-field
                  v-model="form.name"
                  label="Sheet Name (optional)"
                  placeholder="Enter a name for this crew sheet"
                  variant="outlined"
                  hide-details
                />
              </v-col>
              <v-col cols="12" class="mb-4">
                <div class="text-center mb-2">
                  <input
                    ref="fileInput"
                    type="file"
                    accept="image/*"
                    class="d-none"
                    @change="handleFileChange"
                    required
                  />
                  <v-btn
                    size="small"
                    variant="text"
                    @click="triggerFileInput"
                    prepend-icon="mdi-upload"
                    class="me-2 bg-primary"
                  >
                    Choose Image
                  </v-btn>
                  <span
                    v-if="form.image"
                    class="text-caption text-grey-darken-2"
                  >
                    {{ form.image.name }}
                  </span>
                </div>
                <div class="text-grey-darken-1 text-caption mb-2">
                  Supported formats: JPEG, PNG, GIF, BMP
                </div>
              </v-col>
              <v-col cols="12" v-if="imagePreview">
                <v-sheet
                  class="pa-4 mb-4 d-flex justify-center align-center"
                  rounded="lg"
                  color="grey-lighten-4"
                  border
                >
                  <v-img
                    :src="imagePreview"
                    alt="Preview"
                    max-width="100%"
                    max-height="300"
                    contain
                  />
                </v-sheet>
              </v-col>
              <v-col cols="12" class="d-flex justify-center">
                <v-btn
                  color="success"
                  type="submit"
                  :loading="loading"
                  :disabled="loading"
                  size="large"
                  class="px-8"
                >
                  <span v-if="loading">Uploading...</span>
                  <span v-else>Upload Crew Sheet</span>
                </v-btn>
              </v-col>
            </v-row>
          </v-form>
        </v-col>
      </v-row>
    </v-card>
  </v-container>
</template>

<script setup lang="ts">
import { ref, reactive } from "vue";
import { useRouter } from "vue-router";
import { useCrewSheetStore } from "../stores/crewSheets";

const fileInput = ref<HTMLInputElement | null>(null);

function triggerFileInput() {
  if (fileInput.value) fileInput.value.click();
}

const router = useRouter();
const crewSheetStore = useCrewSheetStore();

const form = reactive({
  name: "",
  image: null as File | null,
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
    error.value = "Please select an image file";
    return;
  }

  loading.value = true;
  error.value = null;

  try {
    const formData = new FormData();
    formData.append("image", form.image);

    if (form.name) {
      formData.append("name", form.name);
    }

    const response = await crewSheetStore.uploadCrewSheet(formData);

    // Navigate to the sheet detail page
    router.push({ name: "crewSheet", params: { id: response.id } });
  } catch (e) {
    if (e instanceof Error) {
      error.value = e.message;
    } else {
      error.value = "An error occurred during upload";
    }
  } finally {
    loading.value = false;
  }
};
</script>
