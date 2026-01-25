import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { queryApi } from '../api/client';
import type { QueryResult, Model, Job, KnowledgeBase, MindsDBStatus } from '../types';

export const useQueryStore = defineStore('query', () => {
  // State
  const currentQuery = ref('');
  const queryResult = ref<QueryResult | null>(null);
  const queryHistory = ref<{ query: string; timestamp: Date; success: boolean }[]>([]);
  const models = ref<Model[]>([]);
  const jobs = ref<Job[]>([]);
  const knowledgeBases = ref<KnowledgeBase[]>([]);
  const status = ref<MindsDBStatus | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  // Getters
  const isConnected = computed(() => status.value?.connected ?? false);
  const lastQueries = computed(() => queryHistory.value.slice(-10).reverse());

  // Actions
  async function checkStatus() {
    try {
      status.value = await queryApi.getStatus();
    } catch (e: any) {
      status.value = { connected: false, error: e.message };
    }
  }

  async function executeQuery(query: string) {
    loading.value = true;
    error.value = null;
    currentQuery.value = query;
    
    try {
      queryResult.value = await queryApi.execute(query);
      queryHistory.value.push({
        query,
        timestamp: new Date(),
        success: queryResult.value.type !== 'error'
      });
      
      if (queryResult.value.type === 'error') {
        error.value = queryResult.value.error || 'Query execution failed';
      }
      
      return queryResult.value;
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || 'Failed to execute query';
      queryResult.value = {
        type: 'error',
        columns: [],
        data: [],
        row_count: 0,
        error: error.value || undefined
      };
      return queryResult.value;
    } finally {
      loading.value = false;
    }
  }

  async function createMaterializedTable(
    tableName: string,
    sourceDatabase: string,
    sourceTable: string,
    columns: string[] = ['*'],
    whereClause?: string,
    limit?: number
  ) {
    loading.value = true;
    error.value = null;
    
    try {
      await queryApi.createMaterializedTable({
        table_name: tableName,
        source_database: sourceDatabase,
        source_table: sourceTable,
        columns,
        where_clause: whereClause,
        limit
      });
      return true;
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || 'Failed to create materialized table';
      return false;
    } finally {
      loading.value = false;
    }
  }

  async function fetchModels() {
    try {
      models.value = await queryApi.getModels();
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch models';
    }
  }

  async function fetchJobs() {
    try {
      jobs.value = await queryApi.getJobs();
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch jobs';
    }
  }

  async function fetchKnowledgeBases() {
    try {
      knowledgeBases.value = await queryApi.getKnowledgeBases();
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch knowledge bases';
    }
  }

  function clearResult() {
    queryResult.value = null;
    error.value = null;
  }

  function clearError() {
    error.value = null;
  }

  function setQuery(query: string) {
    currentQuery.value = query;
  }

  return {
    // State
    currentQuery,
    queryResult,
    queryHistory,
    models,
    jobs,
    knowledgeBases,
    status,
    loading,
    error,
    // Getters
    isConnected,
    lastQueries,
    // Actions
    checkStatus,
    executeQuery,
    createMaterializedTable,
    fetchModels,
    fetchJobs,
    fetchKnowledgeBases,
    clearResult,
    clearError,
    setQuery,
  };
});
