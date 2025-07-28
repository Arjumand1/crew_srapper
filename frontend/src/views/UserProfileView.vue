<template>
  <v-container class="py-8" fluid>
    <v-row class="mb-6 align-center justify-space-between">
      <v-col cols="12">
        <div class="d-flex align-center gap-4">
          <v-icon size="x-large" color="primary">mdi-account-circle</v-icon>
          <div>
            <span class="text-h4">User Profile</span>
            <p class="text-subtitle-1 mt-1">Manage your templates and company learning patterns</p>
          </div>
        </div>
      </v-col>
    </v-row>

    <!-- Error Message -->
    <v-row v-if="error">
      <v-col cols="12">
        <v-alert type="error" variant="tonal" closable @click:close="error = null">
          {{ error }}
        </v-alert>
      </v-col>
    </v-row>

    <!-- Company Learning Patterns -->
    <v-row class="mb-6">
      <v-col cols="12">
        <v-card variant="outlined">
          <v-card-title class="d-flex align-center">
            <v-icon class="mr-2" color="primary">mdi-office-building</v-icon>
            Company Learning Patterns
            <v-spacer />
            <v-btn size="small" color="primary" variant="text" prepend-icon="mdi-refresh" :loading="loadingProfile"
              @click="loadCompanyProfile">
              Refresh
            </v-btn>
          </v-card-title>

          <v-card-text>
            <v-row>
              <!-- Cost Centers -->
              <v-col cols="12" md="6">
                <div class="d-flex align-center mb-2">
                  <v-icon class="mr-2" size="small">mdi-currency-usd</v-icon>
                  <span class="font-weight-medium">Cost Centers</span>
                  <v-spacer />
                  <v-btn size="small" color="primary" variant="text" prepend-icon="mdi-plus"
                    @click="showCostCenterDialog = true">
                    Add
                  </v-btn>
                </div>
                <v-chip-group v-if="availableCostCenters.length">
                  <v-chip v-for="center in availableCostCenters" :key="center" size="small" color="primary"
                    variant="outlined" closable @click:close="removeCostCenter(center)">
                    {{ center }}
                  </v-chip>
                </v-chip-group>
                <v-alert v-else type="info" variant="tonal" density="compact">
                  No cost centers learned yet. Add commonly used cost centers.
                </v-alert>
              </v-col>

              <!-- Tasks -->
              <v-col cols="12" md="6">
                <div class="d-flex align-center mb-2">
                  <v-icon class="mr-2" size="small">mdi-clipboard-list</v-icon>
                  <span class="font-weight-medium">Tasks</span>
                  <v-spacer />
                  <v-btn size="small" color="primary" variant="text" prepend-icon="mdi-plus"
                    @click="showTaskDialog = true">
                    Add
                  </v-btn>
                </div>
                <v-chip-group v-if="availableTasks.length">
                  <v-chip v-for="task in availableTasks" :key="task" size="small" color="secondary" variant="outlined"
                    closable @click:close="removeTask(task)">
                    {{ task }}
                  </v-chip>
                </v-chip-group>
                <v-alert v-else type="info" variant="tonal" density="compact">
                  No tasks learned yet. Add commonly used task codes.
                </v-alert>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Template Management -->
    <v-row>
      <v-col cols="12">
        <v-card variant="outlined">
          <v-card-title class="d-flex align-center">
            <v-icon class="mr-2" color="secondary">mdi-folder-multiple</v-icon>
            Template Management
            <v-spacer />
            <v-btn size="small" color="primary" variant="text" prepend-icon="mdi-upload" class="mr-2"
              @click="showUploadTemplateDialog = true">
              Upload Template
            </v-btn>
            <v-btn size="small" color="secondary" variant="text" prepend-icon="mdi-refresh"
              :loading="loadingTemplateManagement" @click="loadAllTemplates">
              Refresh
            </v-btn>
          </v-card-title>

          <v-card-text>
            <v-data-table :items="allTemplates" :headers="[
              { title: 'Name', key: 'name', sortable: true },
              { title: 'Company', key: 'company', sortable: true },
              { title: 'Type', key: 'template_type', sortable: true },
              { title: 'Usage', key: 'usage_count', sortable: true },
              { title: 'Success Rate', key: 'success_rate', sortable: true },
              { title: 'Active', key: 'is_active', sortable: true },
              { title: 'Actions', key: 'actions', sortable: false }
            ]" :loading="loadingTemplateManagement" class="elevation-0">
              <template v-slot:item.template_type="{ item }">
                <v-chip size="small" :color="getTemplateTypeColor(item.template_type)" variant="outlined">
                  {{ getTemplateTypeName(item.template_type) }}
                </v-chip>
              </template>

              <template v-slot:item.success_rate="{ item }">
                <div class="d-flex align-center">
                  <v-progress-circular :model-value="item.success_rate * 100" size="24" width="3"
                    :color="item.success_rate > 0.8 ? 'success' : item.success_rate > 0.6 ? 'warning' : 'error'" />
                  <span class="ml-2">{{ (item.success_rate * 100).toFixed(1) }}%</span>
                </div>
              </template>
              <template v-slot:item.is_active="{ item }">
                <v-chip size="small" :color="item.is_active ? 'success' : 'error'" variant="outlined">
                  {{ item.is_active ? 'Active' : 'Inactive' }}
                </v-chip>
              </template>
              <template v-slot:item.actions="{ item }">
                <div class="d-flex gap-1">
                  <v-btn icon size="small" color="primary" variant="text" @click="editTemplate(item)">
                    <v-icon size="small">mdi-pencil</v-icon>
                  </v-btn>
                  <v-btn icon size="small" color="error" variant="text" @click="deleteTemplate(item)">
                    <v-icon size="small">mdi-delete</v-icon>
                  </v-btn>
                </div>
              </template>
              <template #no-data>
                <div class="text-center py-4">
                  No templates found. Upload one to get started.
                </div>
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Add Cost Center Dialog -->
    <v-dialog v-model="showCostCenterDialog" max-width="400px" persistent>
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2" color="primary">mdi-currency-usd</v-icon>
          Add Cost Center
        </v-card-title>

        <v-card-text>
          <v-text-field v-model="newCostCenter" label="Cost Center" placeholder="e.g., MAINT-001, PROD-200"
            prepend-inner-icon="mdi-tag" @keydown.enter="addCostCenter" />
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn color="grey" variant="text" @click="cancelCostCenterDialog">
            Cancel
          </v-btn>
          <v-btn color="primary" variant="elevated" :disabled="!newCostCenter.trim()" @click="addCostCenter">
            Add
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Add Task Dialog -->
    <v-dialog v-model="showTaskDialog" max-width="400px" persistent>
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2" color="secondary">mdi-clipboard-list</v-icon>
          Add Task
        </v-card-title>

        <v-card-text>
          <v-text-field v-model="newTask" label="Task Code" placeholder="e.g., WELD-01, PAINT-05"
            prepend-inner-icon="mdi-wrench" @keydown.enter="addTask" />
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn color="grey" variant="text" @click="cancelTaskDialog">
            Cancel
          </v-btn>
          <v-btn color="secondary" variant="elevated" :disabled="!newTask.trim()" @click="addTask">
            Add
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Edit Template Dialog -->
    <v-dialog v-model="showEditTemplateDialog" max-width="600px" persistent>
      <v-card v-if="editingTemplate">
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2" color="primary">mdi-pencil</v-icon>
          Edit Template
        </v-card-title>

        <v-card-text>
          <v-form ref="editTemplateFormRef">
            <v-row>
              <v-col cols="12">
                <v-text-field v-model="editingTemplate.name" label="Template Name" required
                  :rules="[v => !!v || 'Template name is required']" prepend-inner-icon="mdi-tag" />
              </v-col>

              <v-col cols="12">
                <v-textarea v-model="editingTemplate.description" label="Description" rows="3"
                  prepend-inner-icon="mdi-text" />
              </v-col>

              <v-col cols="12" md="6">
                <v-text-field v-model="editingTemplate.company" label="Company Name" prepend-inner-icon="mdi-domain" />
              </v-col>

              <v-col cols="12" md="6">
                <v-select v-model="editingTemplate.template_type" :items="[
                  { value: 'time_tracking', title: 'Time Tracking' },
                  { value: 'piece_work', title: 'Piece Work' },
                  { value: 'mixed', title: 'Mixed Time/Piece' },
                  { value: 'custom', title: 'Custom' }
                ]" label="Template Type" prepend-inner-icon="mdi-format-list-bulleted-type" />
              </v-col>

              <v-col cols="12">
                <v-switch v-model="editingTemplate.is_active" label="Active Template" color="success"
                  prepend-icon="mdi-power" />
              </v-col>

              <!-- Template Statistics (Read-only) -->
              <v-col cols="12" md="6">
                <v-text-field :model-value="editingTemplate.usage_count" label="Usage Count" readonly
                  prepend-inner-icon="mdi-counter" />
              </v-col>

              <v-col cols="12" md="6">
                <v-text-field :model-value="`${(editingTemplate.success_rate * 100).toFixed(1)}%`" label="Success Rate"
                  readonly prepend-inner-icon="mdi-chart-line" />
              </v-col>
            </v-row>
          </v-form>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn color="grey" variant="text" @click="cancelEditTemplate">
            Cancel
          </v-btn>
          <v-btn color="primary" variant="elevated" :loading="processing" @click="updateTemplate">
            Update Template
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Upload Template Dialog -->
    <v-dialog v-model="showUploadTemplateDialog" max-width="600px" persistent>
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2" color="primary">mdi-upload</v-icon>
          Upload Template
        </v-card-title>

        <v-card-text>
          <v-form ref="uploadTemplateFormRef">
            <v-row>
              <v-col cols="12">
                <v-text-field v-model="newTemplate.name" label="Template Name" required
                  :rules="[v => !!v || 'Template name is required']" prepend-inner-icon="mdi-tag" />
              </v-col>

              <v-col cols="12">
                <v-textarea v-model="newTemplate.description" label="Description" rows="3" prepend-inner-icon="mdi-text"
                  hint="Describe how this template should be used" />
              </v-col>

              <v-col cols="12" md="6">
                <v-text-field v-model="newTemplate.company" label="Company Name" prepend-inner-icon="mdi-domain"
                  hint="Company that uses this format" />
              </v-col>

              <v-col cols="12" md="6">
                <v-select v-model="newTemplate.template_type" :items="[
                  { value: 'time_tracking', title: 'Time Tracking' },
                  { value: 'piece_work', title: 'Piece Work' },
                  { value: 'mixed', title: 'Mixed Time/Piece' },
                  { value: 'custom', title: 'Custom' }
                ]" label="Template Type" prepend-inner-icon="mdi-format-list-bulleted-type" />
              </v-col>

              <v-col cols="12">
                <v-file-input v-model="templateFile" label="Template Image" accept="image/*" prepend-icon="mdi-image"
                  show-size truncate-length="15" :rules="[v => !!v || 'Template image is required']" />
                <v-alert v-if="templateFile" type="info" variant="tonal" density="compact" class="mt-2">
                  Upload a blank or example crew sheet. This helps the AI recognize the format.
                </v-alert>
              </v-col>

              <v-col cols="12">
                <v-switch v-model="newTemplate.is_active" label="Active Template" color="success"
                  prepend-icon="mdi-power" />
              </v-col>
            </v-row>
          </v-form>
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn color="grey" variant="text" @click="cancelUploadTemplate">
            Cancel
          </v-btn>
          <v-btn color="primary" variant="elevated" :loading="uploading" @click="uploadTemplate">
            Upload Template
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useCrewSheetStore } from '../stores/crewSheets';

