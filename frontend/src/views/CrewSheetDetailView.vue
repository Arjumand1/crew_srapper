<template>
  <v-container class="py-8 w-lg-75 w-100" fluid>
    <v-row class="mb-6 align-center mt-6 justify-space-between">
      <v-col cols="12" md="6">
        <div class="d-flex align-center gap-4">
          <v-icon size="x-large" color="primary">mdi-file-document-outline</v-icon>
          <div>
            <span class="text-h4">{{ currentSheet?.name || 'Crew Sheet Details' }}</span>
            <!-- Quality indicators -->
            <div v-if="currentSheet && currentSheet.confidence_score !== undefined" class="mt-2">
              <v-chip :color="getConfidenceColor(currentSheet.confidence_score)" size="small" class="mr-2">
                <v-icon start size="small">mdi-gauge</v-icon>
                Confidence: {{ (currentSheet.confidence_score * 100).toFixed(1) }}%
              </v-chip>
              <v-chip v-if="currentSheet.needs_review" color="warning" size="small">
                <v-icon start size="small">mdi-alert</v-icon>
                Needs Review
              </v-chip>
            </div>
          </div>
        </div>
      </v-col>
      <v-col cols="12" md="6" class="d-flex justify-end align-center">
        <v-chip :color="statusColor(currentSheet?.status)" class="text-uppercase" size="large">
          {{ currentSheet?.status }}
        </v-chip>
      </v-col>
    </v-row>

    <!-- Smart Review Queue Alert -->
    <v-row v-if="inReviewQueue" class="mb-4">
      <v-col cols="12">
        <v-alert type="warning" variant="tonal" border="start">
          <template v-slot:title>
            <v-icon class="mr-2">mdi-flag</v-icon>
            Smart Review Required
          </template>
          <div class="mt-2">
            <p><strong>Priority Score:</strong> {{ reviewQueueItem.priority_score }}/100</p>
            <p><strong>Reason:</strong> {{ formatReviewReason(reviewQueueItem.review_reason) }}</p>
            <div v-if="reviewQueueItem.flagged_issues?.length" class="mt-2">
              <strong>Issues Detected:</strong>
              <v-chip-group class="mt-1">
                <v-chip 
                  v-for="issue in reviewQueueItem.flagged_issues" 
                  :key="issue" 
                  size="small"
                  color="warning"
                >
                  {{ issue }}
                </v-chip>
              </v-chip-group>
            </div>
            <div v-if="reviewQueueItem.suggested_actions?.length" class="mt-2">
              <strong>Suggested Actions:</strong>
              <ul class="mt-1">
                <li v-for="action in reviewQueueItem.suggested_actions" :key="action">
                  {{ action }}
                </li>
              </ul>
            </div>
          </div>
        </v-alert>
      </v-col>
    </v-row>

    <!-- Template Selection and Smart Processing -->
    <v-row v-if="currentSheet && currentSheet.status === 'pending'" class="mb-4">
      <v-col cols="12">
        <v-card class="pa-4" variant="outlined">
          <v-card-title class="d-flex align-center">
            <v-icon class="mr-2" color="primary">mdi-robot</v-icon>
            AI-Enhanced Processing
          </v-card-title>
          <v-card-text>
            <!-- Template Selection -->
            <v-row>
              <v-col cols="12" md="6">
                <v-select
                  v-model="selectedTemplate"
                  :items="availableTemplates"
                  item-title="name"
                  item-value="id"
                  label="Select Template (Optional)"
                  hint="Choose a template for better extraction accuracy"
                  persistent-hint
                  clearable
                >
                  <template v-slot:item="{ props, item }">
                    <v-list-item v-bind="props">
                      <template v-slot:title>{{ item.raw.name }}</template>
                      <template v-slot:subtitle>
                        {{ item.raw.description }} • Success Rate: {{ (item.raw.success_rate * 100).toFixed(1) }}%
                      </template>
                      <template v-slot:append>
                        <v-chip size="small" :color="getTemplateTypeColor(item.raw.template_type)">
                          {{ formatTemplateType(item.raw.template_type) }}
                        </v-chip>
                      </template>
                    </v-list-item>
                  </template>
                </v-select>
              </v-col>
              <v-col cols="12" md="6">
                <div class="d-flex flex-column gap-2">
                  <v-btn 
                    v-if="selectedTemplate" 
                    color="primary" 
                    :loading="processing" 
                    @click="processWithTemplate"
                    block
                  >
                    <v-icon start>mdi-auto-fix</v-icon>
                    Process with Template
                  </v-btn>
                  <v-btn 
                    color="secondary" 
                    :loading="processing" 
                    @click="processWithAI"
                    block
                  >
                    <v-icon start>mdi-brain</v-icon>
                    Smart Process (AI Learning)
                  </v-btn>
                  <v-btn 
                    color="info" 
                    :loading="loadingTemplates" 
                    @click="loadTemplateSuggestions"
                    variant="outlined"
                    block
                  >
                    <v-icon start>mdi-lightbulb</v-icon>
                    Get Template Suggestions
                  </v-btn>
                </div>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Learning Insights Panel -->
    <v-row v-if="learningInsights && showLearningInsights" class="mb-4">
      <v-col cols="12">
        <v-expansion-panels variant="accordion">
          <v-expansion-panel title="🧠 AI Learning Insights">
            <v-expansion-panel-text>
              <v-row>
                <v-col cols="12" md="4">
                  <v-card class="pa-4" variant="tonal" color="info">
                    <div class="text-subtitle-2 mb-2">Your Editing Patterns</div>
                    <div class="text-h6 mb-1">{{ learningInsights.user_insights?.avg_edits_per_sheet?.toFixed(1) || 0 }} edits/sheet</div>
                    <div class="text-body-2 text-medium-emphasis">Average corrections needed</div>
                  </v-card>
                </v-col>
                <v-col cols="12" md="4">
                  <v-card class="pa-4" variant="tonal" color="success">
                    <div class="text-subtitle-2 mb-2">Completion Rate</div>
                    <div class="text-h6 mb-1">{{ ((learningInsights.user_insights?.completion_rate || 0) * 100).toFixed(1) }}%</div>
                    <div class="text-body-2 text-medium-emphasis">Sheets successfully completed</div>
                  </v-card>
                </v-col>
                <v-col cols="12" md="4">
                  <v-card class="pa-4" variant="tonal" color="primary">
                    <div class="text-subtitle-2 mb-2">Templates Available</div>
                    <div class="text-h6 mb-1">{{ learningInsights.templates_available || 0 }}</div>
                    <div class="text-body-2 text-medium-emphasis">Custom templates created</div>
                  </v-card>
                </v-col>
              </v-row>

              <!-- Most Edited Fields -->
              <v-row v-if="learningInsights.user_insights?.most_edited_fields" class="mt-4">
                <v-col cols="12">
                  <h4 class="mb-3">Fields You Most Often Correct:</h4>
                  <v-chip-group>
                    <v-chip 
                      v-for="(count, field) in learningInsights.user_insights.most_edited_fields" 
                      :key="field"
                      :color="getFieldEditColor(count)"
                      size="small"
                    >
                      {{ formatFieldName(field) }}: {{ count }}
                    </v-chip>
                  </v-chip-group>
                </v-col>
              </v-row>

              <!-- Company Profile -->
              <v-row v-if="learningInsights.company_profile" class="mt-4">
                <v-col cols="12">
                  <h4 class="mb-3">Learned Company Patterns:</h4>
                  <v-row>
                    <v-col cols="12" md="4" v-if="learningInsights.company_profile.common_cost_centers?.length">
                      <div class="text-subtitle-2 mb-2">Cost Centers</div>
                      <v-chip-group>
                        <v-chip 
                          v-for="center in learningInsights.company_profile.common_cost_centers" 
                          :key="center"
                          size="small"
                          color="blue-grey"
                        >
                          {{ center }}
                        </v-chip>
                      </v-chip-group>
                    </v-col>
                    <v-col cols="12" md="4" v-if="learningInsights.company_profile.common_tasks?.length">
                      <div class="text-subtitle-2 mb-2">Common Tasks</div>
                      <v-chip-group>
                        <v-chip 
                          v-for="task in learningInsights.company_profile.common_tasks" 
                          :key="task"
                          size="small"
                          color="teal"
                        >
                          {{ task }}
                        </v-chip>
                      </v-chip-group>
                    </v-col>
                    <v-col cols="12" md="4" v-if="learningInsights.company_profile.typical_headers?.length">
                      <div class="text-subtitle-2 mb-2">Typical Headers</div>
                      <v-chip-group>
                        <v-chip 
                          v-for="header in learningInsights.company_profile.typical_headers" 
                          :key="header"
                          size="small"
                          color="purple"
                        >
                          {{ formatFieldName(header) }}
                        </v-chip>
                      </v-chip-group>
                    </v-col>
                  </v-row>
                </v-col>
              </v-row>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-col>
    </v-row>

    <!-- Quality Metrics Panel -->
    <v-row v-if="learningMetrics && showLearningMetrics" class="mb-4">
      <v-col cols="12">
        <v-expansion-panels variant="accordion">
          <v-expansion-panel title="Quality Metrics">
            <v-expansion-panel-text>
              <v-row>
                <v-col cols="12" md="6">
                  <v-card class="pa-4" variant="tonal">
                    <div class="text-subtitle-2 mb-2">Confidence Score</div>
                    <div class="text-h5" :class="getConfidenceColor(learningMetrics.confidence_score)">
                      {{ (learningMetrics.confidence_score * 100).toFixed(1) }}%
                    </div>
                    <v-progress-linear :model-value="learningMetrics.confidence_score * 100"
                      :color="getConfidenceColor(learningMetrics.confidence_score)" height="6"
                      class="mt-2"></v-progress-linear>
                  </v-card>
                </v-col>
                <v-col cols="12" md="6">
                  <v-card class="pa-4" variant="tonal">
                    <div class="text-subtitle-2 mb-2">Issues Detected</div>
                    <v-chip-group v-if="learningMetrics.issues_detected?.length">
                      <v-chip v-for="issue in learningMetrics.issues_detected" :key="issue" size="small"
                        color="warning">
                        {{ issue }}
                      </v-chip>
                    </v-chip-group>
                    <span v-else class="text-success">No issues detected</span>
                  </v-card>
                </v-col>
              </v-row>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-col>
    </v-row>

    <v-alert v-if="loading" type="info" class="mb-4" border="start" variant="tonal">
      Loading crew sheet data...
    </v-alert>
    <v-alert v-if="error" type="error" class="mb-4" border="start" variant="tonal">
      {{ error }}
    </v-alert>

    <v-row v-if="currentSheet && !loading" class="mb-8">
      <v-col cols="12">
        <v-alert v-if="currentSheet.status === 'failed'" type="error" class="mb-6" border="start" variant="tonal">
          <div class="d-flex align-center justify-space-between">
            <div>
              <div class="text-h6 mb-2">Processing Error</div>
              <div>{{ currentSheet.error_message }}</div>
            </div>
            <v-btn color="success" :loading="processing" :disabled="processing" @click="processCrewSheet">
              {{ processing ? 'Retrying...' : 'Retry Processing' }}
            </v-btn>
          </div>
        </v-alert>
        <v-row v-if="currentSheet.status !== 'failed'" class="mb-4">
          <v-col style="gap: 8px;" cols="12" class="d-flex justify-center flex-wrap">
            <v-btn v-if="currentSheet.status === 'pending'" color="primary" :loading="processing" :disabled="processing"
              @click="processCrewSheet">
              {{ processing ? 'Starting Process...' : 'Process Sheet' }}
            </v-btn>
            <v-btn color="info" :disabled="!canDownload" @click="downloadExcel">
              <v-icon start>mdi-microsoft-excel</v-icon> Download Excel
            </v-btn>
            <v-btn color="success" :disabled="!isEdited" @click="saveChanges">
              <v-icon start>mdi-content-save</v-icon> Save Changes
              <v-badge v-if="editCount > 0" :content="editCount" color="warning" inline></v-badge>
            </v-btn>
            <v-btn color="secondary" @click="goBack">
              <v-icon start>mdi-arrow-left</v-icon> Back to List
            </v-btn>
          </v-col>
        </v-row>
      </v-col>
    </v-row>

    <v-row v-if="currentSheet && currentSheet.status === 'completed' && currentSheet.extracted_data">
      <v-col cols="12">
        <v-card class="pa-6 mb-8 elevation-2">
          <v-card-title class="text-h5 mb-4">Extracted Data</v-card-title>
          <v-row>
            <v-col cols="12" md="6">
              <v-card class="pa-4 mb-4" color="grey-lighten-4" flat>
                <div class="text-h6 mb-2">Sheet Information</div>
                <v-list density="compact">
                  <v-list-item v-for="(value, key) in headerInfo" :key="String(key)">
                    <v-list-item-title class="font-weight-bold">{{ formatLabel(String(key)) }}:</v-list-item-title>
                    <v-list-item-subtitle>{{ value }}</v-list-item-subtitle>
                  </v-list-item>
                </v-list>
              </v-card>
            </v-col>
            <!-- {{ summaryInfo }} -->
            <v-col cols="12" md="6">
              <v-card class="pa-4 mb-4" color="grey-lighten-4" flat>
                <div class="text-h6 mb-2">Summary</div>
                <v-list density="compact">
                  <v-list-item v-for="(value, key) in summaryInfo" :key="String(key)">
                    <v-list-item-title class="font-weight-bold">{{ formatLabel(String(key)) }}:</v-list-item-title>
                    <v-list-item-subtitle>{{ value }}</v-list-item-subtitle>
                  </v-list-item>
                </v-list>
              </v-card>
            </v-col>
          </v-row>



          <!-- Editable Data Table -->
          <div class="mt-8">
            <div style="gap: 8px;" class="d-flex align-center justify-center mb-4">
              <v-btn color="success" @click="addRow">Add Row</v-btn>
              <v-btn color="secondary" @click="toggleEditingHeaders">
                {{ editingHeaders ? 'Done Editing Headers' : 'Edit Headers' }}
              </v-btn>
            </div>
            <v-table class="overflow-x-auto" fixed-header style="min-width: 900px;">
              <thead class="font-weight-bold">
                <tr>
                  <th class="text-center" style="min-width: 60px;">ID</th>
                  <th v-for="(header, index) in headers" :key="'header-th-' + index + '-' + headerEditKey"
                    class="text-center" style="min-width: 160px; white-space: pre-line;">
                    <template v-if="editingHeaders">
                      <v-text-field :model-value="headers[index]"
                        @update:model-value="handleHeaderRename(index, $event)" density="compact" hide-details
                        class="w-75 mx-auto" :ref="setHeaderInputRef(index)"
                        :key="'header-input-' + index + '-' + headerEditKey">
                        <template #append-inner>
                          <v-btn v-if="!isEmployeeNameHeader(header)" icon size="x-small" color="error"
                            @click.stop="removeHeader(index)" tabindex="-1" style="height: 16px; width: 16px;">
                            <v-icon>mdi-close</v-icon>
                          </v-btn>
                        </template>
                      </v-text-field>
                    </template>
                    <template v-else>
                      <span @click="sortTable(header)" class="cursor-pointer">
                        {{ formatHeaderForDisplay(header) }}
                        <v-icon v-if="sortColumn === header" size="x-small">
                          {{ sortDirection === 'asc' ? 'mdi-arrow-up' : 'mdi-arrow-down' }}
                        </v-icon>
                      </span>
                    </template>
                  </th>
                  <th v-if="editingHeaders" class="text-center" style="min-width: 140px;">
                    <v-text-field v-model="newHeader" density="compact" hide-details class="w-75 mx-auto"
                      placeholder="New header" @keydown.enter="addHeader" />
                    <v-btn icon size="x-small" color="success" @click.stop="addHeader">
                      <v-icon>mdi-plus</v-icon>
                    </v-btn>
                  </th>
                  <th class="text-center" style="min-width: 120px;">Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(employee, rowIndex) in sortedEmployees" :key="rowIndex">
                  <td class="text-center font-weight-bold" style="min-width: 60px;">{{ rowIndex + 1 }}</td>
                  <td v-for="header in headers" :key="`${rowIndex}-${header}`" style="min-width: 160px;">
                    <v-text-field v-model="employee[isEmployeeNameHeader(header) ? 'name' : header]" density="compact"
                      hide-details :class="{
                        'bg-yellow-lighten-4': isUncertain(employee, header),
                        'bg-blue-lighten-4': employee._edited && employee._edited.includes(isEmployeeNameHeader(header) ? 'name' : header),
                        'font-weight-bold': isEmployeeNameHeader(header),
                      }" @input="handleCellInput(rowIndex, header)" />
                  </td>
                  <td class="text-center" style="min-width: 100px;">
                    <v-btn icon size="small" color="error" @click="deleteRow(rowIndex)">
                      <v-icon>mdi-delete</v-icon>
                    </v-btn>
                  </td>
                </tr>
              </tbody>
            </v-table>
          </div>
        </v-card>
      </v-col>
    </v-row>



    <!-- Create Template Dialog -->
    <v-dialog v-model="showCreateTemplateDialog" max-width="600px" persistent>
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2" color="primary">mdi-file-plus</v-icon>
          Create Sheet Template
        </v-card-title>
        
        <v-card-text>
          <v-form ref="templateFormRef">
            <v-row>
              <v-col cols="12">
                <v-text-field
                  v-model="templateForm.name"
                  label="Template Name"
                  required
                  :rules="[v => !!v || 'Template name is required']"
                  prepend-inner-icon="mdi-tag"
                />
              </v-col>
              
              <v-col cols="12">
                <v-textarea
                  v-model="templateForm.description"
                  label="Description"
                  rows="3"
                  prepend-inner-icon="mdi-text"
                />
              </v-col>
              
              <v-col cols="12" md="6">
                <v-text-field
                  v-model="templateForm.company"
                  label="Company Name"
                  prepend-inner-icon="mdi-domain"
                />
              </v-col>
              
              <v-col cols="12" md="6">
                <v-select
                  v-model="templateForm.template_type"
                  :items="[
                    { value: 'time_tracking', title: 'Time Tracking' },
                    { value: 'piece_work', title: 'Piece Work' },
                    { value: 'mixed', title: 'Mixed Time/Piece' },
                    { value: 'custom', title: 'Custom' }
                  ]"
                  label="Template Type"
                  prepend-inner-icon="mdi-format-list-bulleted-type"
                />
              </v-col>
              
              <v-col cols="12">
                <v-file-input
                  v-model="templateForm.template_image"
                  label="Template Image (Optional)"
                  accept="image/*"
                  prepend-icon="mdi-camera"
                  show-size
                  clearable
                >
                  <template v-slot:selection="{ fileNames }">
                    <template v-for="fileName in fileNames" :key="fileName">
                      {{ fileName }}
                    </template>
                  </template>
                </v-file-input>
                <v-card 
                  v-if="templateForm.template_image && templateForm.template_image.length" 
                  variant="outlined" 
                  class="mt-2"
                >
                  <v-img
                    :src="getImagePreview(templateForm.template_image[0])"
                    max-height="200"
                    contain
                  />
                </v-card>
              </v-col>
            </v-row>
          </v-form>
        </v-card-text>
        
        <v-card-actions>
          <v-spacer />
          <v-btn 
            color="grey" 
            variant="text" 
            @click="cancelCreateTemplate"
          >
            Cancel
          </v-btn>
          <v-btn 
            color="primary" 
            variant="elevated"
            :loading="processing"
            @click="createTemplateFromSheet"
          >
            Create Template
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>





  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, nextTick, watch } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useCrewSheetStore } from '../stores/crewSheets';
