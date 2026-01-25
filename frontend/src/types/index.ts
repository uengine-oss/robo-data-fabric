// Data Source Types
export interface DataSourceField {
  name: string;
  label: string;
  type: 'text' | 'number' | 'password';
  required: boolean;
  default?: string | number;
}

export interface DataSourceTypeConfig {
  type: string;
  display_name: string;
  icon: string;
  fields: DataSourceField[];
}

export interface DataSource {
  name: string;
  engine: string;
  tables: string[];
}

export interface TableColumn {
  name: string;
  type: string;
  nullable?: string;
  key?: string;
}

export interface TableSchema {
  table: string;
  columns: TableColumn[];
}

export interface TableData {
  columns: string[];
  data: any[][];
  total_rows: number;
}

// Query Types
export interface QueryResult {
  type: 'table' | 'ok' | 'error';
  columns: string[];
  data: any[][];
  row_count: number;
  error?: string;
  execution_time?: number;
}

export interface MaterializedTableRequest {
  table_name: string;
  source_database: string;
  source_table: string;
  columns?: string[];
  where_clause?: string;
  limit?: number;
}

// MindsDB Objects
export interface Model {
  name: string;
  status: string;
  predict?: string;
  engine?: string;
}

export interface Job {
  name: string;
  schedule?: string;
  next_run?: string;
}

export interface KnowledgeBase {
  name: string;
  model?: string;
}

export interface MindsDBStatus {
  connected: boolean;
  version?: string;
  error?: string;
}

// UI State Types
export interface ConnectionFormData {
  [key: string]: string | number;
}
