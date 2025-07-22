<template>
  <v-container class="py-8 w-lg-75 w-100" fluid>
    <v-row class="mb-6 align-center justify-space-between">
      <v-col cols="12" md="8">
        <div class="d-flex align-center gap-4">
          <v-icon size="x-large" color="primary">mdi-file-document-outline</v-icon>
          <span class="text-h4 font-weight-bold">{{ currentSheet?.name || 'Crew Sheet Details' }}</span>
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
            <v-btn v-if="currentSheet.status === 'pending'" color="primary" :loading="processing" :disabled="processing" @click="processCrewSheet">
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
            <v-col cols="12" md="6" v-if="summaryInfo">
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
              <v-btn color="secondary" @click="toggleHeaderEditing">
                {{ editingHeaders ? 'Done Editing Headers' : 'Edit Headers' }}
              </v-btn>
            </div>
            <v-table class="overflow-x-auto" fixed-header style="min-width: 900px;">
              <thead class="font-weight-bold">
                <tr>
                  <th class="text-center" style="min-width: 60px;">ID</th>
                  <th v-for="(header, index) in editingHeaders ? editableHeaders : tableHeaders" :key="header + '-' + index" class="text-center" style="min-width: 160px;">
                    <template v-if="editingHeaders">
                      <v-text-field
                        v-model="editableHeaders[index]"
                        density="compact"
                        hide-details
                        class="w-75 mx-auto"
                      >
                        <template #append-inner>
                          <v-btn
                            v-if="header !== 'EMPLOYEE NAME'"
                            icon
                            size="x-small"
                            color="error"
                            @click.stop="removeHeader(index)"
                            tabindex="-1"
                            style="height: 16px; width: 16px;"
                          >
                            <v-icon>mdi-close</v-icon>
                          </v-btn>
                        </template>
                      </v-text-field>
                    </template>
                    <template v-else>
                      <span @click="sortTable(header)" class="cursor-pointer">
                        {{ header }}
                        <v-icon v-if="sortColumn === header" size="x-small">
                          {{ sortDirection === 'asc' ? 'mdi-arrow-up' : 'mdi-arrow-down' }}
                        </v-icon>
                      </span>
                    </template>
                  </th>
                  <th v-if="editingHeaders" class="text-center" style="min-width: 140px;">
                    <v-text-field
                      v-model="newHeader"
                      density="compact"
                      hide-details
                      class="w-75 mx-auto"
                      placeholder="New header"
                      @keydown.enter="addHeader"
                    />
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
                  <td v-for="header in tableHeaders" :key="`${rowIndex}-${header}`" style="min-width: 160px;">
                    <v-text-field
                      v-model="editableEmployees[rowIndex][header === 'EMPLOYEE NAME' ? 'name' : header]"
                      density="compact"
                      hide-details
                      :class="{
                        'bg-yellow-lighten-4': isUncertain(employee, header),
                        'bg-blue-lighten-4': employee._edited && employee._edited.includes(header === 'EMPLOYEE NAME' ? 'name' : header),
                        'font-weight-bold': header === 'EMPLOYEE NAME',
                      }"
                    />
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
import { ref, computed, watch, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useCrewSheetStore } from '../stores/crewSheets';
import * as XLSX from 'xlsx';

// Initialize router and store
const router = useRouter();
const route = useRoute();
const crewSheetStore = useCrewSheetStore();

// Get the sheet ID from the route params
const sheetId = computed(() => {
    return route.params.id as string;
});

// Get the current crew sheet
const currentSheet = computed(() => {
    return crewSheetStore.currentCrewSheet;
});

// State variables
const loading = ref(false);
const processing = ref(false);
const saving = ref(false);
const error = ref('');
const isEdited = ref(false);
const editableEmployees = ref<any[]>([]);
const sortColumn = ref('');
const sortDirection = ref('asc');
const tableHeaders = ref<string[]>([]);
const editingHeaders = ref(false);
const editableHeaders = ref<string[]>([]);
const newHeader = ref('');