// Store
const crewSheetStore = useCrewSheetStore();

// Reactive state
const error = ref<string | null>(null);
const processing = ref(false);
const loading = ref(false);

// Company Learning Profile
const companyProfile = ref<any>(null);
const availableCostCenters = ref<string[]>([]);
const availableTasks = ref<string[]>([]);
const showCostCenterDialog = ref(false);
const showTaskDialog = ref(false);
const newCostCenter = ref('');
const newTask = ref('');
const loadingProfile = ref(false);

// Template Management
const allTemplates = ref<any[]>([]);
const editingTemplate = ref<any>(null);
const showEditTemplateDialog = ref(false);
const loadingTemplateManagement = ref(false);
const showUploadTemplateDialog = ref(false);
const newTemplate = ref({
  name: '',
  description: '',
  company: '',
  template_type: 'time_tracking',
  is_active: true
});
const templateFile = ref<File | null>(null);
const uploading = ref(false);
const uploadTemplateFormRef = ref<any>(null);

// Company Profile Functions
const loadCompanyProfile = async () => {
  loadingProfile.value = true;
  try {
    const profile = await crewSheetStore.getCompanyLearningProfile();
    companyProfile.value = profile;
    availableCostCenters.value = profile.common_cost_centers || [];
    availableTasks.value = profile.common_tasks || [];
  } catch (err: any) {
    console.error('Failed to load company profile:', err);
    error.value = 'Failed to load company profile. API endpoint may not be implemented.';
  } finally {
    loadingProfile.value = false;
  }
};

