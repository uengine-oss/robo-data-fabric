<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useQueryStore } from '../stores/query';
import { useDatasourcesStore } from '../stores/datasources';
import {
  PlusIcon,
  TableCellsIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
} from '@heroicons/vue/24/outline';

const queryStore = useQueryStore();
const datasourcesStore = useDatasourcesStore();

// Form state
const tableName = ref('');
const selectedDatabase = ref('');
const selectedTable = ref('');
const selectedColumns = ref<string[]>([]);
const whereClause = ref('');
const limitRows = ref<number | undefined>(undefined);
const creating = ref(false);
const createSuccess = ref(false);
const availableTables = ref<string[]>([]);
const availableColumns = ref<{name: string; type: string}[]>([]);

// Generated SQL preview
const sqlPreview = computed(() => {
  if (!tableName.value || !selectedDatabase.value || !selectedTable.value) {
    return '-- Fill in the form to generate SQL';
  }
  
  const cols = selectedColumns.value.length > 0 
    ? selectedColumns.value.join(', ') 
    : '*';
  
  let sql = `CREATE TABLE mindsdb.${tableName.value} AS\nSELECT ${cols}\nFROM ${selectedDatabase.value}.${selectedTable.value}`;
  
  if (whereClause.value) {
    sql += `\nWHERE ${whereClause.value}`;
  }
  
  if (limitRows.value) {
    sql += `\nLIMIT ${limitRows.value}`;
  }
  
  return sql + ';';
});

onMounted(async () => {
  await datasourcesStore.fetchDatasources();
});

async function onDatabaseChange() {
  selectedTable.value = '';
  selectedColumns.value = [];
  availableColumns.value = [];
  
  if (selectedDatabase.value) {
    const response = await datasourcesStore.fetchTables(selectedDatabase.value);
    availableTables.value = datasourcesStore.tables;
  }
}

async function onTableChange() {
  selectedColumns.value = [];
  
  if (selectedDatabase.value && selectedTable.value) {
    const schema = await import('../api/client').then(m => 
      m.datasourcesApi.getTableSchema(selectedDatabase.value, selectedTable.value)
    );
    availableColumns.value = schema.columns.map(c => ({ name: c.name, type: c.type }));
  }
}

function toggleColumn(columnName: string) {
  const idx = selectedColumns.value.indexOf(columnName);
  if (idx > -1) {
    selectedColumns.value.splice(idx, 1);
  } else {
    selectedColumns.value.push(columnName);
  }
}

function selectAllColumns() {
  if (selectedColumns.value.length === availableColumns.value.length) {
    selectedColumns.value = [];
  } else {
    selectedColumns.value = availableColumns.value.map(c => c.name);
  }
}

async function createTable() {
  if (!tableName.value || !selectedDatabase.value || !selectedTable.value) {
    return;
  }
  
  creating.value = true;
  queryStore.clearError();
  
  const success = await queryStore.createMaterializedTable(
    tableName.value,
    selectedDatabase.value,
    selectedTable.value,
    selectedColumns.value.length > 0 ? selectedColumns.value : ['*'],
    whereClause.value || undefined,
    limitRows.value
  );
  
  creating.value = false;
  
  if (success) {
    createSuccess.value = true;
    // Reset form after delay
    setTimeout(() => {
      createSuccess.value = false;
      tableName.value = '';
      selectedTable.value = '';
      selectedColumns.value = [];
      whereClause.value = '';
      limitRows.value = undefined;
    }, 2000);
  }
}
</script>

