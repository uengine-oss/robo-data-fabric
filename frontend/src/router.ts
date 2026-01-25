import { createRouter, createWebHistory } from 'vue-router';
import type { RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('./views/Dashboard.vue'),
  },
  {
    path: '/datasources',
    name: 'DataSources',
    component: () => import('./views/DataSources.vue'),
  },
  {
    path: '/query',
    name: 'Query',
    component: () => import('./views/QueryEditor.vue'),
  },
  {
    path: '/materialized',
    name: 'Materialized',
    component: () => import('./views/MaterializedTables.vue'),
  },
  {
    path: '/objects',
    name: 'Objects',
    component: () => import('./views/MindsDBObjects.vue'),
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
