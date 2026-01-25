<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useDatasourcesStore } from '../stores/datasources';
import {
  PlusIcon,
  TrashIcon,
  ChevronRightIcon,
  XMarkIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
} from '@heroicons/vue/24/outline';
import type { DataSourceTypeConfig, ConnectionFormData } from '../types';

const store = useDatasourcesStore();

// Modal state
const showAddModal = ref(false);
const selectedType = ref<DataSourceTypeConfig | null>(null);
const formData = ref<ConnectionFormData>({});
const connectionName = ref('');
const creating = ref(false);
const createSuccess = ref(false);

// Data source icons
const icons: Record<string, string> = {
  mysql: '🐬',
  postgresql: '🐘',
  postgres: '🐘',
  neo4j: '🔵',
  web: '🌐',
  openai: '🤖',
  minds_endpoint: '🤖',
  mongodb: '🍃',
  redis: '🔴',
  elasticsearch: '🔍',
};

onMounted(async () => {
  await Promise.all([
    store.fetchTypes(),
    store.fetchDatasources(),
  ]);
});

function openAddModal() {
  showAddModal.value = true;
  selectedType.value = null;
  formData.value = {};
  connectionName.value = '';
  createSuccess.value = false;
}

function selectType(type: DataSourceTypeConfig) {
  selectedType.value = type;
  formData.value = {};
  // Set default values
  type.fields.forEach(field => {
    if (field.default !== undefined) {
      formData.value[field.name] = field.default;
    }
  });
}

function closeModal() {
  showAddModal.value = false;
  selectedType.value = null;
  formData.value = {};
  connectionName.value = '';
  createSuccess.value = false;
}

async function createConnection() {
  if (!selectedType.value || !connectionName.value) return;
  
  creating.value = true;
  store.clearError();
  
  const success = await store.createDatasource(
    connectionName.value,
    selectedType.value.type,
    formData.value
  );
  
  creating.value = false;
  
  if (success) {
    createSuccess.value = true;
    setTimeout(() => {
      closeModal();
    }, 1500);
  }
}

async function deleteSource(name: string) {
  if (confirm(`Are you sure you want to delete "${name}"?`)) {
    await store.deleteDatasource(name);
  }
}

function selectSource(source: any) {
  store.selectDatasource(source);
}
</script>