// Table headers initialization
const initTableHeaders = () => {
    if (!currentSheet.value || !currentSheet.value.extracted_data) {
        tableHeaders.value = [];
        return;
    }

    // Parse the extracted data if it's a string
    const extractedData = typeof currentSheet.value.extracted_data === 'string'
        ? JSON.parse(currentSheet.value.extracted_data)
        : currentSheet.value.extracted_data;


    // Try different possible fields where headers might be stored
    let headers = [];

    // First priority: table_headers array
    if (extractedData.table_headers && Array.isArray(extractedData.table_headers)) {
        headers = [...extractedData.table_headers];
    }
    // Second priority: headers array
    else if (extractedData.headers && Array.isArray(extractedData.headers)) {
        headers = [...extractedData.headers];
    }
    // Third priority: column_names array
    else if (extractedData.column_names && Array.isArray(extractedData.column_names)) {
        headers = [...extractedData.column_names];
    }
    // Fourth priority: extract keys from the first employee object
    else if (extractedData.employees && extractedData.employees.length > 0) {
        headers = Object.keys(extractedData.employees[0])
            .filter(key => key !== '_edited' && key !== 'uncertain'); // Exclude special properties
    }
    // Fifth priority: extract from data array if it exists
    else if (extractedData.data && extractedData.data.length > 0) {
        headers = Object.keys(extractedData.data[0])
            .filter(key => key !== '_edited' && key !== 'uncertain');
    }
    // Last priority: extract from rows array if it exists
    else if (extractedData.rows && extractedData.rows.length > 0) {
        headers = Object.keys(extractedData.rows[0])
            .filter(key => key !== '_edited' && key !== 'uncertain');
    }
    else {
        tableHeaders.value = [];
        return;
    }


    // Make sure "name" field is always displayed as "EMPLOYEE NAME"
    // and is always first in the headers list
    const nameIndex = headers.findIndex(h =>
        h.toUpperCase() === 'NAME' ||
        h.toUpperCase() === 'EMPLOYEE NAME' ||
        h.toUpperCase() === 'EMPLOYEE'
    );

    const idIndex = headers.findIndex(h =>
        h === '#' ||
        h.toUpperCase() === 'ID' ||
        h.toUpperCase() === 'NUMBER' ||
        h.toUpperCase() === 'EMPLOYEE NUMBER'
    );

    // Remove name and id from their current positions
    let nameHeader = null;
    let idHeader = null;

    if (nameIndex !== -1) {
        nameHeader = headers.splice(nameIndex, 1)[0];
    }

    if (idIndex !== -1) {
        idHeader = headers.splice(idIndex > nameIndex ? idIndex - 1 : idIndex, 1)[0];
    }

    // If we found a name header, standardize it to EMPLOYEE NAME and add it first
    const standardizedHeaders = [];

    if (idHeader) {
        standardizedHeaders.push(idHeader);
    }

    if (nameHeader) {
        standardizedHeaders.push('EMPLOYEE NAME');
    } else if (!headers.includes('EMPLOYEE NAME')) {
        standardizedHeaders.push('EMPLOYEE NAME');
    }

    // Add the rest of the headers
    standardizedHeaders.push(...headers);

    tableHeaders.value = standardizedHeaders;
};

// Initialize the employees data
const initEmployees = () => {
    if (!currentSheet.value || !currentSheet.value.extracted_data) {
        editableEmployees.value = [];
        return;
    }

    // Parse the extracted data if it's a string
    const extractedData = typeof currentSheet.value.extracted_data === 'string'
        ? JSON.parse(currentSheet.value.extracted_data)
        : currentSheet.value.extracted_data;


    // First priority: employees array
    if (extractedData.employees && Array.isArray(extractedData.employees)) {
        editableEmployees.value = JSON.parse(JSON.stringify(extractedData.employees));
    }
    // Second priority: data array
    else if (extractedData.data && Array.isArray(extractedData.data)) {
        editableEmployees.value = JSON.parse(JSON.stringify(extractedData.data));
    }
    // Third priority: rows array
    else if (extractedData.rows && Array.isArray(extractedData.rows)) {
        editableEmployees.value = JSON.parse(JSON.stringify(extractedData.rows));
    }
    else {
        editableEmployees.value = [];
    }

    // Ensure each employee has all the headers
    const headers = tableHeaders.value;
    editableEmployees.value.forEach(employee => {
        headers.forEach(header => {
            // Map EMPLOYEE NAME header to name property
            const fieldName = header === 'EMPLOYEE NAME' ? 'name' : header;

            // Initialize empty or missing fields
            if (!(fieldName in employee)) {
                employee[fieldName] = '';
            }
        });

        // Initialize tracking arrays
        employee._edited = [];
    });

};