import { useAuthStore } from '../stores/auth';
import axios from 'axios';
import * as XLSX from 'xlsx';

// Router and stores
const router = useRouter();
const route = useRoute();
const crewSheetStore = useCrewSheetStore();
const authStore = useAuthStore();

// Constants
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const sheetId = ref(route.params.id as string);

// Core reactive refs
const processing = ref(false);
const loading = ref(false);
const isEdited = ref(false);
const editCount = ref(0);
const error = ref<string | null>(null);
const sessionId = ref<string | null>(null);

// AI improvement features
const selectedTemplate = ref<string | null>(null);
const availableTemplates = ref<Array<any>>([]);
const loadingTemplates = ref(false);
const learningInsights = ref<any>(null);
const showLearningInsights = ref(false);
const learningMetrics = ref<any>(null);
const showLearningMetrics = ref(false);
const reviewQueueItem = ref<any>(null);
const inReviewQueue = ref(false);
const showCreateTemplateDialog = ref(false);
const templateForm = ref({
  name: '',
  description: '',
  company: '',
  template_type: 'mixed',
  template_image: [] as File[]
});

// Table editing refs
const headers = ref<string[]>([]);
const rows = ref<Record<string, string>[]>([]);
const editingHeaders = ref(false);
const newHeader = ref('');
const headerEditKey = ref(0);
const headerInputRefs = ref<any[]>([]);
const sortColumn = ref('');
const sortDirection = ref('asc');

