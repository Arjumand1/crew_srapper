<template>
  <v-container class="py-8 w-lg-75 w-100" fluid>
    <v-row class="mb-6 align-center mt-6 justify-space-between">
      <v-col cols="12" md="8">
        <div class="d-flex align-center gap-4">
          <v-icon size="x-large" color="primary">mdi-file-document-outline</v-icon>
          <span class="text-h4">{{ currentSheet?.name || 'Crew Sheet Details' }}</span>
        </div>
      </v-col>
      <v-col cols="12" md="4" class="d-flex justify-end align-center">
        <v-chip :color="statusColor(currentSheet?.status)" class="text-uppercase" size="large">
          {{ currentSheet?.status }}
        </v-chip>
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

          <!-- Editable Excel-like Table -->
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
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, nextTick, watch } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useCrewSheetStore } from '../stores/crewSheets';

// Utility to format summary/header labels for display
function formatLabel(label: string) {
  return label
    .replace(/_/g, ' ')
    .replace(/\b\w/g, l => l.toUpperCase());
}

function isEmployeeNameHeader(header) {
  if (!header) return false;
  const normalized = header.toString().toLowerCase().replace(/[_\s]/g, '');
  return normalized === 'employeename' || normalized === 'name' || normalized === 'employee';
}

function parseHierarchicalHeader(header) {
  if (!header || typeof header !== 'string') return { costCenter: null, task: null, jobType: header };
  
  // Common job-related keywords that indicate job type part of the header
  const jobKeywords = ['JOB', 'PIECE', 'WORK', 'HRS', 'HOURS', 'NO', 'PCS'];
  const parts = header.split('_');
  
  // If header is too short, treat it as a simple header
  if (parts.length < 3) {
    return { costCenter: null, task: null, jobType: header.replace(/_/g, ' ') };
  }
  
  // Find where job type starts in the header
  let jobTypeStartIndex = -1;
  for (let i = 0; i < parts.length; i++) {
    if (jobKeywords.includes(parts[i])) {
      jobTypeStartIndex = i;
      break;
    }
  }
  
  // If no job keywords found, use a default split (first=costCenter, middle=task, rest=jobType)
  if (jobTypeStartIndex === -1) {
    // Default to treating first part as cost center, second as task, rest as job type if 3+ parts
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
  
  // Extract cost center, task, and job type based on found index
  const costCenter = parts[0] || null;
  const task = jobTypeStartIndex > 1 ? parts.slice(1, jobTypeStartIndex).join(' ') : null;
  const jobType = parts.slice(jobTypeStartIndex).join(' ');
  
  return { costCenter, task, jobType };
}

function formatHeaderForDisplay(header) {
  if (!header) return '';
  
  // Handle employee name headers specially
  if (isEmployeeNameHeader(header)) {
    return 'EMPLOYEE NAME';
  }
  
  // Parse hierarchical structure
  const { costCenter, task, jobType } = parseHierarchicalHeader(header);
  
  // Build multi-line display with cost center on top, task in middle, job type at bottom
  let displayText = '';
  
  if (costCenter) {
    displayText += costCenter;
  }
  
  if (task) {
    displayText += (displayText ? '\n' : '') + task;
  }
  
  if (jobType) {
    displayText += (displayText ? '\n' : '') + jobType;
  }
  
  return displayText || header.replace(/_/g, ' ');
}

const router = useRouter();
const route = useRoute();
const crewSheetStore = useCrewSheetStore();

const sheetId = ref(route.params.id as string);
const loading = ref(false);
const error = ref('');
const isEdited = ref(false);
const saving = ref(false);
const processing = ref(false);

// Single source of truth for table
const headers = ref<string[]>([]); // e.g. ['EMPLOYEE NAME', 'Role', ...]
const rows = ref<Record<string, string>[]>([]); // array of objects, each key is header

// --- Header edit logic to preserve data ---
function handleHeaderRename(index: number, newName: string) {
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
}
// --- End header edit logic ---

const editingHeaders = ref(false);
const newHeader = ref('');
const headerEditKey = ref(0);

function toggleEditingHeaders() {
  editingHeaders.value = !editingHeaders.value;
  headerEditKey.value++;
}

// Refs for header inputs
const headerInputRefs = ref<any[]>([]);
function setHeaderInputRef(index: number) {
  return (el: any) => {
    headerInputRefs.value[index] = el;
  };
}

// Load data from backend
async function loadSheet() {
  loading.value = true;
  error.value = '';
  try {
    await crewSheetStore.fetchCrewSheet(sheetId.value);
    const data = crewSheetStore.currentCrewSheet?.extracted_data;
    let parsed = typeof data === 'string' ? JSON.parse(data) : data;
    // Try to get headers from several possible keys
    headers.value = parsed?.table_headers || parsed?.headers || parsed?.column_names || (parsed?.employees?.length ? Object.keys(parsed.employees[0]) : []);

    // Check for employee name column in various formats and ensure we only have one
    const hasEmployeeName = headers.value.some(h =>
      h === 'EMPLOYEE NAME' || h === 'EMPLOYEE_NAME' || h === 'name'
    );

    if (!hasEmployeeName && parsed?.employees?.length && parsed.employees[0].name !== undefined) {
      headers.value.unshift('EMPLOYEE NAME');
    }

    // Get rows from employees/data/rows
    rows.value = parsed?.employees || parsed?.data || parsed?.rows || [];
    // Ensure all rows have all headers
    for (const row of rows.value) {
      for (const h of headers.value) {
        if (!(h in row)) row[h] = '';
      }
    }
  } catch (e) {
    error.value = 'Failed to load sheet';
  } finally {
    loading.value = false;
  }
}

onMounted(loadSheet);

function addHeader() {
  const h = newHeader.value.trim();
  if (!h || headers.value.includes(h)) return;
  headers.value.push(h);
  for (const row of rows.value) row[h] = '';
  newHeader.value = '';
  isEdited.value = true;
}

function removeHeader(idx: number) {
  if (headers.value[idx] === 'EMPLOYEE NAME') return;
  const h = headers.value[idx];
  headers.value.splice(idx, 1);
  for (const row of rows.value) delete row[h];
  isEdited.value = true;
}

function addRow() {
  const newRow: Record<string, string> = {};
  for (const h of headers.value) newRow[h] = '';
  rows.value.push(newRow);
  isEdited.value = true;
}

function deleteRow(idx: number) {
  rows.value.splice(idx, 1);
  isEdited.value = true;
}

function updateCell(rowIdx: number, header: string, value: string) {
  rows.value[rowIdx][header] = value;
  isEdited.value = true;
}

async function saveChanges() {
  if (!isEdited.value) return;
  saving.value = true;
  try {
    console.log('Saving changes to backend...');
    console.log('Current table headers:', headers.value);
    console.log('Employee data sample:', rows.value[0]);

    // Get the complete original extracted data
    const originalData = currentSheet.value?.extracted_data;
    let completeData = typeof originalData === 'string'
      ? JSON.parse(originalData)
      : originalData || {};

    // Update with our edited data while preserving all original fields
    completeData = {
      ...completeData,  // Keep all original data (date, metadata, notes, etc.)
      table_headers: headers.value,
      employees: rows.value
    };

    // Also update alternative data structures if they exist
    if (completeData.data) {
      completeData.data = rows.value;
    }
    if (completeData.rows) {
      completeData.rows = rows.value;
    }

    console.log('Sending complete data to backend:', completeData);

    await crewSheetStore.updateCrewSheetData(sheetId.value, completeData);
    isEdited.value = false;

    // Refresh data from server
    console.log('Refreshing data from server...');
    await loadSheet();

  } catch (e) {
    console.error('Save failed:', e);
    alert('Save failed. Please try again.');
  } finally {
    saving.value = false;
  }
}

import * as XLSX from 'xlsx';

// Get the current crew sheet
const currentSheet = computed(() => {
  return crewSheetStore.currentCrewSheet;
});

const sortColumn = ref('');
const sortDirection = ref('asc');

// Sort function for the table
const sortTable = (header: string) => {
  // If clicking the same header, toggle direction
  if (sortColumn.value === header) {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc';
  } else {
    // New header, set as sort column and default to ascending
    sortColumn.value = header;
    sortDirection.value = 'asc';
  }
};

// Get the status class for styling
const statusColor = (status?: string) => {
  switch (status) {
    case 'pending': return 'warning';
    case 'processing': return 'info';
    case 'completed': return 'success';
    case 'failed': return 'error';
    default: return 'default';
  }
};

// Process the crew sheet
const processCrewSheet = async () => {
  if (!currentSheet.value) return;

  try {
    processing.value = true;
    error.value = '';
    await crewSheetStore.processCrewSheet(currentSheet.value.id);

    // Refresh the sheet data after processing completes
    console.log('Processing completed, refreshing sheet data...');
    await loadSheet();

  } catch (e) {
    if (e instanceof Error) {
      error.value = e.message;
    } else {
      error.value = 'Error processing crew sheet';
    }
  } finally {
    processing.value = false;
  }
};

// Method to download the data as Excel
const downloadExcel = () => {
  if (!rows.value || rows.value.length === 0) {
    alert('No data to export');
    return;
  }

  try {
    // Create a workbook
    const wb = XLSX.utils.book_new();

    // Create sheet for employee data
    const employeeData = rows.value.map(employee => {
      const row = {};
      
      // Always add employee name (ensuring it's never empty)
      row['EMPLOYEE NAME'] = employee.name || '';
      
      // Add all other headers
      headers.value.forEach(header => {
        if (!isEmployeeNameHeader(header)) {
          // Format header for Excel display - replace newlines with spaces for readability
          const displayHeader = formatHeaderForDisplay(header).replace(/\n/g, ' - ');
          row[displayHeader] = employee[header] || '';
        }
      });
      
      return row;
    });

    const ws = XLSX.utils.json_to_sheet(employeeData);
    XLSX.utils.book_append_sheet(wb, ws, 'Employees');

    // Add metadata sheet if available
    if (headerInfo.value && typeof headerInfo.value === 'object' && Object.keys(headerInfo.value).length > 0) {
      const metadataEntries = Object.entries(headerInfo.value).map(([key, value]) => {
        return { Key: key.replace(/_/g, ' ').toUpperCase(), Value: value || '' };
      });
      
      if (metadataEntries.length > 0) {
        const metadataSheet = XLSX.utils.json_to_sheet(metadataEntries);
        XLSX.utils.book_append_sheet(wb, metadataSheet, 'Metadata');
      }
    }

    // Add summary sheet if available
    if (summaryInfo.value && typeof summaryInfo.value === 'object' && Object.keys(summaryInfo.value).length > 0) {
      const summaryEntries = Object.entries(summaryInfo.value).map(([key, value]) => {
        return { Key: key.replace(/_/g, ' ').toUpperCase(), Value: value || '' };
      });
      
      if (summaryEntries.length > 0) {
        const summarySheet = XLSX.utils.json_to_sheet(summaryEntries);
        XLSX.utils.book_append_sheet(wb, summarySheet, 'Summary');
      }
    }

    // Generate filename with date
    const date = new Date().toISOString().split('T')[0];
    const fileName = `crew_sheet_${date}.xlsx`;

    // Write and download
    XLSX.writeFile(wb, fileName);
  } catch (error) {
    console.error('Error generating Excel:', error);
    alert('Error generating Excel file');
  }
};

// Extracted data computed properties
const headerInfo = computed(() => {
  if (!currentSheet.value?.extracted_data) return null;

  // Handle the case where extracted_data might be a string
  const data = typeof currentSheet.value.extracted_data === 'string'
    ? JSON.parse(currentSheet.value.extracted_data)
    : currentSheet.value.extracted_data;

  // If there's a header section in the data, return it
  if (data.header) {
    return data.header;
  }

  // If there are metadata fields that should be displayed in the header
  const headerFields = ['date', 'location', 'supervisor', 'project', 'title'];
  const extractedHeader: Record<string, any> = {};

  for (const field of headerFields) {
    if (data[field]) {
      extractedHeader[field] = data[field];
    }
  }

  return Object.keys(extractedHeader).length > 0 ? extractedHeader : null;
});

// Extract summary information for the summary card
const summaryInfo = computed(() => {
  // Defensive: always work with parsed data
  let data: any = null;
  if (!currentSheet.value?.extracted_data) return null;
  data = typeof currentSheet.value.extracted_data === 'string'
    ? JSON.parse(currentSheet.value.extracted_data)
    : currentSheet.value.extracted_data;

  // If there is a metadata object, use it directly
  if (data.metadata && typeof data.metadata === 'object') {
    return data.metadata;
  }

  // If there is a summary object, use it directly
  if (data.summary && typeof data.summary === 'object') {
    return data.summary;
  }

  // Try to extract summary fields
  const summary: Record<string, any> = {};
  // 1. Total Employees
  let employees = data.employees || data.rows || data.data || [];
  if (!Array.isArray(employees) && typeof employees === 'object') {
    employees = Object.values(employees);
  }
  summary['Total Employees'] = employees.length;

  // 2. Unique Roles (if role/position column exists)
  const roleKey = ['role', 'position', 'job'].find(k => employees.length && k in employees[0]);
  if (roleKey) {
    const uniqueRoles = Array.from(new Set(employees.map((e: any) => e[roleKey] || '').filter(Boolean)));
    summary['Unique Roles'] = uniqueRoles.length;
    summary['Roles'] = uniqueRoles.join(', ');
  }

  // 3. Total Hours (sum if any hour fields)
  const hourKey = ['hours', 'total_hours', 'worked_hours'].find(k => employees.length && k in employees[0]);
  if (hourKey) {
    const totalHours = employees.reduce((sum: number, e: any) => sum + (parseFloat(e[hourKey]) || 0), 0);
    summary['Total Hours'] = totalHours;
  }

  // 4. Total Pay (sum if any pay fields)
  const payKey = ['pay', 'total_pay', 'wages', 'cost'].find(k => employees.length && k in employees[0]);
  if (payKey) {
    const totalPay = employees.reduce((sum: number, e: any) => sum + (parseFloat(e[payKey]) || 0), 0);
    summary['Total Pay'] = totalPay;
  }

  // 5. Fallback: show first and last employee names if present
  const nameKey = ['name', 'employee_name', 'EMPLOYEE NAME'].find(k => employees.length && k in employees[0]);
  if (nameKey) {
    summary['First Employee'] = employees[0][nameKey];
    summary['Last Employee'] = employees[employees.length - 1][nameKey];
  }

  return summary;
});

const sortedEmployees = computed(() => {
  if (!rows.value || rows.value.length === 0) {
    return [];
  }

  let result = [...rows.value];

  // Sort based on sort column if specified
  if (sortColumn.value) {
    result.sort((a, b) => {
      const valueA = getCellValue(a, sortColumn.value);
      const valueB = getCellValue(b, sortColumn.value);

      if (sortDirection.value === 'asc') {
        return valueA.localeCompare(valueB);
      } else {
        return valueB.localeCompare(valueA);
      }
    });
  }

  return result;
});

const canDownload = computed(() => {
  return currentSheet.value?.status === 'completed' && rows.value.length > 0;
});

const isUncertain = (employee: any, header: string) => {
  if (!employee || !employee._uncertain) return false;
  
  // Map header to field name
  const fieldName = isEmployeeNameHeader(header) ? 'name' : header;
  
  // Check if field is in uncertain array
  if (Array.isArray(employee._uncertain) && employee._uncertain.includes(fieldName)) {
    return true;
  }
  
  return false;
};

// Get value for a cell, handling special cases
const getCellValue = (employee: any, header: string) => {
  if (!employee) return '';
  
  // Map header to field name
  const fieldName = isEmployeeNameHeader(header) ? 'name' : header;
  
  // Get the value
  const value = employee[fieldName];
  
  // Handle missing values
  if (value === null || value === undefined) return '';
  
  // Handle object values (from AI extraction)
  if (typeof value === 'object' && value !== null) {
    if ('value' in value) return value.value || '';
    if ('text' in value) return value.text || '';
  }
  
  // Handle checkmarks
  if (value === true || value === 'true' || value === '✓') {
    return '✓';
  }
  
  return String(value);
};

// Handle cell input
const handleCellInput = (rowIndex: number, header: string) => {
  // Map EMPLOYEE NAME to name field
  const fieldName = isEmployeeNameHeader(header) ? 'name' : header;

  // Mark as edited
  isEdited.value = true;

  // Track edited fields
  if (!rows.value[rowIndex]._edited) {
    rows.value[rowIndex]._edited = [];
  }

  if (!rows.value[rowIndex]._edited.includes(fieldName)) {
    rows.value[rowIndex]._edited.push(fieldName);
  }

  console.log(`Cell edited: Row ${rowIndex}, Header ${header}, Field ${fieldName}`);
};

// Download the crew sheet image
const downloadImage = async () => {
  if (!currentSheet.value?.image) {
    alert('No image available for download');
    return;
  }

  try {
    // Create a temporary link to download the image
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

// Navigate back to the list view
const goBack = () => {
  router.push({ name: 'crewSheets' });
};

// Fetch sheet details on component mount
onMounted(async () => {
  try {
    loading.value = true;
    await crewSheetStore.fetchCrewSheet(sheetId.value.toString());
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
</script>
