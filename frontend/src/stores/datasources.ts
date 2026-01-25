import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { datasourcesApi } from '../api/client';
import type { DataSource, DataSourceTypeConfig, TableSchema, TableData } from '../types';

export const useDatasourcesStore = defineStore('datasources', () => {
  // State
  const datasources = ref<DataSource[]>([]);
  const datasourceTypes = ref<DataSourceTypeConfig[]>([]);
  const selectedDatasource = ref<DataSource | null>(null);
  const tables = ref<string[]>([]);
  const selectedTable = ref<string | null>(null);
  const tableSchema = ref<TableSchema | null>(null);
  const tableData = ref<TableData | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  // Getters
  const hasDatasources = computed(() => datasources.value.length > 0);
  const sortedDatasources = computed(() => 
    [...datasources.value].sort((a, b) => a.name.localeCompare(b.name))
  );

  // Actions
  async function fetchTypes() {
    try {
      const response = await datasourcesApi.getTypes();
      datasourceTypes.value = response.types;
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch data source types';
    }
  }

  async function fetchDatasources() {
    loading.value = true;
    error.value = null;
    try {
      const response = await datasourcesApi.list();
      datasources.value = response.datasources;
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch data sources';
    } finally {
      loading.value = false;
    }
  }

  async function createDatasource(name: string, engine: string, parameters: Record<string, any>) {
    loading.value = true;
    error.value = null;
    try {
      const newDatasource = await datasourcesApi.create({ name, engine, parameters });
      datasources.value.push(newDatasource);
      return true;
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || 'Failed to create data source';
      return false;
    } finally {
      loading.value = false;
    }
  }

  async function deleteDatasource(name: string) {
    loading.value = true;
    error.value = null;
    try {
      await datasourcesApi.delete(name);
      datasources.value = datasources.value.filter(ds => ds.name !== name);
      if (selectedDatasource.value?.name === name) {
        selectedDatasource.value = null;
        tables.value = [];
        selectedTable.value = null;
        tableSchema.value = null;
        tableData.value = null;
      }
      return true;
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || 'Failed to delete data source';
      return false;
    } finally {
      loading.value = false;
    }
  }

  async function selectDatasource(datasource: DataSource) {
    selectedDatasource.value = datasource;
    selectedTable.value = null;
    tableSchema.value = null;
    tableData.value = null;
    await fetchTables(datasource.name);
  }

  async function fetchTables(datasourceName: string) {
    loading.value = true;
    error.value = null;
    try {
      const response = await datasourcesApi.getTables(datasourceName);
      tables.value = response.tables;
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || 'Failed to fetch tables';
      tables.value = [];
    } finally {
      loading.value = false;
    }
  }

  async function selectTable(tableName: string) {
    if (!selectedDatasource.value) return;
    
    selectedTable.value = tableName;
    loading.value = true;
    error.value = null;
    
    try {
      const [schemaResponse, dataResponse] = await Promise.all([
        datasourcesApi.getTableSchema(selectedDatasource.value.name, tableName),
        datasourcesApi.getSampleData(selectedDatasource.value.name, tableName, 10)
      ]);
      tableSchema.value = schemaResponse;
      tableData.value = dataResponse;
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || 'Failed to fetch table info';
    } finally {
      loading.value = false;
    }
  }

  function clearError() {
    error.value = null;
  }

  return {
    // State
    datasources,
    datasourceTypes,
    selectedDatasource,
    tables,
    selectedTable,
    tableSchema,
    tableData,
    loading,
    error,
    // Getters
    hasDatasources,
    sortedDatasources,
    // Actions
    fetchTypes,
    fetchDatasources,
    createDatasource,
    deleteDatasource,
    selectDatasource,
    fetchTables,
    selectTable,
    clearError,
  };
});