// Computed properties
const sortedEmployees = computed(() => {
  if (!rows.value.length || !sortColumn.value) {
    return rows.value;
  }

  return [...rows.value].sort((a, b) => {
    const aValue = a[sortColumn.value] || '';
    const bValue = b[sortColumn.value] || '';
    
    const comparison = aValue.toString().localeCompare(bValue.toString(), undefined, {
      numeric: true,
      sensitivity: 'base'
    });
    
    return sortDirection.value === 'asc' ? comparison : -comparison;
  });
});


// Utility functions
const formatLabel = (label: string) => {
  return label.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
};

const isEmployeeNameHeader = (header: any) => {
  if (!header) return false;
  const normalized = header.toString().toLowerCase().replace(/[_\s]/g, '');
  return normalized === 'employeename' || normalized === 'name' || normalized === 'employee';
};

const parseHierarchicalHeader = (header: any) => {
  if (!header || typeof header !== 'string') return { costCenter: null, task: null, jobType: header };

  const jobKeywords = ['JOB', 'PIECE', 'WORK', 'HRS', 'HOURS', 'NO', 'PCS'];
  const parts = header.split('_');

  if (parts.length < 3) {
    return { costCenter: null, task: null, jobType: header.replace(/_/g, ' ') };
  }

  let jobTypeStartIndex = -1;
  for (let i = 0; i < parts.length; i++) {
    if (jobKeywords.includes(parts[i])) {
      jobTypeStartIndex = i;
      break;
    }
  }

  if (jobTypeStartIndex === -1) {
    if (parts.length >= 3) {
      return {
        costCenter: parts[0],
        task: parts[1],
        jobType: parts.slice(2).join(' ')
      };
    } else if (parts.length === 2) {
      return {
        costCenter: parts[0],
        task: null,
        jobType: parts[1]
      };
    } else {
      return { costCenter: null, task: null, jobType: header.replace(/_/g, ' ') };
    }
  }

  const costCenter = parts[0] || null;
  const task = jobTypeStartIndex > 1 ? parts.slice(1, jobTypeStartIndex).join(' ') : null;
  const jobType = parts.slice(jobTypeStartIndex).join(' ');

  return { costCenter, task, jobType };
};