const addCostCenter = async () => {
  if (!newCostCenter.value.trim()) return;

  try {
    await crewSheetStore.addCostCenter(newCostCenter.value.trim());
    availableCostCenters.value.push(newCostCenter.value.trim());
    newCostCenter.value = '';
    showCostCenterDialog.value = false;
  } catch (err: any) {
    console.error('Failed to add cost center:', err);
    error.value = 'Failed to add cost center';
  }
};

const addTask = async () => {
  if (!newTask.value.trim()) return;

  try {
    await crewSheetStore.addTask(newTask.value.trim());
    availableTasks.value.push(newTask.value.trim());
    newTask.value = '';
    showTaskDialog.value = false;
  } catch (err: any) {
    console.error('Failed to add task:', err);
    error.value = 'Failed to add task';
  }
};

const removeCostCenter = async (costCenter: string) => {
  try {
    loadingProfile.value = true;
    const result = await crewSheetStore.removeCostCenter(costCenter);
    if (result.success) {
      availableCostCenters.value = result.common_cost_centers;
    } else {
      error.value = 'Failed to remove cost center';
    }
  } catch (err: any) {
    console.error('Failed to remove cost center:', err);
    error.value = 'Failed to remove cost center';
  } finally {
    loadingProfile.value = false;
  }
};