// Toggle header editing mode
const toggleHeaderEditing = () => {
    if (editingHeaders.value) {
        // Finishing edit mode - apply changes
        applyHeaderChanges();
        editingHeaders.value = false;
    } else {
        // Starting edit mode - create a copy of the current headers
        editableHeaders.value = [...tableHeaders.value];
        editingHeaders.value = true;
    }
};

// Apply header changes when finishing edit mode
const applyHeaderChanges = () => {
    // Check if headers have changed
    const hasChanges = tableHeaders.value.length !== editableHeaders.value.length ||
        tableHeaders.value.some((header, index) =>
            header !== editableHeaders.value[index]
        );

    if (!hasChanges) return;

    // Create a mapping of old header names to new header names
    const headerChanges = new Map();
    const commonLength = Math.min(tableHeaders.value.length, editableHeaders.value.length);

    // Track headers that were renamed
    for (let i = 0; i < commonLength; i++) {
        const oldHeader = tableHeaders.value[i];
        const newHeader = editableHeaders.value[i];
        if (oldHeader !== newHeader) {
            headerChanges.set(oldHeader, newHeader);
        }
    }

    // Find any new headers that were added (not renames)
    const newHeaders = editableHeaders.value.filter(
        header => !tableHeaders.value.includes(header)
    );

    // Update the properties in all employees
    editableEmployees.value.forEach(employee => {
        // Handle renamed headers first
        headerChanges.forEach((newHeader, oldHeader) => {
            if (oldHeader in employee) {
                // Copy the value to the new property
                employee[newHeader] = employee[oldHeader];
                // Delete the old property
                delete employee[oldHeader];
            }
        });

        // Handle new headers
        newHeaders.forEach(header => {
            if (!(header in employee)) {
                employee[header] = '';
            }
        });
    });

    // Update the actual headers array
    tableHeaders.value = [...editableHeaders.value];

    // Mark as edited
    isEdited.value = true;
};

// Update editable header
const updateEditableHeader = (index: number, value: string) => {
    if (index >= 0 && index < editableHeaders.value.length) {
        editableHeaders.value[index] = value;
    }
};

// Add new header
const addHeader = () => {
    if (newHeader.value.trim() !== '') {
        const newHeaderName = newHeader.value.trim();
        editableHeaders.value.push(newHeaderName);

        // Initialize the new field for all employees
        // This ensures every employee has a value (empty string) for the new field
        // when applying the header changes later
        editableEmployees.value.forEach(employee => {
            if (!(newHeaderName in employee)) {
                employee[newHeaderName] = '';
            }
        });

        newHeader.value = '';
    }
};

// Remove header
const removeHeader = (index: number) => {
    if (index >= 0 && index < editableHeaders.value.length) {
        const headerToRemove = editableHeaders.value[index];

        // Don't allow removing the EMPLOYEE NAME header
        if (headerToRemove === 'EMPLOYEE NAME') {
            alert('Cannot remove the EMPLOYEE NAME header');
            return;
        }

        editableHeaders.value.splice(index, 1);
    }
};

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