const formatHeaderForDisplay = (header: any) => {
  if (!header) return '';
  if (isEmployeeNameHeader(header)) return 'EMPLOYEE NAME';

  const { costCenter, task, jobType } = parseHierarchicalHeader(header);
  let displayText = '';

  if (costCenter) displayText += costCenter;
  if (task) displayText += (displayText ? '\n' : '') + task;
  if (jobType) displayText += (displayText ? '\n' : '') + jobType;

  return displayText || header.replace(/_/g, ' ');
};

// AI improvement helper functions
const formatTemplateType = (type: string) => {
  return type.replace('_', ' ').replace(/\b\w/g, (l: string) => l.toUpperCase());
};

const getTemplateTypeColor = (type: string) => {
  const colors: Record<string, string> = {
    'time_tracking': 'blue',
    'piece_work': 'green', 
    'mixed': 'purple',
    'custom': 'orange'
  };
  return colors[type] || 'grey';
};

const formatReviewReason = (reason: string) => {
  const reasons: Record<string, string> = {
    'low_confidence': 'Low Confidence Score',
    'validation_failed': 'Validation Rules Failed',
    'unusual_format': 'Unusual Format Detected',
    'high_edit_frequency': 'High Edit Frequency Expected',
    'user_requested': 'User Requested Review',
    'template_mismatch': 'Template Mismatch'
  };
  return reasons[reason] || reason;
};

