<template>
    <div class="crew-sheet-detail">
        <div class="header">
            <h1>{{ currentSheet?.name || 'Crew Sheet Details' }}</h1>
            <div class="status-badge" :class="statusClass">
                {{ currentSheet?.status }}
            </div>
        </div>

        <div v-if="loading" class="loading">
            Loading crew sheet data...
        </div>

        <div v-if="error" class="error-message">
            {{ error }}
        </div>

        <div v-if="currentSheet && !loading" class="crew-sheet-container">
            <!-- Processing Error -->
            <div v-if="currentSheet.status === 'failed'" class="error-container">
                <h3>Processing Error</h3>
                <p>{{ currentSheet.error_message }}</p>
                <button @click="processCrewSheet" class="btn-retry" :disabled="processing">
                    {{ processing ? 'Retrying...' : 'Retry Processing' }}
                </button>
            </div>

            <!-- Actions -->
            <div class="actions">
                <button v-if="currentSheet.status === 'pending'" @click="processCrewSheet" class="btn-primary"
                    :disabled="processing">
                    {{ processing ? 'Starting Process...' : 'Process Sheet' }}
                </button>

                <button @click="downloadExcel" class="btn-secondary" :disabled="!canDownload">
                    <i class="fas fa-download"></i> Download Excel
                </button>

                <button @click="saveChanges" class="btn-primary" :disabled="!isEdited">
                    <i class="fas fa-save"></i> Save Changes
                </button>

                <button @click="goBack" class="btn-secondary">
                    Back to List
                </button>
            </div>

            <!-- Extracted Data as Excel -->
            <div v-if="currentSheet.status === 'completed' && currentSheet.extracted_data" class="extracted-data">
                <!-- Excel-like Editable Grid -->
                <div class="crew-sheet-data-section">
                    <h2>Extracted Data</h2>
                    <div class="sheet-info">
                        <h3>Sheet Information</h3>
                        <div class="info-grid">
                            <div v-for="(value, key) in headerInfo" :key="key" class="info-item">
                                <span class="info-label">{{ formatLabel(key) }}:</span>
                                <span class="info-value">{{ value }}</span>
                            </div>
                        </div>
                    </div>

                    <div class="excel-container">
                        <div class="table-controls">
                            <button @click="addRow" class="add-row-btn">
                                Add Row
                            </button>
                        </div>

                        <div class="excel-table-container">
                            <div class="excel-table">
                                <!-- Header row -->
                                <div class="excel-row excel-header-row">
                                    <!-- ID column header -->
                                    <div class="excel-cell excel-header-cell id-cell">
                                        ID
                                    </div>

                                    <!-- Data column headers -->
                                    <div v-for="header in tableHeaders" :key="header"
                                        class="excel-cell excel-header-cell"
                                        :class="{ 'name-cell': header === 'EMPLOYEE NAME' }" @click="sortTable(header)">
                                        {{ header }}
                                        <span v-if="sortColumn === header" class="sort-icon">
                                            {{ sortDirection === 'asc' ? '▲' : '▼' }}
                                        </span>
                                    </div>

                                    <!-- Action column header -->
                                    <div class="excel-cell excel-header-cell excel-actions-cell">
                                        Actions
                                    </div>
                                </div>

                                <!-- Data rows -->
                                <div v-for="(employee, rowIndex) in sortedEmployees" :key="rowIndex" class="excel-row">
                                    <!-- ID cell -->
                                    <div class="excel-cell id-cell">
                                        {{ rowIndex + 1 }}
                                    </div>

                                    <!-- Data cells -->
                                    <div v-for="header in tableHeaders" :key="`${rowIndex}-${header}`"
                                        class="excel-cell" :class="{
                                            'uncertain': isUncertain(employee, header),
                                            'edited': employee._edited && employee._edited.includes(header === 'EMPLOYEE NAME' ? 'name' : header),
                                            'name-cell': header === 'EMPLOYEE NAME'
                                        }">
                                        <input type="text" :value="getCellValue(employee, header)"
                                            @input="handleCellInput($event, rowIndex, header)"
                                            :class="{ 'checkmark': getCellValue(employee, header) === '✓' }" />
                                    </div>

                                    <!-- Action column -->
                                    <div class="excel-cell excel-actions-cell">
                                        <button @click="deleteRow(rowIndex)" class="excel-btn-delete">
                                            Delete
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Metadata Summary -->
                <div v-if="summaryInfo" class="summary-info">
                    <h3>Summary</h3>
                    <div class="info-grid">
                        <div v-for="(value, key) in summaryInfo" :key="key" class="info-item">
                            <span class="info-label">{{ formatLabel(key) }}:</span>
                            <span class="info-value">{{ value }}</span>
                        </div>
                    </div>
                </div>

                <!-- Raw JSON Data -->
                <div class="raw-json">
                    <details>
                        <summary>View Raw JSON Data</summary>
                        <pre>{{ JSON.stringify(currentSheet.extracted_data, null, 2) }}</pre>
                    </details>
                </div>
            </div>
        </div>
    </div>
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
// const tableHeaders = ref<string[]>([]);