<template>
  <div class="space-y-8">
    <!-- Header -->
    <div>
      <h1 class="text-3xl font-bold text-minds-text">Materialized Tables</h1>
      <p class="text-minds-muted mt-1">Create cached tables from external data sources</p>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Form -->
      <div class="card">
        <h2 class="text-lg font-semibold text-minds-text mb-6 flex items-center gap-2">
          <PlusIcon class="w-5 h-5 text-minds-accent" />
          Create Materialized Table
        </h2>

        <!-- Success Message -->
        <div v-if="createSuccess" class="mb-6 p-4 bg-minds-accent/10 border border-minds-accent/30 rounded-lg flex items-center gap-3">
          <CheckCircleIcon class="w-6 h-6 text-minds-accent" />
          <p class="text-minds-accent">Table created successfully!</p>
        </div>

        <!-- Error Message -->
        <div v-if="queryStore.error" class="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg flex items-center gap-3">
          <ExclamationCircleIcon class="w-6 h-6 text-red-400" />
          <p class="text-red-400 text-sm">{{ queryStore.error }}</p>
        </div>

        <form @submit.prevent="createTable" class="space-y-5">
          <!-- Table Name -->
          <div>
            <label class="block text-sm font-medium text-minds-text mb-1">
              New Table Name *
            </label>
            <input
              v-model="tableName"
              type="text"
              class="input-field"
              placeholder="cached_data"
              required
            />
            <p class="text-xs text-minds-muted mt-1">
              Table will be created in mindsdb database
            </p>
          </div>

          <!-- Source Database -->
          <div>
            <label class="block text-sm font-medium text-minds-text mb-1">
              Source Database *
            </label>
            <select
              v-model="selectedDatabase"
              @change="onDatabaseChange"
              class="input-field"
              required
            >
              <option value="">Select a database</option>
              <option
                v-for="ds in datasourcesStore.datasources"
                :key="ds.name"
                :value="ds.name"
              >
                {{ ds.name }} ({{ ds.engine }})
              </option>
            </select>
          </div>

          <!-- Source Table -->
          <div>
            <label class="block text-sm font-medium text-minds-text mb-1">
              Source Table *
            </label>
            <select
              v-model="selectedTable"
              @change="onTableChange"
              class="input-field"
              :disabled="!selectedDatabase"
              required
            >
              <option value="">Select a table</option>
              <option
                v-for="table in availableTables"
                :key="table"
                :value="table"
              >
                {{ table }}
              </option>
            </select>
          </div>

          <!-- Columns Selection -->
          <div v-if="availableColumns.length > 0">
            <div class="flex items-center justify-between mb-2">
              <label class="block text-sm font-medium text-minds-text">
                Columns ({{ selectedColumns.length || 'All' }})
              </label>
              <button
                type="button"
                @click="selectAllColumns"
                class="text-xs text-minds-accent hover:text-minds-accent-hover"
              >
                {{ selectedColumns.length === availableColumns.length ? 'Deselect All' : 'Select All' }}
              </button>
            </div>
            <div class="bg-minds-surface rounded-lg p-3 max-h-48 overflow-y-auto space-y-2">
              <label
                v-for="col in availableColumns"
                :key="col.name"
                class="flex items-center gap-3 cursor-pointer hover:bg-minds-border/30 p-2 rounded"
              >
                <input
                  type="checkbox"
                  :checked="selectedColumns.includes(col.name)"
                  @change="toggleColumn(col.name)"
                  class="w-4 h-4 rounded border-minds-border bg-minds-surface text-minds-accent focus:ring-minds-accent"
                />
                <span class="text-minds-text font-mono text-sm">{{ col.name }}</span>
                <span class="text-minds-muted text-xs">{{ col.type }}</span>
              </label>
            </div>
          </div>

          <!-- WHERE Clause -->
          <div>
            <label class="block text-sm font-medium text-minds-text mb-1">
              WHERE Clause (optional)
            </label>
            <input
              v-model="whereClause"
              type="text"
              class="input-field font-mono text-sm"
              placeholder="column > 100 AND status = 'active'"
            />
          </div>

          <!-- LIMIT -->
          <div>
            <label class="block text-sm font-medium text-minds-text mb-1">
              LIMIT (optional)
            </label>
            <input
              v-model.number="limitRows"
              type="number"
              class="input-field"
              placeholder="1000"
              min="1"
            />
          </div>

          <!-- Submit -->
          <button
            type="submit"
            :disabled="creating || !tableName || !selectedDatabase || !selectedTable"
            class="w-full btn-primary disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            <TableCellsIcon class="w-5 h-5" />
            {{ creating ? 'Creating...' : 'Create Materialized Table' }}
          </button>
        </form>
      </div>

      <!-- SQL Preview -->
      <div class="card">
        <h2 class="text-lg font-semibold text-minds-text mb-6">SQL Preview</h2>
        <div class="bg-minds-surface rounded-lg p-4 font-mono text-sm">
          <pre class="text-minds-text whitespace-pre-wrap">{{ sqlPreview }}</pre>
        </div>

        <div class="mt-6 p-4 bg-minds-surface rounded-lg">
          <h3 class="text-sm font-medium text-minds-text mb-3">What is a Materialized Table?</h3>
          <ul class="text-sm text-minds-muted space-y-2">
            <li>• Creates a copy of data from an external source into MindsDB</li>
            <li>• Data is cached locally for faster query performance</li>
            <li>• Useful for frequently accessed data or complex joins</li>
            <li>• Can be used with ML models for training and predictions</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>