const formatFieldName = (field: string) => {
  return field.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase());
};

const getFieldEditColor = (count: number) => {
  if (count > 10) return 'red';
  if (count > 5) return 'orange';
  if (count > 2) return 'yellow';
  return 'green';
};

const getConfidenceColor = (score: number) => {
  if (score >= 0.8) return 'success';
  if (score >= 0.6) return 'warning';
  return 'error';
};

const statusColor = (status?: string) => {
  switch (status) {
    case 'completed': return 'success';
    case 'processing': return 'info';
    case 'failed': return 'error';
    case 'pending': return 'warning';
    default: return 'grey';
  }
};

// Computed properties
const currentSheet = computed(() => crewSheetStore.currentCrewSheet);

const canDownload = computed(() => {
  return currentSheet.value?.status === 'completed' && rows.value.length > 0;
});

const headerInfo = computed(() => {
  if (!currentSheet.value?.extracted_data) return null;
  const data = typeof currentSheet.value.extracted_data === 'string'
    ? JSON.parse(currentSheet.value.extracted_data)
    : currentSheet.value.extracted_data;
  
  if (data.header) return data.header;
  
  const headerFields = ['date', 'location', 'supervisor', 'project', 'title'];
  const extractedHeader: Record<string, any> = {};
  
  for (const field of headerFields) {
    if (data[field]) extractedHeader[field] = data[field];
  }
  
  return Object.keys(extractedHeader).length > 0 ? extractedHeader : null;
});

const summaryInfo = computed(() => {
  if (!currentSheet.value?.extracted_data) return null;
  const data = typeof currentSheet.value.extracted_data === 'string'
    ? JSON.parse(currentSheet.value.extracted_data)
    : currentSheet.value.extracted_data;
  
  if (data.metadata && typeof data.metadata === 'object') return data.metadata;
  if (data.summary && typeof data.summary === 'object') return data.summary;
  
  const summary: Record<string, any> = {};
  let employees = data.employees || data.rows || data.data || [];
  if (!Array.isArray(employees) && typeof employees === 'object') {
    employees = Object.values(employees);
  }
  summary['Total Employees'] = employees.length;
  
  const roleKey = ['role', 'position', 'job'].find(k => employees.length && k in employees[0]);
  if (roleKey) {
    const uniqueRoles = Array.from(new Set(employees.map((e: any) => e[roleKey] || '').filter(Boolean)));
    summary['Unique Roles'] = uniqueRoles.length;
    summary['Roles'] = uniqueRoles.join(', ');
  }
  
  return summary;
});

// Utility functions
const sortTable = (header: string) => {
  if (sortColumn.value === header) {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc';
  } else {
    sortColumn.value = header;
    sortDirection.value = 'asc';
  }
};

