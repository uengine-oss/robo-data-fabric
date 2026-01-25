<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useQueryStore } from '../stores/query';
import { useDatasourcesStore } from '../stores/datasources';
import {
  PlayIcon,
  ClockIcon,
  DocumentDuplicateIcon,
  TrashIcon,
} from '@heroicons/vue/24/outline';

const queryStore = useQueryStore();
const datasourcesStore = useDatasourcesStore();

const queryText = ref(`-- MindsDB SQL Query Editor
-- Examples:

-- Show all databases
-- SHOW DATABASES;

-- Show tables from a database
-- SHOW TABLES FROM your_database;

-- Query data
-- SELECT * FROM your_database.your_table LIMIT 10;

SELECT 1 AS test;
`);

onMounted(async () => {
  await datasourcesStore.fetchDatasources();
  if (queryStore.currentQuery) {
    queryText.value = queryStore.currentQuery;
  }
});

async function executeQuery() {
  queryStore.setQuery(queryText.value);
  await queryStore.executeQuery(queryText.value);
}

function insertQuery(sql: string) {
  queryText.value += '\n' + sql + '\n';
}

function clearEditor() {
  queryText.value = '';
}

function copyResult() {
  if (queryStore.queryResult) {
    const headers = queryStore.queryResult.columns.join('\t');
    const rows = queryStore.queryResult.data.map(row => row.join('\t')).join('\n');
    navigator.clipboard.writeText(headers + '\n' + rows);
  }
}

function handleKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    e.preventDefault();
    executeQuery();
  }
}

// Quick insert templates
const templates = [
  { label: 'SHOW DATABASES', sql: 'SHOW DATABASES;' },
  { label: 'SHOW MODELS', sql: 'SHOW MODELS;' },
  { label: 'SHOW JOBS', sql: 'SHOW JOBS;' },
  { label: 'SHOW TABLES', sql: 'SHOW TABLES FROM database_name;' },
];
</script>