const removeTask = async (task: string) => {
  try {
    loadingProfile.value = true;
    const result = await crewSheetStore.removeTask(task);
    if (result.success) {
      availableTasks.value = result.common_tasks;
    } else {
      error.value = 'Failed to remove task';
    }
  } catch (err: any) {
    console.error('Failed to remove task:', err);
    error.value = 'Failed to remove task';
  } finally {
    loadingProfile.value = false;
  }
};

const cancelCostCenterDialog = () => {
  showCostCenterDialog.value = false;
  newCostCenter.value = '';
};

const cancelTaskDialog = () => {
  showTaskDialog.value = false;
  newTask.value = '';
};

// Template Management Functions
const loadAllTemplates = async () => {
  try {
    loadingTemplateManagement.value = true;
    allTemplates.value = await crewSheetStore.getAllTemplates();
  } catch (err: any) {
    console.error('Error loading templates:', err);
    error.value = 'Error loading templates';
  } finally {
    loadingTemplateManagement.value = false;
  }
};

const editTemplate = (template: any) => {
  editingTemplate.value = { ...template };
  showEditTemplateDialog.value = true;
};

const cancelEditTemplate = () => {
  showEditTemplateDialog.value = false;
  editingTemplate.value = null;
};

const updateTemplate = async () => {
  try {
    processing.value = true;
    // Update template via API
    const updatedTemplate = await crewSheetStore.updateTemplate(
      editingTemplate.value.id,
      {
        name: editingTemplate.value.name,
        description: editingTemplate.value.description,
        company: editingTemplate.value.company,
        template_type: editingTemplate.value.template_type,
        is_active: editingTemplate.value.is_active
      }
    );

    // Update local templates list
    const index = allTemplates.value.findIndex(t => t.id === editingTemplate.value.id);
    if (index !== -1 && updatedTemplate) {
      allTemplates.value[index] = updatedTemplate;
    }

    showEditTemplateDialog.value = false;
    editingTemplate.value = null;
  } catch (err: any) {
    console.error('Failed to update template:', err);
    error.value = 'Failed to update template';
  } finally {
    processing.value = false;
  }
};