const getCellValue = (employee: any, header: string) => {
  if (!employee) return '';
  const fieldName = isEmployeeNameHeader(header) ? 'name' : header;
  const value = employee[fieldName];
  
  if (value === null || value === undefined) return '';
  if (typeof value === 'object' && value !== null) {
    if ('value' in value) return value.value || '';
    if ('text' in value) return value.text || '';
  }
  if (value === true || value === 'true' || value === '✓') return '✓';
  
  return String(value);
};

const isUncertain = (employee: any, header: string) => {
  if (!employee || !employee._uncertain) return false;
  const fieldName = isEmployeeNameHeader(header) ? 'name' : header;
  return Array.isArray(employee._uncertain) && employee._uncertain.includes(fieldName);
};

const setHeaderInputRef = (index: number) => {
  return (el: any) => {
    headerInputRefs.value[index] = el;
  };
};

const handleCellInput = (rowIndex: number, header: string) => {
  const fieldName = isEmployeeNameHeader(header) ? 'name' : header;
  isEdited.value = true;
  editCount.value++;
  
  if (!rows.value[rowIndex]._edited) {
    rows.value[rowIndex]._edited = [];
  }
  
  if (!rows.value[rowIndex]._edited.includes(fieldName)) {
    rows.value[rowIndex]._edited.push(fieldName);
  }
};

// Table editing functions
const handleHeaderRename = (index: number, newName: string) => {
  const oldName = headers.value[index];
  if (!newName || headers.value.includes(newName)) return;
  headers.value[index] = newName;
  for (const row of rows.value) {
    if (Object.prototype.hasOwnProperty.call(row, oldName)) {
      row[newName] = row[oldName];
      delete row[oldName];
    }
  }
  isEdited.value = true;
  editCount.value++;
};

const toggleEditingHeaders = () => {
  editingHeaders.value = !editingHeaders.value;
  headerEditKey.value++;
};

// AI improvement functions using store
const loadTemplateSuggestions = async () => {
  if (!currentSheet.value) return;
  
  loadingTemplates.value = true;
  try {
    const suggestions = await crewSheetStore.getTemplateSuggestions();
    availableTemplates.value = suggestions || [];
  } catch (err: any) {
    console.error('Failed to load template suggestions:', err);
    error.value = 'Failed to load template suggestions';
  } finally {
    loadingTemplates.value = false;
  }
};

const processWithTemplate = async () => {
  if (!currentSheet.value || !selectedTemplate.value) return;
  
  processing.value = true;
  error.value = null;
  
  try {
    const response = await crewSheetStore.processWithTemplate(
      currentSheet.value.id,
      selectedTemplate.value
    );
    
    if (response.id) {
      learningMetrics.value = response.learning_metrics;
      showLearningMetrics.value = true;
      await checkReviewQueueStatus();
      await loadSheet();
    }
  } catch (err: any) {
    console.error('Template processing failed:', err);
    error.value = 'Template processing failed';
  } finally {
    processing.value = false;
  }
};

const processWithAI = async () => {
  if (!currentSheet.value) return;
  
  processing.value = true;
  error.value = null;
  
  try {
    const response = await crewSheetStore.processWithAI(currentSheet.value.id);
    
    if (response.id) {
      learningMetrics.value = response.learning_metrics;
      showLearningMetrics.value = true;
      await checkReviewQueueStatus();
      await loadSheet();
    }
  } catch (err: any) {
    console.error('AI processing failed:', err);
    error.value = 'AI processing failed';
  } finally {
    processing.value = false;
  }
};

const checkReviewQueueStatus = async () => {
  if (!currentSheet.value) return;
  
  try {
    const response = await crewSheetStore.getReviewQueue();
    
    const queueItem = response.queue_items?.find(
      (item: any) => item.crew_sheet_id === currentSheet.value.id
    );
    
    if (queueItem) {
      reviewQueueItem.value = queueItem;
      inReviewQueue.value = true;
    } else {
      inReviewQueue.value = false;
    }
  } catch (err: any) {
    console.error('Failed to check review queue:', err);
  }
};

const loadLearningInsights = async () => {
  try {
    const insights = await crewSheetStore.getLearningInsights();
    learningInsights.value = insights;
    showLearningInsights.value = true;
  } catch (err: any) {
    console.error('Failed to load learning insights:', err);
  }
};

const createTemplateFromSheet = async () => {
  if (!currentSheet.value) return;
  
  try {
    const templateData: any = {
      template_name: templateForm.value.name,
      description: templateForm.value.description,
      company: templateForm.value.company,
      template_type: templateForm.value.template_type
    };
    
    // Add image if provided
    if (templateForm.value.template_image.length > 0) {
      templateData.template_image = templateForm.value.template_image[0];
    }
    
    const response = await crewSheetStore.createTemplate(
      currentSheet.value.id,
      templateData
    );
    
    if (response.template_id) {
      showCreateTemplateDialog.value = false;
      resetTemplateForm();
      await loadTemplateSuggestions();
      console.log('Template created successfully:', response.name);
    }
  } catch (err: any) {
    console.error('Failed to create template:', err);
    error.value = 'Failed to create template';
  }
};

const cancelCreateTemplate = () => {
  showCreateTemplateDialog.value = false;
  resetTemplateForm();
};

const resetTemplateForm = () => {
  templateForm.value = {
    name: '',
    description: '',
    company: '',
    template_type: 'mixed',
    template_image: []
  };
};

const getImagePreview = (file: File): string => {
  return URL.createObjectURL(file);
};





// Session management using store
const startSession = async () => {
  if (!currentSheet.value) return;
  
  try {
    const response = await crewSheetStore.startSession(currentSheet.value.id);
    sessionId.value = response.session_id;
  } catch (err: any) {
    console.error('Failed to start session:', err);
  }
};