// Table headers computed property
const tableHeaders = computed(() => {
    console.log("Computing table headers from currentSheet:", currentSheet.value);

    if (!currentSheet.value || !currentSheet.value.extracted_data) {
        console.log("No current sheet or extracted data");
        return [];
    }

    // Parse the extracted data if it's a string
    const extractedData = typeof currentSheet.value.extracted_data === 'string'
        ? JSON.parse(currentSheet.value.extracted_data)
        : currentSheet.value.extracted_data;

    console.log("Parsed extracted data:", extractedData);

    // Try different possible fields where headers might be stored
    let headers = [];

    // First priority: table_headers array
    if (extractedData.table_headers && Array.isArray(extractedData.table_headers)) {
        console.log("Using table_headers array");
        headers = [...extractedData.table_headers];
    }
    // Second priority: headers array
    else if (extractedData.headers && Array.isArray(extractedData.headers)) {
        console.log("Using headers array");
        headers = [...extractedData.headers];
    }
    // Third priority: column_names array
    else if (extractedData.column_names && Array.isArray(extractedData.column_names)) {
        console.log("Using column_names array");
        headers = [...extractedData.column_names];
    }
    // Fourth priority: extract keys from the first employee object
    else if (extractedData.employees && extractedData.employees.length > 0) {
        console.log("Extracting headers from first employee object");
        headers = Object.keys(extractedData.employees[0])
            .filter(key => key !== '_edited' && key !== 'uncertain'); // Exclude special properties
    }
    // Fifth priority: extract from data array if it exists
    else if (extractedData.data && extractedData.data.length > 0) {
        console.log("Extracting headers from first data object");
        headers = Object.keys(extractedData.data[0])
            .filter(key => key !== '_edited' && key !== 'uncertain');
    }
    // Last priority: extract from rows array if it exists
    else if (extractedData.rows && extractedData.rows.length > 0) {
        console.log("Extracting headers from first row object");
        headers = Object.keys(extractedData.rows[0])
            .filter(key => key !== '_edited' && key !== 'uncertain');
    }
    else {
        console.log("No headers found, using empty array");
        return [];
    }

    console.log("Initial headers:", headers);

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

    console.log("Final standardized headers:", standardizedHeaders);
    return standardizedHeaders;
});

// Initialize the employees data
const initEmployees = () => {
    console.log("Initializing employees data");
    if (!currentSheet.value || !currentSheet.value.extracted_data) {
        console.log("No current sheet or extracted data");
        editableEmployees.value = [];
        return;
    }

    // Parse the extracted data if it's a string
    const extractedData = typeof currentSheet.value.extracted_data === 'string'
        ? JSON.parse(currentSheet.value.extracted_data)
        : currentSheet.value.extracted_data;

    console.log("Parsed extracted data for employees:", extractedData);

    // First priority: employees array
    if (extractedData.employees && Array.isArray(extractedData.employees)) {
        console.log("Using employees array");
        editableEmployees.value = JSON.parse(JSON.stringify(extractedData.employees));
    }
    // Second priority: data array
    else if (extractedData.data && Array.isArray(extractedData.data)) {
        console.log("Using data array");
        editableEmployees.value = JSON.parse(JSON.stringify(extractedData.data));
    }
    // Third priority: rows array
    else if (extractedData.rows && Array.isArray(extractedData.rows)) {
        console.log("Using rows array");
        editableEmployees.value = JSON.parse(JSON.stringify(extractedData.rows));
    }
    else {
        console.log("No employees data found, using empty array");
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

    console.log("Initialized employees:", editableEmployees.value);
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
            console.log('Current Sheet changed, initializing employees');
            initEmployees();
        }
    },
    { immediate: true }
);