watch(
    () => currentSheet.value,
    (newSheet) => {
        if (newSheet) {
            initTableHeaders();
            initEmployees();
        }
    },
    { immediate: true }
);

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
    if (!employees.value || employees.value.length === 0) {
        return;
    }

    try {
        // Create a new workbook
        const workbook = XLSX.utils.book_new();

        // Create a worksheet with only visible table data (not raw data)
        const wsData = [];

        // Add headers row (exclude action column)
        const headers = tableHeaders.value.filter(header => header !== 'Actions');
        wsData.push(headers);

        // Add employee data rows
        employees.value.forEach((employee: any, index: number) => {
            const row = [];

            // Add data for each header except action column
            headers.forEach((header) => {
                let cellValue = '';

                // Special handling for employee name - check multiple possible keys
                if (header === 'EMPLOYEE NAME' || header === 'Employee Name' || header === 'NAME') {
                    // Check various possible property names for employee name
                    cellValue = employee[header] || employee.name || employee.EMPLOYEE_NAME ||
                        employee.employee_name || employee['EMPLOYEE NAME'] || '';

                    // Debug logging to see what's available
                } else {
                    // Normal handling for other fields
                    cellValue = employee[header] || '';
                }

                // Handle uncertainty markers
                if (employee.uncertain && employee.uncertain[header]) {
                    cellValue += ' (uncertain)';
                }

                row.push(cellValue);
            });

            wsData.push(row);
        });

        // Create worksheet from the data
        const worksheet = XLSX.utils.aoa_to_sheet(wsData);

        // Add the worksheet to the workbook
        XLSX.utils.book_append_sheet(workbook, worksheet, 'Crew Sheet Data');

        // Generate Excel file with sheet name and date
        const sheetName = currentSheet.value?.name || `crew_sheet_${sheetId.value}`;
        const fileName = `${sheetName.replace(/\s+/g, '_')}_${new Date().toISOString().split('T')[0]}.xlsx`;
        XLSX.writeFile(workbook, fileName);

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

const employees = computed(() => {
    if (!currentSheet.value?.extracted_data) return [];

    // Handle the case where extracted_data might be a string
    const data = typeof currentSheet.value.extracted_data === 'string'
        ? JSON.parse(currentSheet.value.extracted_data)
        : currentSheet.value.extracted_data;

    // Look for employees in different possible locations
    if (data.employees && Array.isArray(data.employees)) {
        return data.employees;
    } else if (data.data && Array.isArray(data.data)) {
        return data.data;
    } else if (data.rows && Array.isArray(data.rows)) {
        return data.rows;
    }

    return [];
});

const summaryInfo = computed(() => {
    if (!currentSheet.value?.extracted_data) return null;

    // Handle the case where extracted_data might be a string
    const data = typeof currentSheet.value.extracted_data === 'string'
        ? JSON.parse(currentSheet.value.extracted_data)
        : currentSheet.value.extracted_data;

    if (data.metadata) {
        return data.metadata;
    }

    // Look for summary fields in various locations
    const summaryFields = ['total_hours', 'people_count', 'summary', 'notes'];
    const extractedSummary: Record<string, any> = {};

    for (const field of summaryFields) {
        if (data[field]) {
            extractedSummary[field] = data[field];
        }
    }

    return Object.keys(extractedSummary).length > 0 ? extractedSummary : null;
});

// Sorted employees for display
const sortedEmployees = computed(() => {
    if (!editableEmployees.value || editableEmployees.value.length === 0) {
        return [];
    }

    let result = [...editableEmployees.value];

    // Sort based on sort column if specified
    if (sortColumn.value) {
        result.sort((a, b) => {
            const valueA = getEmployeeValue(a, sortColumn.value);
            const valueB = getEmployeeValue(b, sortColumn.value);

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
    return currentSheet.value?.status === 'completed' && employees.value.length > 0;
});

const formatLabel = (key: string) => {
    return key.split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
};

const isUncertain = (employee: any, header: string) => {
    // Map EMPLOYEE NAME header to name field
    const fieldName = header === 'EMPLOYEE NAME' ? 'name' : header;

    // Check if the field is explicitly marked as uncertain
    if (employee.uncertain && Array.isArray(employee.uncertain) && employee.uncertain.includes(fieldName)) {
        return true;
    }

    // Check if the field is uncertain in object format
    const value = employee[fieldName];
    if (typeof value === 'object' && value !== null) {
        if ('uncertain' in value && value.uncertain) {
            return true;
        }
        if ('confidence' in value && value.confidence < 0.8) {
            return true;
        }
    }

    // Check if the string value contains uncertainty indicators
    if (typeof value === 'string') {
        const lowerValue = value.toLowerCase();
        if (lowerValue.includes('*') ||
            lowerValue.includes('?') ||
            lowerValue.includes('uncertain') ||
            lowerValue.includes('unclear')) {
            return true;
        }
    }

    return false;
};

// Get employee value for sorting and display
const getEmployeeValue = (employee: any, header: string) => {
    // Special case for 'EMPLOYEE NAME' header which maps to 'name' field
    const fieldName = header === 'EMPLOYEE NAME' ? 'name' : header;

    const value = employee[fieldName];

    // Handle object with value property
    if (value && typeof value === 'object' && 'value' in value) {
        return value.value || '';
    }

    return value || '';
};

// Get value for a cell, handling special cases
const getCellValue = (employee: any, header: string) => {
    // Map EMPLOYEE NAME header to name field
    const fieldName = header === 'EMPLOYEE NAME' ? 'name' : header;

    const value = employee[fieldName];

    // Handle null values
    if (value === null || value === undefined) return '';

    // Handle object format with value property
    if (typeof value === 'object' && value !== null && 'value' in value) {
        return value.value || '';
    }

    // Special handling for checkmarks
    if (value === true || value === 'true' || value === '✓' || value === 'X' || value === 'x') {
        return '✓';
    }

    return value;
};

// Handle cell input
const handleCellInput = (event: any, rowIndex: number, header: string) => {
    // Map EMPLOYEE NAME to name field
    const fieldName = header === 'EMPLOYEE NAME' ? 'name' : header;

    // Update employee data
    editableEmployees.value[rowIndex][fieldName] = event.target.value;

    // Mark as edited
    isEdited.value = true;

    // Track edited fields
    if (!editableEmployees.value[rowIndex]._edited) {
        editableEmployees.value[rowIndex]._edited = [];
    }

    if (!editableEmployees.value[rowIndex]._edited.includes(fieldName)) {
        editableEmployees.value[rowIndex]._edited.push(fieldName);
    }

};

// Prepare row data for a new employee
const addRow = () => {
    // Create a new empty row with all table headers
    const newRow: Record<string, string> = {};

    // Initialize all fields with empty strings
    tableHeaders.value.forEach(header => {
        if (header === 'EMPLOYEE NAME') {
            newRow['name'] = ''; // Map EMPLOYEE NAME to name field
        } else {
            newRow[header] = '';
        }
    });

    editableEmployees.value.push(newRow);
    isEdited.value = true;
};

// Delete a row with confirmation
const deleteRow = (index: number) => {
    if (confirm('Are you sure you want to delete this employee record?')) {
        editableEmployees.value.splice(index, 1);
        isEdited.value = true;
    }
};

// Save changes to server
const saveChanges = async () => {
    if (!isEdited.value) return;
    if (!currentSheet.value) return;

    try {
        saving.value = true;

        // Create a new copy of the extracted data
        let updatedData;

        // Handle the case where extracted_data might be a string
        if (typeof currentSheet.value.extracted_data === 'string') {
            updatedData = JSON.parse(currentSheet.value.extracted_data);

            // Update with our edited data
            updatedData.employees = editableEmployees.value;
            updatedData.table_headers = tableHeaders.value;

            // Ensure the structure is consistent
            if (!updatedData.employees && updatedData.data) {
                updatedData.data = editableEmployees.value;
            } else if (!updatedData.employees && updatedData.rows) {
                updatedData.rows = editableEmployees.value;
            }

            await crewSheetStore.updateCrewSheetData(
                currentSheet.value.id,
                updatedData
            );
        } else {
            updatedData = {
                ...currentSheet.value.extracted_data,
                employees: editableEmployees.value,
                table_headers: tableHeaders.value
            };

            // Ensure the structure is consistent
            if (!updatedData.employees && updatedData.data) {
                updatedData.data = editableEmployees.value;
                delete updatedData.employees;
            } else if (!updatedData.employees && updatedData.rows) {
                updatedData.rows = editableEmployees.value;
                delete updatedData.employees;
            }


            await crewSheetStore.updateCrewSheetData(
                currentSheet.value.id,
                updatedData
            );
        }

        isEdited.value = false;
        alert('Changes saved successfully');

        // Refresh the data from the server to show the updated version
        await crewSheetStore.fetchCrewSheet(sheetId.value.toString());

        // Re-initialize the view with the updated data
        initTableHeaders();
        initEmployees();

    } catch (e) {
        console.error('Error saving changes:', e);
        alert('Error saving changes. Please try again.');
    } finally {
        saving.value = false;
    }
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
        // Debug data after fetch completes
        initTableHeaders();
        initEmployees();
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