const endSession = async (outcome: string = 'saved') => {
  if (!sessionId.value) return;
  
  try {
    await crewSheetStore.endSession(sessionId.value, outcome);
    sessionId.value = null;
  } catch (err: any) {
    console.error('Failed to end session:', err);
  }
};

const trackEdit = async (fieldName: string, originalValue: string, newValue: string, rowIndex: number) => {
  if (!sessionId.value) return;
  
  try {
    await crewSheetStore.trackEdit(
      sessionId.value,
      fieldName,
      originalValue,
      newValue,
      rowIndex,
      0 // edit_time_seconds will be calculated in store if needed
    );
  } catch (err: any) {
    console.error('Failed to track edit:', err);
  }
};

// Core functions
const loadSheet = async () => {
  loading.value = true;
  error.value = '';
  
  try {
    await crewSheetStore.fetchCrewSheet(sheetId.value);
    
    if (!currentSheet.value) {
      throw new Error('Failed to load crew sheet data');
    }
    
    const data = currentSheet.value.extracted_data;
    console.log('Raw extracted data:', data);
    
    // Handle different data formats
    let parsed;
    if (typeof data === 'string') {
      try {
        parsed = JSON.parse(data);
      } catch (parseErr) {
        console.error('Failed to parse extracted data JSON:', parseErr);
        parsed = {};
      }
    } else {
      parsed = data || {};
    }
    
    console.log('Parsed data structure:', parsed);

    // Extract headers with multiple fallback options
    let extractedHeaders = [];
    if (parsed.table_headers && Array.isArray(parsed.table_headers)) {
      extractedHeaders = parsed.table_headers;
    } else if (parsed.headers && Array.isArray(parsed.headers)) {
      extractedHeaders = parsed.headers;
    } else if (parsed.column_names && Array.isArray(parsed.column_names)) {
      extractedHeaders = parsed.column_names;
    } else if (parsed.employees && Array.isArray(parsed.employees) && parsed.employees.length > 0) {
      extractedHeaders = Object.keys(parsed.employees[0]);
    } else if (parsed.data && Array.isArray(parsed.data) && parsed.data.length > 0) {
      extractedHeaders = Object.keys(parsed.data[0]);
    } else if (parsed.rows && Array.isArray(parsed.rows) && parsed.rows.length > 0) {
      extractedHeaders = Object.keys(parsed.rows[0]);
    }
    
    headers.value = extractedHeaders.filter(h => h && typeof h === 'string');
    console.log('Extracted headers:', headers.value);

    // Ensure EMPLOYEE NAME header exists
    const hasEmployeeName = headers.value.some(h => 
      ['EMPLOYEE NAME', 'EMPLOYEE_NAME', 'name', 'Name', 'EMPLOYEE', 'employee'].includes(h)
    );

    if (!hasEmployeeName && headers.value.length > 0) {
      headers.value.unshift('EMPLOYEE NAME');
    }

    // Extract row data with multiple fallback options
    let extractedRows = [];
    if (parsed.employees && Array.isArray(parsed.employees)) {
      extractedRows = parsed.employees;
    } else if (parsed.data && Array.isArray(parsed.data)) {
      extractedRows = parsed.data;
    } else if (parsed.rows && Array.isArray(parsed.rows)) {
      extractedRows = parsed.rows;
    }
    
    console.log('Extracted rows:', extractedRows);
    
    // Ensure all rows have all header fields
    rows.value = extractedRows.map(row => {
      const normalizedRow: Record<string, string> = {};
      for (const header of headers.value) {
        // Handle special case for EMPLOYEE_NAME mapping to 'name' field
        if (header === 'EMPLOYEE_NAME' || header === 'EMPLOYEE NAME') {
          normalizedRow[header] = row.name || row.EMPLOYEE_NAME || row['EMPLOYEE NAME'] || '';
        } else {
          // Try direct match first, then variations
          normalizedRow[header] = row[header] || 
                                 row[header.toLowerCase()] || 
                                 row[header.replace(/[_\s]/g, '')] || 
                                 row[header.replace(/_/g, ' ')] || 
                                 '';
        }
      }
      return normalizedRow;
    });
    
    // Add default row if no data
    if (rows.value.length === 0 && headers.value.length > 0) {
      const defaultRow: Record<string, string> = {};
      headers.value.forEach(header => {
        defaultRow[header] = '';
      });
      rows.value = [defaultRow];
    }
    
    console.log('Final table state - headers:', headers.value, 'rows:', rows.value);
    
    isEdited.value = false;
    editCount.value = 0;
  } catch (err: any) {
    console.error('Failed to load sheet:', err);
    error.value = err.message || 'Failed to load sheet';
    
    // Fallback to empty table structure
    headers.value = ['EMPLOYEE NAME'];
    rows.value = [{ 'EMPLOYEE NAME': '' }];
  } finally {
    loading.value = false;
  }
};

const processCrewSheet = async () => {
  if (!currentSheet.value) return;
  
  processing.value = true;
  error.value = null;
  
  try {
    await startSession();
    await crewSheetStore.processCrewSheet(currentSheet.value.id);
    await crewSheetStore.fetchCrewSheet(currentSheet.value.id);
    loadSheet();
  } catch (err: any) {
    console.error('Processing failed:', err);
    error.value = err instanceof Error ? err.message : 'Processing failed';
  } finally {
    processing.value = false;
  }
};

// Lifecycle
onMounted(async () => {
  await loadSheet();
  await loadTemplateSuggestions();
  await loadLearningInsights();
  await checkReviewQueueStatus();
  await loadCompanyProfile();
});