// Get the status class for styling
const statusClass = computed(() => {
    if (!currentSheet.value) return '';
    const status = currentSheet.value.status;
    return {
        'status-pending': status === 'pending',
        'status-processing': status === 'processing',
        'status-completed': status === 'completed',
        'status-failed': status === 'failed',
    };
});

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
        employees.value.forEach((employee, index) => {
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
                    console.log('Employee:', employee);
                    console.log('Name header:', header);
                    console.log('Available name values:', {
                        headerValue: employee[header],
                        name: employee.name,
                        employeeName: employee.employee_name,
                        employeeNameUppercase: employee['EMPLOYEE NAME']
                    });
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

        console.log('Excel file generated successfully:', fileName);
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

// Debug function to examine crew sheet data
const debugData = () => {
    console.log('Current Sheet:', currentSheet.value);
    console.log('Extracted Data Type:', typeof currentSheet.value?.extracted_data);
    console.log('Extracted Data:', currentSheet.value?.extracted_data);
    console.log('Parsed Employees:', employees.value);
    console.log('Editable Employees:', editableEmployees.value);
    console.log('Table Headers:', tableHeaders.value);
};

// Methods
const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }).format(date);
};

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

    console.log(`Edited ${fieldName} in row ${rowIndex}`);
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
            updatedData.employees = editableEmployees.value;

            await crewSheetStore.updateCrewSheetData(
                currentSheet.value.id,
                JSON.stringify(updatedData)
            );
        } else {
            updatedData = {
                ...currentSheet.value.extracted_data,
                employees: editableEmployees.value
            };

            await crewSheetStore.updateCrewSheetData(
                currentSheet.value.id,
                updatedData
            );
        }

        isEdited.value = false;
        alert('Changes saved successfully');
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
        setTimeout(debugData, 1000);
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
<style scoped>

.crew-sheet-detail {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
}

.header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2rem;
}

.status-badge {
    padding: 0.5rem 1rem;
    border-radius: 20px;
    font-weight: bold;
    text-transform: uppercase;
    font-size: 0.8rem;
}

.status-pending {
    background-color: #fff3cd;
    color: #856404;
}

.status-processing {
    background-color: #cce5ff;
    color: #004085;
}

.status-completed {
    background-color: #d4edda;
    color: #155724;
}

.status-failed {
    background-color: #f8d7da;
    color: #721c24;
}

.loading {
    text-align: center;
    padding: 2rem;
    font-size: 1.2rem;
    color: #666;
}

.error-message {
    background-color: #f8d7da;
    color: #721c24;
    padding: 1rem;
    border-radius: 4px;
    margin-bottom: 1rem;
}

.crew-sheet-container {
    display: flex;
    flex-direction: column;
    gap: 2rem;
}

.actions {
    display: flex;
    gap: 1rem;
    margin: 1rem 0;
}

.btn-primary {
    background-color: #4caf50;
    color: white;
    border: none;
    padding: 0.75rem 1.5rem;
    font-size: 1rem;
    border-radius: 4px;
    cursor: pointer;
}

.btn-primary:disabled {
    background-color: #a5d6a7;
    cursor: not-allowed;
}

.btn-secondary {
    background-color: #6c757d;
    color: white;
    border: none;
    padding: 0.75rem 1.5rem;
    font-size: 1rem;
    border-radius: 4px;
    cursor: pointer;
}

.btn-secondary:disabled {
    background-color: #adb5bd;
    cursor: not-allowed;
}

.error-container {
    background-color: #f8d7da;
    padding: 1rem;
    border-radius: 8px;
    margin: 1rem 0;
}

.btn-retry {
    background-color: #4caf50;
    color: white;
    border: none;
    padding: 0.75rem 1.5rem;
    font-size: 1rem;
    border-radius: 4px;
    cursor: pointer;
}

.btn-retry:disabled {
    background-color: #a5d6a7;
    cursor: not-allowed;
}

.extracted-data {
    background-color: #f9f9f9;
    padding: 2rem;
    border-radius: 8px;
    margin-top: 2rem;
}

.header-info,
.summary-info {
    margin-bottom: 2rem;
}

.info-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1rem;
}

.info-item {
    display: flex;
    gap: 0.5rem;
}