const cancelUploadTemplate = () => {
  showUploadTemplateDialog.value = false;
  // Reset form
  newTemplate.value = {
    name: '',
    description: '',
    company: '',
    template_type: 'time_tracking',
    is_active: true
  };
  templateFile.value = null;
};

const uploadTemplate = async () => {
  try {
    // Form validation
    const valid = await uploadTemplateFormRef.value?.validate();
    if (!valid) return;

    // Check if template file is selected
    if (!templateFile.value) {
      error.value = 'Please select a template image file';
      return;
    }

    uploading.value = true;

    // Create FormData for file upload
    const formData = new FormData();
    formData.append('name', newTemplate.value.name);
    formData.append('description', newTemplate.value.description);
    formData.append('company', newTemplate.value.company);
    formData.append('template_type', newTemplate.value.template_type);
    formData.append('is_active', newTemplate.value.is_active ? 'true' : 'false');
    formData.append('template_image', templateFile.value);

    // Call API to upload template
    const result = await crewSheetStore.createTemplate(formData);

    if (result.id) {
      // Success
      showUploadTemplateDialog.value = false;
      await loadAllTemplates();
      cancelUploadTemplate(); // Reset form
    } else {
      error.value = 'Error uploading template';
    }
  } catch (err: any) {
    console.error('Error uploading template:', err);
    error.value = err.response?.data?.detail || 'Error uploading template';
  } finally {
    uploading.value = false;
  }
};

const deleteTemplate = async (template: any) => {
  if (!confirm(`Are you sure you want to delete template "${template.name}"?`)) {
    return;
  }

  try {
    await crewSheetStore.deleteTemplate(Number(template.id));
    allTemplates.value = allTemplates.value.filter(t => t.id !== template.id);
  } catch (err: any) {
    console.error('Failed to delete template:', err);
    error.value = 'Failed to delete template';
  }
};

// Helper functions for template types
const getTemplateTypeColor = (type: string): string => {
  const colorMap: Record<string, string> = {
    'time_tracking': 'blue',
    'piece_work': 'green',
    'mixed': 'purple',
    'custom': 'orange'
  };
  return colorMap[type] || 'grey';
};

const getTemplateTypeName = (type: string): string => {
  const nameMap: Record<string, string> = {
    'time_tracking': 'Time Tracking',
    'piece_work': 'Piece Work',
    'mixed': 'Mixed',
    'custom': 'Custom'
  };
  return nameMap[type] || type;
};

// Lifecycle
onMounted(async () => {
  await loadCompanyProfile();
  await loadAllTemplates();
});
</script>