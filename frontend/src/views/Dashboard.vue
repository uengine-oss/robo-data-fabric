<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useQueryStore } from '../stores/query';
import { useDatasourcesStore } from '../stores/datasources';
import {
  CircleStackIcon,
  CubeIcon,
  ClockIcon,
  BookOpenIcon,
  ArrowPathIcon,
} from '@heroicons/vue/24/outline';

const queryStore = useQueryStore();
const datasourcesStore = useDatasourcesStore();
const refreshing = ref(false);

async function refresh() {
  refreshing.value = true;
  await Promise.all([
    queryStore.checkStatus(),
    datasourcesStore.fetchDatasources(),
    queryStore.fetchModels(),
    queryStore.fetchJobs(),
    queryStore.fetchKnowledgeBases(),
  ]);
  refreshing.value = false;
}

onMounted(() => {
  refresh();
});
</script>

<template>
  <div class="space-y-8">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-minds-text">Dashboard</h1>
        <p class="text-minds-muted mt-1">Overview of your MindsDB resources</p>
      </div>
      <button
        @click="refresh"
        :disabled="refreshing"
        class="btn-secondary flex items-center gap-2"
      >
        <ArrowPathIcon :class="['w-5 h-5', refreshing && 'animate-spin']" />
        Refresh
      </button>
    </div>

    <!-- Stats Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <!-- Data Sources -->
      <div class="card group hover:border-minds-accent/50 transition-colors">
        <div class="flex items-start justify-between">
          <div>
            <p class="text-minds-muted text-sm">Data Sources</p>
            <p class="text-4xl font-bold text-minds-text mt-2">
              {{ datasourcesStore.datasources.length }}
            </p>
          </div>
          <div class="w-12 h-12 rounded-lg bg-blue-500/10 flex items-center justify-center">
            <CircleStackIcon class="w-6 h-6 text-blue-400" />
          </div>
        </div>
        <div class="mt-4 pt-4 border-t border-minds-border">
          <RouterLink
            to="/datasources"
            class="text-sm text-minds-accent hover:text-minds-accent-hover"
          >
            Manage sources →
          </RouterLink>
        </div>
      </div>

      <!-- Models -->
      <div class="card group hover:border-minds-accent/50 transition-colors">
        <div class="flex items-start justify-between">
          <div>
            <p class="text-minds-muted text-sm">ML Models</p>
            <p class="text-4xl font-bold text-minds-text mt-2">
              {{ queryStore.models.length }}
            </p>
          </div>
          <div class="w-12 h-12 rounded-lg bg-purple-500/10 flex items-center justify-center">
            <CubeIcon class="w-6 h-6 text-purple-400" />
          </div>
        </div>
        <div class="mt-4 pt-4 border-t border-minds-border">
          <RouterLink
            to="/objects"
            class="text-sm text-minds-accent hover:text-minds-accent-hover"
          >
            View models →
          </RouterLink>
        </div>
      </div>

      <!-- Jobs -->
      <div class="card group hover:border-minds-accent/50 transition-colors">
        <div class="flex items-start justify-between">
          <div>
            <p class="text-minds-muted text-sm">Scheduled Jobs</p>
            <p class="text-4xl font-bold text-minds-text mt-2">
              {{ queryStore.jobs.length }}
            </p>
          </div>
          <div class="w-12 h-12 rounded-lg bg-amber-500/10 flex items-center justify-center">
            <ClockIcon class="w-6 h-6 text-amber-400" />
          </div>
        </div>
        <div class="mt-4 pt-4 border-t border-minds-border">
          <RouterLink
            to="/objects"
            class="text-sm text-minds-accent hover:text-minds-accent-hover"
          >
            View jobs →
          </RouterLink>
        </div>
      </div>

      <!-- Knowledge Bases -->
      <div class="card group hover:border-minds-accent/50 transition-colors">
        <div class="flex items-start justify-between">
          <div>
            <p class="text-minds-muted text-sm">Knowledge Bases</p>
            <p class="text-4xl font-bold text-minds-text mt-2">
              {{ queryStore.knowledgeBases.length }}
            </p>
          </div>
          <div class="w-12 h-12 rounded-lg bg-teal-500/10 flex items-center justify-center">
            <BookOpenIcon class="w-6 h-6 text-teal-400" />
          </div>
        </div>
        <div class="mt-4 pt-4 border-t border-minds-border">
          <RouterLink
            to="/objects"
            class="text-sm text-minds-accent hover:text-minds-accent-hover"
          >
            View KBs →
          </RouterLink>
        </div>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="card">
      <h2 class="text-xl font-semibold text-minds-text mb-6">Quick Actions</h2>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <RouterLink
          to="/datasources"
          class="p-4 rounded-lg bg-minds-surface border border-minds-border hover:border-minds-accent/50 transition-all group"
        >
          <CircleStackIcon class="w-8 h-8 text-minds-accent mb-3" />
          <h3 class="font-medium text-minds-text group-hover:text-minds-accent transition-colors">
            Add Data Source
          </h3>
          <p class="text-sm text-minds-muted mt-1">
            Connect MySQL, PostgreSQL, Neo4j, and more
          </p>
        </RouterLink>

        <RouterLink
          to="/query"
          class="p-4 rounded-lg bg-minds-surface border border-minds-border hover:border-minds-accent/50 transition-all group"
        >
          <svg class="w-8 h-8 text-minds-accent mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <h3 class="font-medium text-minds-text group-hover:text-minds-accent transition-colors">
            Run SQL Query
          </h3>
          <p class="text-sm text-minds-muted mt-1">
            Execute queries across your data sources
          </p>
        </RouterLink>

        <RouterLink
          to="/materialized"
          class="p-4 rounded-lg bg-minds-surface border border-minds-border hover:border-minds-accent/50 transition-all group"
        >
          <svg class="w-8 h-8 text-minds-accent mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
          </svg>
          <h3 class="font-medium text-minds-text group-hover:text-minds-accent transition-colors">
            Create Materialized Table
          </h3>
          <p class="text-sm text-minds-muted mt-1">
            Cache data from external sources
          </p>
        </RouterLink>
      </div>
    </div>

    <!-- Connection Status -->
    <div class="card">
      <h2 class="text-xl font-semibold text-minds-text mb-4">MindsDB Server Status</h2>
      <div class="flex items-center gap-4">
        <div
          :class="[
            'w-3 h-3 rounded-full',
            queryStore.isConnected ? 'bg-minds-accent animate-pulse' : 'bg-red-500'
          ]"
        />
        <div>
          <p class="text-minds-text">
            {{ queryStore.isConnected ? 'Connected to MindsDB' : 'Not connected' }}
          </p>
          <p v-if="queryStore.status?.version" class="text-sm text-minds-muted">
            Version: {{ queryStore.status.version }}
          </p>
          <p v-if="queryStore.status?.error" class="text-sm text-red-400">
            {{ queryStore.status.error }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