onUnmounted(() => {
  if (sessionId.value) {
    endSession('abandoned');
  }
});

const addHeader = () => {
  const h = newHeader.value.trim();
  if (!h || headers.value.includes(h)) return;
  headers.value.push(h);
  for (const row of rows.value) row[h] = '';
  newHeader.value = '';
  isEdited.value = true;
  editCount.value++;
};

const removeHeader = (idx: number) => {
  if (headers.value[idx] === 'EMPLOYEE NAME') return;
  const h = headers.value[idx];
  headers.value.splice(idx, 1);
  for (const row of rows.value) delete row[h];
  isEdited.value = true;
  editCount.value++;
};

const addRow = () => {
  const newRow: Record<string, string> = {};
  for (const h of headers.value) newRow[h] = '';
  rows.value.push(newRow);
  isEdited.value = true;
  editCount.value++;
};

const deleteRow = (idx: number) => {
  rows.value.splice(idx, 1);
  isEdited.value = true;
  editCount.value++;
};

const updateCell = (rowIdx: number, header: string, value: string) => {
  rows.value[rowIdx][header] = value;
  isEdited.value = true;
};

const saveChanges = async () => {
  if (!isEdited.value) return;
  processing.value = true;
  error.value = '';

  try {
    console.log('Saving changes to backend...');

    const originalData = currentSheet.value?.extracted_data;
    let completeData = typeof originalData === 'string'
      ? JSON.parse(originalData)
      : originalData || {};

    if (sessionId.value) {
      console.log('Tracking edits for learning system...');
      const originalEmployees = completeData.employees || [];

      for (let i = 0; i < rows.value.length; i++) {
        const row = rows.value[i];
        if (!row._edited || !row._edited.length) continue;

        for (const fieldName of row._edited) {
          const newValue = row[fieldName];
          let originalValue = '';
          if (originalEmployees[i]) {
            originalValue = originalEmployees[i][fieldName] || '';
          }

          await trackEdit(fieldName, originalValue, newValue, i);
        }
      }
    }

    completeData = {
      ...completeData,
      table_headers: headers.value,
      employees: rows.value
    };

    if (completeData.data) completeData.data = rows.value;
    if (completeData.rows) completeData.rows = rows.value;

    await crewSheetStore.updateCrewSheetData(sheetId.value, completeData);
    isEdited.value = false;
    editCount.value = 0;

    await loadSheet();

    if (sessionId.value) {
      await endSession('saved');
    }
  } catch (err: any) {
    console.error('Save failed:', err);
    error.value = err.response?.data?.detail || 'Failed to save changes';
  } finally {
    processing.value = false;
  }
};

const downloadExcel = async () => {
  if (!rows.value || rows.value.length === 0) {
    alert('No data to export');
    return;
  }

  try {
    const wb = XLSX.utils.book_new();

    const employeeData = rows.value.map(employee => {
      const row: any = {};
      row['EMPLOYEE NAME'] = employee.name || '';

      headers.value.forEach(header => {
        if (!isEmployeeNameHeader(header)) {
          const displayHeader = formatHeaderForDisplay(header).replace(/\n/g, ' - ');
          row[displayHeader] = employee[header] || '';
        }
      });

      return row;
    });

    const ws = XLSX.utils.json_to_sheet(employeeData);
    XLSX.utils.book_append_sheet(wb, ws, 'Employees');

    if (headerInfo.value && typeof headerInfo.value === 'object' && Object.keys(headerInfo.value).length > 0) {
      const metadataEntries = Object.entries(headerInfo.value).map(([key, value]) => {
        return { Key: key.replace(/_/g, ' ').toUpperCase(), Value: value || '' };
      });

      if (metadataEntries.length > 0) {
        const metadataSheet = XLSX.utils.json_to_sheet(metadataEntries);
        XLSX.utils.book_append_sheet(wb, metadataSheet, 'Metadata');
      }
    }

    const date = new Date().toISOString().split('T')[0];
    const fileName = `crew_sheet_${date}.xlsx`;
    XLSX.writeFile(wb, fileName);
  } catch (error) {
    console.error('Error generating Excel:', error);
    alert('Error generating Excel file');
  }
};

const downloadImage = async () => {
  if (!currentSheet.value?.image) {
    alert('No image available for download');
    return;
  }

  try {
    const link = document.createElement('a');
    link.href = currentSheet.value.image;
    link.download = currentSheet.value?.name
      ? `${currentSheet.value.name.replace(/\s+/g, '_')}.jpg`
      : 'crew_sheet_image.jpg';

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  } catch (e) {
    console.error('Error downloading image:', e);
    alert('Error downloading image');
  }
};

const goBack = async () => {
  if (sessionId.value) {
    try {
      await endSession('abandoned');
    } catch (e) {
      console.warn('Error ending session:', e);
    }
  }
  router.push({ name: 'crewSheets' });
};

// Fetch sheet details on component mount
onMounted(async () => {
  try {
    loading.value = true;
    await crewSheetStore.fetchCrewSheet(sheetId.value.toString());

    // Start session for completed sheets
    if (currentSheet.value?.status === 'completed') {
      await startSession();
    }

  } catch (e) {
    if (e instanceof Error) {
      error.value = e.message;
    } else {
      error.value = 'Error loading crew sheet';
    }
  } finally {
    loading.value = false;
  }
});

// Clean up session on unmount
onUnmounted(async () => {
  if (sessionId.value) {
    try {
      await endSession('abandoned');
    } catch (e) {
      console.warn('Error ending session on unmount:', e);
    }
  }
});
</script>