<template>
  <div class="space-y-8">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-minds-text">Data Sources</h1>
        <p class="text-minds-muted mt-1">Connect and manage your data sources</p>
      </div>
      <button @click="openAddModal" class="btn-primary flex items-center gap-2">
        <PlusIcon class="w-5 h-5" />
        Add Data Source
      </button>
    </div>

    <!-- Main Content -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Data Sources List -->
      <div class="lg:col-span-1">
        <div class="card">
          <h2 class="text-lg font-semibold text-minds-text mb-4">Connected Sources</h2>
          
          <div v-if="store.loading" class="text-center py-8">
            <div class="animate-spin w-8 h-8 border-2 border-minds-accent border-t-transparent rounded-full mx-auto"></div>
          </div>
          
          <div v-else-if="!store.hasDatasources" class="text-center py-8">
            <p class="text-minds-muted">No data sources connected</p>
            <button @click="openAddModal" class="text-minds-accent hover:text-minds-accent-hover mt-2">
              Add your first source
            </button>
          </div>
          
          <div v-else class="space-y-2">
            <button
              v-for="source in store.sortedDatasources"
              :key="source.name"
              @click="selectSource(source)"
              :class="[
                'w-full flex items-center gap-3 p-3 rounded-lg transition-all text-left',
                store.selectedDatasource?.name === source.name
                  ? 'bg-minds-accent/10 border border-minds-accent/30'
                  : 'hover:bg-minds-surface border border-transparent'
              ]"
            >
              <span class="text-2xl">{{ icons[source.engine] || '📦' }}</span>
              <div class="flex-1 min-w-0">
                <p class="font-medium text-minds-text truncate">{{ source.name }}</p>
                <p class="text-xs text-minds-muted">{{ source.engine }}</p>
              </div>
              <button
                @click.stop="deleteSource(source.name)"
                class="p-1 text-minds-muted hover:text-red-400 transition-colors"
              >
                <TrashIcon class="w-4 h-4" />
              </button>
            </button>
          </div>
        </div>
      </div>

      <!-- Table Explorer -->
      <div class="lg:col-span-2">
        <div class="card h-full">
          <template v-if="store.selectedDatasource">
            <div class="flex items-center gap-2 mb-4">
              <span class="text-2xl">{{ icons[store.selectedDatasource.engine] || '📦' }}</span>
              <h2 class="text-lg font-semibold text-minds-text">
                {{ store.selectedDatasource.name }}
              </h2>
            </div>

            <!-- Tables List -->
            <div class="mb-6">
              <h3 class="text-sm font-medium text-minds-muted mb-2">Tables</h3>
              <div v-if="store.tables.length === 0" class="text-minds-muted text-sm">
                No tables found
              </div>
              <div v-else class="flex flex-wrap gap-2">
                <button
                  v-for="table in store.tables"
                  :key="table"
                  @click="store.selectTable(table)"
                  :class="[
                    'px-3 py-1 rounded-lg text-sm transition-all',
                    store.selectedTable === table
                      ? 'bg-minds-accent text-minds-primary'
                      : 'bg-minds-surface text-minds-text hover:bg-minds-border'
                  ]"
                >
                  {{ table }}
                </button>
              </div>
            </div>

            <!-- Table Schema & Data -->
            <template v-if="store.selectedTable">
              <!-- Schema -->
              <div v-if="store.tableSchema" class="mb-6">
                <h3 class="text-sm font-medium text-minds-muted mb-2">Schema</h3>
                <div class="bg-minds-surface rounded-lg p-4 overflow-x-auto">
                  <table class="w-full text-sm">
                    <thead>
                      <tr class="text-left text-minds-muted">
                        <th class="pb-2">Column</th>
                        <th class="pb-2">Type</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="col in store.tableSchema.columns" :key="col.name" class="text-minds-text">
                        <td class="py-1 font-mono">{{ col.name }}</td>
                        <td class="py-1 text-minds-accent">{{ col.type }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <!-- Sample Data -->
              <div v-if="store.tableData">
                <h3 class="text-sm font-medium text-minds-muted mb-2">
                  Sample Data ({{ store.tableData.total_rows }} rows)
                </h3>
                <div class="bg-minds-surface rounded-lg overflow-x-auto">
                  <table class="data-table">
                    <thead>
                      <tr>
                        <th v-for="col in store.tableData.columns" :key="col">{{ col }}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(row, idx) in store.tableData.data" :key="idx">
                        <td v-for="(cell, cellIdx) in row" :key="cellIdx">
                          {{ cell ?? 'null' }}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </template>
          </template>

          <template v-else>
            <div class="h-full flex items-center justify-center">
              <div class="text-center">
                <p class="text-minds-muted">Select a data source to explore its tables</p>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>

    <!-- Add Data Source Modal -->
    <Teleport to="body">
      <div
        v-if="showAddModal"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
      >
        <div class="absolute inset-0 bg-black/70" @click="closeModal"></div>
        <div class="relative bg-minds-secondary border border-minds-border rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
          <!-- Modal Header -->
          <div class="flex items-center justify-between p-6 border-b border-minds-border">
            <h2 class="text-xl font-semibold text-minds-text">
              {{ selectedType ? `Add ${selectedType.display_name} Connection` : 'Add Data Source' }}
            </h2>
            <button @click="closeModal" class="text-minds-muted hover:text-minds-text">
              <XMarkIcon class="w-6 h-6" />
            </button>
          </div>

          <!-- Modal Body -->
          <div class="p-6 overflow-y-auto max-h-[60vh]">
            <!-- Success Message -->
            <div v-if="createSuccess" class="flex flex-col items-center py-8">
              <CheckCircleIcon class="w-16 h-16 text-minds-accent mb-4" />
              <p class="text-lg font-medium text-minds-text">Connection created successfully!</p>
            </div>

            <!-- Type Selection -->
            <div v-else-if="!selectedType">
              <p class="text-minds-muted mb-4">Select a data source type:</p>
              <div class="grid grid-cols-2 sm:grid-cols-3 gap-4">
                <button
                  v-for="type in store.datasourceTypes"
                  :key="type.type"
                  @click="selectType(type)"
                  class="p-4 rounded-xl bg-minds-surface border border-minds-border hover:border-minds-accent/50 transition-all text-center group"
                >
                  <span class="text-3xl mb-2 block">{{ icons[type.type] || '📦' }}</span>
                  <p class="font-medium text-minds-text group-hover:text-minds-accent transition-colors">
                    {{ type.display_name }}
                  </p>
                </button>
              </div>
            </div>

            <!-- Connection Form -->
            <div v-else>
              <button
                @click="selectedType = null"
                class="text-minds-accent hover:text-minds-accent-hover mb-4 flex items-center gap-1"
              >
                ← Back to types
              </button>

              <form @submit.prevent="createConnection" class="space-y-4">
                <!-- Connection Name -->
                <div>
                  <label class="block text-sm font-medium text-minds-text mb-1">
                    Connection Name *
                  </label>
                  <input
                    v-model="connectionName"
                    type="text"
                    class="input-field"
                    placeholder="my_database"
                    required
                  />
                </div>

                <!-- Dynamic Fields -->
                <div v-for="field in selectedType.fields" :key="field.name">
                  <label class="block text-sm font-medium text-minds-text mb-1">
                    {{ field.label }} {{ field.required ? '*' : '' }}
                  </label>
                  <input
                    v-model="formData[field.name]"
                    :type="field.type === 'password' ? 'password' : field.type === 'number' ? 'number' : 'text'"
                    class="input-field"
                    :placeholder="field.default?.toString() || ''"
                    :required="field.required"
                  />
                </div>

                <!-- Error Message -->
                <div v-if="store.error" class="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
                  <ExclamationCircleIcon class="w-5 h-5 text-red-400 flex-shrink-0" />
                  <p class="text-sm text-red-400">{{ store.error }}</p>
                </div>

                <!-- Submit Button -->
                <button
                  type="submit"
                  :disabled="creating || !connectionName"
                  class="w-full btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {{ creating ? 'Creating...' : 'Create Connection' }}
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