.info-label {
    font-weight: bold;
}

/* Excel-like Grid Styles */
.excel-grid-container {
    margin: 2rem 0;
    width: 100%;
    overflow-x: auto;
}

.excel-toolbar {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 0.5rem;
}

.excel-btn {
    background-color: #4caf50;
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.9rem;
}

.excel-btn-delete {
    background-color: #ff4757;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 5px 10px;
    cursor: pointer;
    font-size: 0.8rem;
    transition: background-color 0.2s;
}

.excel-btn-delete:hover {
    background-color: #ff6b81;
}

.excel-grid {
    border: 1px solid #999;
    border-radius: 4px;
    overflow: hidden;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
}

.excel-header-row {
    display: flex;
    background-color: #e6e6e6;
    font-weight: bold;
}

.excel-header-cell {
    flex: 1;
    min-width: 150px;
    padding: 0.75rem;
    border-right: 1px solid #999;
    position: relative;
    cursor: pointer;
    color: #333;
}

.excel-header-cell:hover {
    background-color: #d9d9d9;
}

.sort-indicator {
    margin-left: 5px;
    font-size: 10px;
}

.excel-row {
    display: flex;
    border-top: 1px solid #999;
}

.excel-row:nth-child(even) {
    background-color: #f2f2f2;
}

.excel-row:nth-child(odd) {
    background-color: #ffffff;
}

.excel-cell {
    flex: 1;
    min-width: 150px;
    padding: 0;
    border-right: 1px solid #999;
    position: relative;
}

.excel-actions-col {
    flex: 0 0 100px;
    min-width: 100px;
}

.excel-actions-cell {
    flex: 0 0 100px;
    min-width: 100px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.excel-cell input {
    width: 100%;
    height: 100%;
    border: none;
    padding: 0.75rem;
    background: transparent;
    color: #333;
}

.excel-cell input:focus {
    outline: 2px solid #4caf50;
    background-color: #efffef;
}

.excel-cell input.checkmark {
    text-align: center;
    font-weight: bold;
    color: green !important;
}

/* Special styling for the name column */
.excel-cell.name-cell input {
    font-weight: 600;
    color: #000 !important;
    background-color: #f5f5f5;
}

/* Show debug info for cell content */
.excel-cell::before {
    position: absolute;
    top: -15px;
    left: 0;
    font-size: 8px;
    color: #999;
    display: none;
    /* Set to flex for debugging */
}

.excel-cell.uncertain {
    background-color: #fff8e1;
}

.excel-cell.uncertain input {
    color: #d32f2f;
    font-style: italic;
}

.excel-cell.uncertain::after {
    content: "?";
    color: #d32f2f;
    font-weight: bold;
    position: absolute;
    top: 2px;
    right: 5px;
    font-size: 12px;
    background-color: #ffecb3;
    border-radius: 50%;
    width: 16px;
    height: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.excel-cell.edited {
    background-color: #e3f2fd;
}

.excel-cell.edited input {
    color: #1565c0;
}

.raw-json {
    margin-top: 2rem;
    border-top: 1px solid #ddd;
    padding-top: 2rem;
}

.raw-json summary {
    cursor: pointer;
    color: #007bff;
    font-weight: bold;
    margin-bottom: 1rem;
}

.raw-json pre {
    background-color: #f8f9fa;
    padding: 1rem;
    border-radius: 4px;
    overflow-x: auto;
    font-size: 0.9rem;
}

.crew-sheet-data-section {
    background-color: white;
    border-radius: 8px;
    padding: 20px;
    margin-top: 20px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

/* Table styles */
.excel-container {
    margin-top: 20px;
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.excel-table-container {
    overflow-x: auto;
    /* Make it horizontally scrollable */
    border: 1px solid #ddd;
    border-radius: 4px;
}

.excel-table {
    min-width: 100%;
    width: max-content;
    /* Allow the table to grow based on content */
}

.excel-row {
    display: flex;
    border-bottom: 1px solid #ddd;
}

.excel-row:nth-child(even) {
    background-color: #f9f9f9;
}

.excel-cell {
    padding: 8px;
    border-right: 1px solid #ddd;
    min-width: 120px;
    display: flex;
    align-items: center;
}

.id-cell {
    min-width: 50px;
    width: 50px;
    justify-content: center;
    font-weight: bold;
    background-color: #f0f0f0;
}
</style>