<template>
  <div class="h-[calc(100vh-8rem)] flex flex-col gap-6">
    <!-- Header -->
    <div class="flex items-center justify-between flex-shrink-0">
      <div>
        <h1 class="text-3xl font-bold text-minds-text">Query Editor</h1>
        <p class="text-minds-muted mt-1">Execute SQL queries on MindsDB</p>
      </div>
      <div class="flex items-center gap-3">
        <button
          @click="executeQuery"
          :disabled="queryStore.loading"
          class="btn-primary flex items-center gap-2"
        >
          <PlayIcon class="w-5 h-5" />
          {{ queryStore.loading ? 'Running...' : 'Run Query' }}
          <span class="text-xs opacity-70">(Ctrl+Enter)</span>
        </button>
      </div>
    </div>

    <div class="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-6 min-h-0">
      <!-- Sidebar -->
      <div class="lg:col-span-1 flex flex-col gap-4">
        <!-- Quick Templates -->
        <div class="card">
          <h3 class="text-sm font-medium text-minds-muted mb-3">Quick Insert</h3>
          <div class="space-y-2">
            <button
              v-for="tpl in templates"
              :key="tpl.label"
              @click="insertQuery(tpl.sql)"
              class="w-full text-left px-3 py-2 rounded-lg text-sm text-minds-text hover:bg-minds-surface transition-colors"
            >
              {{ tpl.label }}
            </button>
          </div>
        </div>

        <!-- Data Sources -->
        <div class="card flex-1 overflow-hidden flex flex-col">
          <h3 class="text-sm font-medium text-minds-muted mb-3">Data Sources</h3>
          <div class="flex-1 overflow-y-auto space-y-1">
            <div
              v-for="ds in datasourcesStore.datasources"
              :key="ds.name"
              class="px-3 py-2 rounded-lg text-sm cursor-pointer hover:bg-minds-surface transition-colors"
              @click="insertQuery(`SELECT * FROM ${ds.name}.table_name LIMIT 10;`)"
            >
              <span class="text-minds-text">{{ ds.name }}</span>
              <span class="text-minds-muted text-xs ml-2">({{ ds.engine }})</span>
            </div>
          </div>
        </div>

        <!-- Query History -->
        <div class="card flex-1 overflow-hidden flex flex-col">
          <h3 class="text-sm font-medium text-minds-muted mb-3 flex items-center gap-2">
            <ClockIcon class="w-4 h-4" />
            History
          </h3>
          <div class="flex-1 overflow-y-auto space-y-1">
            <button
              v-for="(item, idx) in queryStore.lastQueries"
              :key="idx"
              @click="queryText = item.query"
              class="w-full text-left px-3 py-2 rounded-lg text-xs font-mono text-minds-text hover:bg-minds-surface transition-colors truncate"
              :class="{ 'text-red-400': !item.success }"
            >
              {{ item.query.slice(0, 50) }}{{ item.query.length > 50 ? '...' : '' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Editor & Results -->
      <div class="lg:col-span-3 flex flex-col gap-4 min-h-0">
        <!-- Editor -->
        <div class="card flex-shrink-0">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-sm font-medium text-minds-muted">SQL Editor</h3>
            <button
              @click="clearEditor"
              class="text-minds-muted hover:text-red-400 transition-colors"
              title="Clear editor"
            >
              <TrashIcon class="w-4 h-4" />
            </button>
          </div>
          <textarea
            v-model="queryText"
            @keydown="handleKeydown"
            class="w-full h-64 bg-minds-surface text-minds-text font-mono text-sm p-4 rounded-lg border border-minds-border focus:outline-none focus:ring-2 focus:ring-minds-accent resize-none"
            placeholder="Enter your SQL query here..."
            spellcheck="false"
          ></textarea>
        </div>

        <!-- Results -->
        <div class="card flex-1 overflow-hidden flex flex-col">
          <div class="flex items-center justify-between mb-4 flex-shrink-0">
            <h3 class="text-sm font-medium text-minds-muted">
              Results
              <span v-if="queryStore.queryResult?.row_count" class="text-minds-accent ml-2">
                ({{ queryStore.queryResult.row_count }} rows)
              </span>
              <span v-if="queryStore.queryResult?.execution_time" class="text-minds-muted ml-2">
                {{ queryStore.queryResult.execution_time.toFixed(2) }}s
              </span>
            </h3>
            <button
              v-if="queryStore.queryResult?.data.length"
              @click="copyResult"
              class="text-minds-muted hover:text-minds-accent transition-colors"
              title="Copy to clipboard"
            >
              <DocumentDuplicateIcon class="w-4 h-4" />
            </button>
          </div>

          <!-- Loading -->
          <div v-if="queryStore.loading" class="flex-1 flex items-center justify-center">
            <div class="animate-spin w-8 h-8 border-2 border-minds-accent border-t-transparent rounded-full"></div>
          </div>

          <!-- Error -->
          <div v-else-if="queryStore.queryResult?.type === 'error'" class="flex-1">
            <div class="p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
              <p class="text-red-400 font-mono text-sm">{{ queryStore.queryResult.error }}</p>
            </div>
          </div>

          <!-- Success (non-table) -->
          <div v-else-if="queryStore.queryResult?.type === 'ok'" class="flex-1">
            <div class="p-4 bg-minds-accent/10 border border-minds-accent/30 rounded-lg">
              <p class="text-minds-accent">Query executed successfully</p>
            </div>
          </div>

          <!-- Table Result -->
          <div v-else-if="queryStore.queryResult?.data.length" class="flex-1 overflow-auto">
            <table class="data-table">
              <thead>
                <tr>
                  <th v-for="col in queryStore.queryResult.columns" :key="col">{{ col }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, idx) in queryStore.queryResult.data" :key="idx">
                  <td v-for="(cell, cellIdx) in row" :key="cellIdx">
                    <span class="font-mono text-xs">{{ cell ?? 'null' }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Empty state -->
          <div v-else class="flex-1 flex items-center justify-center">
            <p class="text-minds-muted">Run a query to see results</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
