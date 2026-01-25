import axios from 'axios';
import type {
  DataSourceTypeConfig,
  DataSource,
  TableSchema,
  TableData,
  QueryResult,
  Model,
  Job,
  KnowledgeBase,
  MindsDBStatus,
  MaterializedTableRequest,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Data Sources API
export const datasourcesApi = {
  getTypes: async (): Promise<{ types: DataSourceTypeConfig[] }> => {
    const response = await api.get('/datasources/types');
    return response.data;
  },

  list: async (): Promise<{ datasources: DataSource[] }> => {
    const response = await api.get('/datasources');
    return response.data;
  },

  create: async (data: {
    name: string;
    engine: string;
    parameters: Record<string, any>;
  }): Promise<DataSource> => {
    const response = await api.post('/datasources', data);
    return response.data;
  },

  delete: async (name: string): Promise<{ message: string }> => {
    const response = await api.delete(`/datasources/${name}`);
    return response.data;
  },

  getTables: async (name: string): Promise<{ tables: string[] }> => {
    const response = await api.get(`/datasources/${name}/tables`);
    return response.data;
  },

  getTableSchema: async (name: string, table: string): Promise<TableSchema> => {
    const response = await api.get(`/datasources/${name}/tables/${table}/schema`);
    return response.data;
  },

  getSampleData: async (name: string, table: string, limit = 10): Promise<TableData> => {
    const response = await api.get(`/datasources/${name}/tables/${table}/sample`, {
      params: { limit },
    });
    return response.data;
  },

  testConnection: async (name: string): Promise<{ success: boolean; message: string }> => {
    const response = await api.post(`/datasources/${name}/test`);
    return response.data;
  },
};

// Query API
export const queryApi = {
  execute: async (query: string): Promise<QueryResult> => {
    const response = await api.post('/query', { query });
    return response.data;
  },

  getStatus: async (): Promise<MindsDBStatus> => {
    const response = await api.get('/query/status');
    return response.data;
  },

  createMaterializedTable: async (data: MaterializedTableRequest): Promise<{ message: string }> => {
    const response = await api.post('/query/materialized-table', data);
    return response.data;
  },

  getModels: async (): Promise<Model[]> => {
    const response = await api.get('/query/models');
    return response.data;
  },

  getJobs: async (): Promise<Job[]> => {
    const response = await api.get('/query/jobs');
    return response.data;
  },

  getKnowledgeBases: async (): Promise<KnowledgeBase[]> => {
    const response = await api.get('/query/knowledge-bases');
    return response.data;
  },
};

export default api;
