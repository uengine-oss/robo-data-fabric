<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useQueryStore } from '../stores/query';
import {
  CubeIcon,
  ClockIcon,
  BookOpenIcon,
  ArrowPathIcon,
} from '@heroicons/vue/24/outline';

const queryStore = useQueryStore();
const activeTab = ref<'models' | 'jobs' | 'knowledgebases'>('models');
const refreshing = ref(false);

async function refresh() {
  refreshing.value = true;
  await Promise.all([
    queryStore.fetchModels(),
    queryStore.fetchJobs(),
    queryStore.fetchKnowledgeBases(),
  ]);
  refreshing.value = false;
}

onMounted(() => {
  refresh();
});

const tabs = [
  { id: 'models' as const, label: 'Models', icon: CubeIcon },
  { id: 'jobs' as const, label: 'Jobs', icon: ClockIcon },
  { id: 'knowledgebases' as const, label: 'Knowledge Bases', icon: BookOpenIcon },
];

function getStatusColor(status: string) {
  switch (status?.toLowerCase()) {
    case 'complete':
    case 'completed':
      return 'bg-minds-accent/20 text-minds-accent';
    case 'training':
    case 'running':
      return 'bg-amber-500/20 text-amber-400';
    case 'error':
    case 'failed':
      return 'bg-red-500/20 text-red-400';
    default:
      return 'bg-minds-muted/20 text-minds-muted';
  }
}
</script>

<template>
  <div class="space-y-8">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-minds-text">MindsDB Objects</h1>
        <p class="text-minds-muted mt-1">Manage models, jobs, and knowledge bases</p>
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

    <!-- Tabs -->
    <div class="border-b border-minds-border">
      <nav class="flex gap-8">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          @click="activeTab = tab.id"
          :class="[
            'flex items-center gap-2 pb-4 border-b-2 transition-colors',
            activeTab === tab.id
              ? 'border-minds-accent text-minds-accent'
              : 'border-transparent text-minds-muted hover:text-minds-text'
          ]"
        >
          <component :is="tab.icon" class="w-5 h-5" />
          {{ tab.label }}
          <span
            :class="[
              'px-2 py-0.5 rounded-full text-xs',
              activeTab === tab.id ? 'bg-minds-accent/20' : 'bg-minds-surface'
            ]"
          >
            {{
              tab.id === 'models' ? queryStore.models.length :
              tab.id === 'jobs' ? queryStore.jobs.length :
              queryStore.knowledgeBases.length
            }}
          </span>
        </button>
      </nav>
    </div>

    <!-- Models Tab -->
    <div v-if="activeTab === 'models'" class="space-y-4">
      <div v-if="queryStore.models.length === 0" class="card text-center py-12">
        <CubeIcon class="w-12 h-12 text-minds-muted mx-auto mb-4" />
        <p class="text-minds-muted">No models found</p>
        <p class="text-sm text-minds-muted mt-2">
          Create a model using: CREATE MODEL model_name ...
        </p>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div
          v-for="model in queryStore.models"
          :key="model.name"
          class="card hover:border-minds-accent/50 transition-colors"
        >
          <div class="flex items-start justify-between">
            <div>
              <h3 class="font-semibold text-minds-text">{{ model.name }}</h3>
              <p class="text-sm text-minds-muted mt-1">
                Predicts: <span class="text-minds-accent">{{ model.predict || 'N/A' }}</span>
              </p>
            </div>
            <span
              :class="[
                'px-2 py-1 rounded-full text-xs font-medium',
                getStatusColor(model.status)
              ]"
            >
              {{ model.status }}
            </span>
          </div>
          <div v-if="model.engine" class="mt-4 pt-4 border-t border-minds-border">
            <p class="text-xs text-minds-muted">
              Engine: <span class="text-minds-text">{{ model.engine }}</span>
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Jobs Tab -->
    <div v-if="activeTab === 'jobs'" class="space-y-4">
      <div v-if="queryStore.jobs.length === 0" class="card text-center py-12">
        <ClockIcon class="w-12 h-12 text-minds-muted mx-auto mb-4" />
        <p class="text-minds-muted">No jobs found</p>
        <p class="text-sm text-minds-muted mt-2">
          Create a job using: CREATE JOB job_name ...
        </p>
      </div>

      <div v-else class="card overflow-hidden">
        <table class="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Schedule</th>
              <th>Next Run</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="job in queryStore.jobs" :key="job.name">
              <td class="font-medium">{{ job.name }}</td>
              <td>{{ job.schedule || 'N/A' }}</td>
              <td>{{ job.next_run || 'N/A' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Knowledge Bases Tab -->
    <div v-if="activeTab === 'knowledgebases'" class="space-y-4">
      <div v-if="queryStore.knowledgeBases.length === 0" class="card text-center py-12">
        <BookOpenIcon class="w-12 h-12 text-minds-muted mx-auto mb-4" />
        <p class="text-minds-muted">No knowledge bases found</p>
        <p class="text-sm text-minds-muted mt-2">
          Create a knowledge base using: CREATE KNOWLEDGE_BASE kb_name ...
        </p>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div
          v-for="kb in queryStore.knowledgeBases"
          :key="kb.name"
          class="card hover:border-minds-accent/50 transition-colors"
        >
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-lg bg-teal-500/20 flex items-center justify-center">
              <BookOpenIcon class="w-5 h-5 text-teal-400" />
            </div>
            <div>
              <h3 class="font-semibold text-minds-text">{{ kb.name }}</h3>
              <p v-if="kb.model" class="text-sm text-minds-muted">
                Model: {{ kb.model }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
