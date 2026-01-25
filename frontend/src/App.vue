<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { RouterLink, RouterView, useRoute } from 'vue-router';
import { useQueryStore } from './stores/query';
import {
  CircleStackIcon,
  CommandLineIcon,
  TableCellsIcon,
  CubeIcon,
  Squares2X2Icon,
  Bars3Icon,
  XMarkIcon,
} from '@heroicons/vue/24/outline';

const queryStore = useQueryStore();
const route = useRoute();
const mobileMenuOpen = ref(false);

const navigation = [
  { name: 'Dashboard', href: '/', icon: Squares2X2Icon },
  { name: 'Data Sources', href: '/datasources', icon: CircleStackIcon },
  { name: 'Query Editor', href: '/query', icon: CommandLineIcon },
  { name: 'Materialized Tables', href: '/materialized', icon: TableCellsIcon },
  { name: 'MindsDB Objects', href: '/objects', icon: CubeIcon },
];

onMounted(() => {
  queryStore.checkStatus();
});
</script>

<template>
  <div class="min-h-screen bg-minds-primary">
    <!-- Mobile menu button -->
    <div class="lg:hidden fixed top-4 left-4 z-50">
      <button
        @click="mobileMenuOpen = !mobileMenuOpen"
        class="p-2 rounded-lg bg-minds-secondary border border-minds-border text-minds-text"
      >
        <Bars3Icon v-if="!mobileMenuOpen" class="w-6 h-6" />
        <XMarkIcon v-else class="w-6 h-6" />
      </button>
    </div>

    <!-- Sidebar -->
    <div
      :class="[
        'fixed inset-y-0 left-0 z-40 w-72 bg-minds-secondary border-r border-minds-border transform transition-transform duration-300 lg:translate-x-0',
        mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
      ]"
    >
      <!-- Logo -->
      <div class="h-20 flex items-center px-6 border-b border-minds-border">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-minds-accent to-teal-400 flex items-center justify-center">
            <span class="text-minds-primary font-bold text-lg">M</span>
          </div>
          <div>
            <h1 class="text-lg font-bold text-minds-text">MindsDB</h1>
            <p class="text-xs text-minds-muted">Data Source Manager</p>
          </div>
        </div>
      </div>

      <!-- Connection Status -->
      <div class="px-6 py-4 border-b border-minds-border">
        <div class="flex items-center gap-2">
          <div
            :class="[
              'w-2 h-2 rounded-full',
              queryStore.isConnected ? 'bg-minds-accent' : 'bg-red-500'
            ]"
          />
          <span class="text-sm text-minds-muted">
            {{ queryStore.isConnected ? 'Connected' : 'Disconnected' }}
          </span>
          <span v-if="queryStore.status?.version" class="text-xs text-minds-muted ml-auto">
            v{{ queryStore.status.version }}
          </span>
        </div>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 px-4 py-6 space-y-2">
        <RouterLink
          v-for="item in navigation"
          :key="item.name"
          :to="item.href"
          @click="mobileMenuOpen = false"
          :class="[
            'flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200',
            route.path === item.href
              ? 'bg-minds-accent/10 text-minds-accent border border-minds-accent/30'
              : 'text-minds-muted hover:text-minds-text hover:bg-minds-surface'
          ]"
        >
          <component :is="item.icon" class="w-5 h-5" />
          <span class="font-medium">{{ item.name }}</span>
        </RouterLink>
      </nav>

      <!-- Footer -->
      <div class="px-6 py-4 border-t border-minds-border">
        <p class="text-xs text-minds-muted text-center">
          MindsDB UI v1.0.0
        </p>
      </div>
    </div>

    <!-- Overlay for mobile -->
    <div
      v-if="mobileMenuOpen"
      @click="mobileMenuOpen = false"
      class="fixed inset-0 z-30 bg-black/50 lg:hidden"
    />

    <!-- Main content -->
    <div class="lg:pl-72">
      <main class="min-h-screen p-6 lg:p-8">
        <RouterView />
      </main>
    </div>
  </div>
</template>
