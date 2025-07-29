/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */
import { useState, useEffect } from 'react';
import { SupersetClient } from '@superset-ui/core';

interface DatabaseConfig {
  success: boolean;
  database_id?: number;
  database_name?: string;
  error?: string;
}

interface Column {
  column_name: string;
  name: string;
  type: string;
  is_dttm: boolean;
}

interface Pagination {
  page: number;
  page_size: number;
  total_count: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
  server_side: boolean;
}

interface ExecutionResults {
  query_id?: number;
  status?: string;
  data?: Record<string, any>[] | null;
  columns?: Column[];
  selected_columns?: Column[];
  expanded_columns?: Column[];
  query?: {
    sql: string;
    executed_sql: string;
  };
  pagination?: Pagination;
  success?: boolean;
  error?: string;
}

export default function AIQuery() {
  const [description, setDescription] = useState('');
  const [generatedQuery, setGeneratedQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [executionResults, setExecutionResults] = useState<ExecutionResults | null>(null);
  const [databaseConfig, setDatabaseConfig] = useState<DatabaseConfig | null>(null);
  const [configLoading, setConfigLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(50);
  const [paginationLoading, setPaginationLoading] = useState(false);

  // Fetch database configuration on component mount
  useEffect(() => {
    const fetchDatabaseConfig = async () => {
      try {
        const response = await SupersetClient.get({
          endpoint: '/ai-query/config',
        });
        setDatabaseConfig(response.json as DatabaseConfig);
      } catch (error) {
        console.error('Failed to fetch database config:', error);
        setDatabaseConfig({
          success: false,
          error: 'Failed to load database configuration'
        });
      } finally {
        setConfigLoading(false);
      }
    };

    fetchDatabaseConfig();
  }, []);

  const handleGenerateAndExecuteQuery = async () => {
    if (!databaseConfig || !databaseConfig.success) {
      setExecutionResults({
        success: false,
        error: 'Database configuration not available. Please refresh the page.',
        data: null,
      });
      return;
    }

    setLoading(true);
    setExecutionResults(null);
    setGeneratedQuery('');
    setCurrentPage(1);
    
    try {
      // Step 1: Generate SQL query
      const generateResponse = await SupersetClient.post({
        endpoint: '/ai-query/generate',
        body: JSON.stringify({ description }),
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      const sqlQuery = generateResponse.json.query;
      setGeneratedQuery(sqlQuery || 'No query generated');
      
      if (!sqlQuery || generateResponse.json.success === false) {
        setExecutionResults({
          success: false,
          error: generateResponse.json.error || 'Failed to generate SQL query',
          data: null,
        });
        return;
      }

      // Step 2: Automatically execute the generated SQL
      const executeResponse = await SupersetClient.post({
        endpoint: '/ai-query/execute',
        body: JSON.stringify({
          database_id: databaseConfig.database_id,
          sql: sqlQuery,
          queryLimit: 1000,
          client_id: `ai_${Date.now().toString().slice(-8)}`,
          expand_data: true,
          page: currentPage,
          page_size: pageSize,
        }),
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      setExecutionResults(executeResponse.json);
      
    } catch (error) {
      setExecutionResults({
        success: false,
        error: error.message,
        data: null,
      });
    } finally {
      setLoading(false);
    }
  };

  // Handle pagination for server-side paginated results
  const handlePageChange = async (newPage: number) => {
    if (!executionResults || !generatedQuery) return;
    
    const pagination = executionResults.pagination;
    if (pagination?.server_side) {
      // Server-side pagination: make new request
      setPaginationLoading(true);
      setCurrentPage(newPage);
      
      try {
        const executeResponse = await SupersetClient.post({
          endpoint: '/ai-query/execute',
          body: JSON.stringify({
            database_id: databaseConfig!.database_id,
            sql: generatedQuery,
            queryLimit: 1000,
            client_id: `ai_${Date.now().toString().slice(-8)}`,
            expand_data: true,
            page: newPage,
            page_size: pageSize,
          }),
          headers: {
            'Content-Type': 'application/json',
          },
        });
        
        setExecutionResults(executeResponse.json);
      } catch (error) {
        console.error('Pagination request failed:', error);
        // Reset to previous page on error
        setCurrentPage(currentPage);
      } finally {
        setPaginationLoading(false);
      }
    } else {
      // Client-side pagination: just update page
      setCurrentPage(newPage);
    }
  };

  // Pagination helpers
  const getTotalPages = () => {
    const pagination = executionResults?.pagination;
    if (pagination) {
      return pagination.total_pages;
    }
    // Fallback for old format
    if (!executionResults?.data) return 0;
    return Math.ceil(executionResults.data.length / pageSize);
  };

  const getCurrentPageData = () => {
    const pagination = executionResults?.pagination;
    if (pagination?.server_side) {
      // Server-side pagination: data is already the current page
      return executionResults?.data || [];
    } else {
      // Client-side pagination: slice the data
      if (!executionResults?.data) return [];
      const startIndex = (currentPage - 1) * pageSize;
      const endIndex = startIndex + pageSize;
      return executionResults.data.slice(startIndex, endIndex);
    }
  };

  const getCurrentPage = () => {
    const pagination = executionResults?.pagination;
    return pagination?.page || currentPage;
  };

  const getTotalCount = () => {
    const pagination = executionResults?.pagination;
    return pagination?.total_count || executionResults?.data?.length || 0;
  };

  const getDisplayRange = () => {
    const pagination = executionResults?.pagination;
    const totalCount = getTotalCount();
    const currentPageNum = getCurrentPage();
    
    if (pagination?.server_side) {
      const start = ((currentPageNum - 1) * pageSize) + 1;
      const end = Math.min(currentPageNum * pageSize, totalCount);
      return { start, end, total: totalCount };
    } else {
      const start = ((currentPage - 1) * pageSize) + 1;
      const end = Math.min(currentPage * pageSize, totalCount);
      return { start, end, total: totalCount };
    }
  };

  return (
    <div style={{ 
      height: '100vh', 
      display: 'flex', 
      flexDirection: 'column',
      padding: '20px',
      gap: '20px'
    }}>
      <div style={{ textAlign: 'center', marginBottom: '20px', flexShrink: 0 }}>
        <h1 style={{ margin: '0 0 10px 0', color: '#333', fontSize: '28px' }}>
          AI Query Assistant
        </h1>
        <p style={{ margin: '0', color: '#666', fontSize: '16px' }}>
          Ask questions about the patent database in natural language
        </p>
        {databaseConfig && databaseConfig.success && (
          <p style={{ margin: '5px 0 0 0', color: '#888', fontSize: '14px' }}>
            Querying: <strong>{databaseConfig.database_name}</strong>
          </p>
        )}
      </div>
      
      <div style={{ 
        background: '#f9f9f9', 
        border: '1px solid #ddd', 
        borderRadius: '8px', 
        padding: '20px',
        flexShrink: 0
      }}>
        <h2 style={{ marginTop: '0', marginBottom: '15px', color: '#444' }}>
          Ask Your Question
        </h2>
        <textarea 
          placeholder="Example: Find all attorneys with last name Smith, or Show me patents filed in 2023..." 
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          style={{
            width: '100%',
            height: '100px',
            padding: '12px',
            border: '2px solid #e1e5e9',
            borderRadius: '6px',
            fontSize: '14px',
            resize: 'vertical',
            outline: 'none',
            transition: 'border-color 0.2s',
          }}
          onFocus={(e) => e.target.style.borderColor = '#1890ff'}
          onBlur={(e) => e.target.style.borderColor = '#e1e5e9'}
        />
        <button 
          onClick={handleGenerateAndExecuteQuery}
          disabled={loading || configLoading || !databaseConfig?.success}
          style={{
            marginTop: '15px',
            padding: '12px 24px',
            background: (loading || configLoading || !databaseConfig?.success) ? '#ccc' : '#1890ff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: (loading || configLoading || !databaseConfig?.success) ? 'not-allowed' : 'pointer',
            fontSize: '16px',
            fontWeight: 'bold'
          }}
        >
          {loading ? 'Processing...' : configLoading ? 'Loading...' : !databaseConfig?.success ? 'Database Unavailable' : 'Ask AI'}
        </button>
        
        {databaseConfig && !databaseConfig.success && (
          <div style={{
            marginTop: '15px',
            padding: '10px',
            background: '#fff2f0',
            border: '1px solid #ffccc7',
            borderRadius: '4px',
            color: '#ff4d4f',
            fontSize: '14px'
          }}>
            <strong>Configuration Error:</strong> {databaseConfig.error}
          </div>
        )}
      </div>
      
      
      <div style={{ 
        background: '#f0f0f0', 
        border: '1px solid #ddd', 
        borderRadius: '8px', 
        padding: '20px',
        flex: '1',
        minHeight: '400px',
        overflow: 'auto',
        display: 'flex',
        flexDirection: 'column'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
          <h3 style={{ margin: '0', color: '#555' }}>
            {loading ? 'Processing your query...' : 'Results'}
          </h3>
        </div>
        {executionResults ? (
          <div>
            {executionResults.error ? (
              <div style={{ 
                color: '#ff4d4f', 
                background: '#fff2f0', 
                padding: '10px', 
                borderRadius: '4px',
                border: '1px solid #ffccc7'
              }}>
                <strong>Error:</strong> {executionResults.error}
              </div>
            ) : (
              <div>
                {executionResults.data && executionResults.data.length > 0 ? (
                  <div style={{ 
                    background: 'white', 
                    border: '1px solid #ddd',
                    borderRadius: '4px',
                    flex: '1',
                    minHeight: '300px',
                    overflow: 'auto',
                    position: 'relative'
                  }}>
                    <table style={{ 
                      width: '100%', 
                      borderCollapse: 'collapse',
                      fontSize: '14px'
                    }}>
                      <thead>
                        <tr style={{
                          position: 'sticky',
                          top: 0,
                          zIndex: 10,
                          background: '#f8f9fa'
                        }}>
                          {executionResults.columns && executionResults.columns.map((col: Column, idx: number) => (
                            <th key={idx} style={{ 
                              padding: '12px 16px', 
                              textAlign: 'left',
                              fontWeight: 'bold',
                              background: '#f8f9fa',
                              fontSize: '14px',
                              borderBottom: '2px solid #e0e0e0',
                              borderRight: idx < executionResults.columns!.length - 1 ? '1px solid #e0e0e0' : 'none',
                              whiteSpace: 'nowrap',
                              boxShadow: '0 2px 2px -1px rgba(0, 0, 0, 0.1)'
                            }}>
                              {col.name}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {getCurrentPageData().map((row: Record<string, any>, rowIdx: number) => (
                          <tr key={rowIdx} style={{ 
                            borderBottom: '1px solid #f0f0f0'
                          }}>
                            {executionResults.columns!.map((col: Column, colIdx: number) => (
                              <td key={colIdx} style={{ 
                                padding: '12px 16px',
                                borderRight: colIdx < executionResults.columns!.length - 1 ? '1px solid #e0e0e0' : 'none',
                                maxWidth: '250px',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap'
                              }}>
                                {row[col.name] !== null && row[col.name] !== undefined ? String(row[col.name]) : 
                                  <span style={{ color: '#999', fontStyle: 'italic' }}>N/A</span>
                                }
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    
                    {/* Pagination Controls */}
                    {getTotalPages() > 1 && (
                      <div style={{ 
                        padding: '12px 16px', 
                        borderTop: '1px solid #f0f0f0',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        background: '#fafafa',
                        fontSize: '14px'
                      }}>
                        <div style={{ color: '#666' }}>
                          {(() => {
                            const range = getDisplayRange();
                            const pagination = executionResults?.pagination;
                            return (
                              <span>
                                Showing {range.start} to {range.end} of {range.total} rows
                                {pagination?.server_side && <span style={{ marginLeft: '8px', fontStyle: 'italic' }}>(server-side pagination)</span>}
                              </span>
                            );
                          })()}
                        </div>
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                          {paginationLoading && (
                            <span style={{ fontSize: '12px', color: '#999', marginRight: '8px' }}>Loading...</span>
                          )}
                          <button 
                            onClick={() => handlePageChange(1)}
                            disabled={getCurrentPage() === 1 || paginationLoading}
                            style={{
                              padding: '4px 8px',
                              border: '1px solid #ddd',
                              background: (getCurrentPage() === 1 || paginationLoading) ? '#f5f5f5' : 'white',
                              cursor: (getCurrentPage() === 1 || paginationLoading) ? 'not-allowed' : 'pointer',
                              borderRadius: '3px',
                              fontSize: '12px'
                            }}
                          >
                            First
                          </button>
                          <button 
                            onClick={() => handlePageChange(getCurrentPage() - 1)}
                            disabled={getCurrentPage() === 1 || paginationLoading}
                            style={{
                              padding: '4px 8px',
                              border: '1px solid #ddd',
                              background: (getCurrentPage() === 1 || paginationLoading) ? '#f5f5f5' : 'white',
                              cursor: (getCurrentPage() === 1 || paginationLoading) ? 'not-allowed' : 'pointer',
                              borderRadius: '3px',
                              fontSize: '12px'
                            }}
                          >
                            Previous
                          </button>
                          <span style={{ padding: '0 8px', color: '#666' }}>
                            Page {getCurrentPage()} of {getTotalPages()}
                          </span>
                          <button 
                            onClick={() => handlePageChange(getCurrentPage() + 1)}
                            disabled={getCurrentPage() === getTotalPages() || paginationLoading}
                            style={{
                              padding: '4px 8px',
                              border: '1px solid #ddd',
                              background: (getCurrentPage() === getTotalPages() || paginationLoading) ? '#f5f5f5' : 'white',
                              cursor: (getCurrentPage() === getTotalPages() || paginationLoading) ? 'not-allowed' : 'pointer',
                              borderRadius: '3px',
                              fontSize: '12px'
                            }}
                          >
                            Next
                          </button>
                          <button 
                            onClick={() => handlePageChange(getTotalPages())}
                            disabled={getCurrentPage() === getTotalPages() || paginationLoading}
                            style={{
                              padding: '4px 8px',
                              border: '1px solid #ddd',
                              background: (getCurrentPage() === getTotalPages() || paginationLoading) ? '#f5f5f5' : 'white',
                              cursor: (getCurrentPage() === getTotalPages() || paginationLoading) ? 'not-allowed' : 'pointer',
                              borderRadius: '3px',
                              fontSize: '12px'
                            }}
                          >
                            Last
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div style={{ 
                    color: '#666', 
                    background: '#f9f9f9', 
                    padding: '15px', 
                    borderRadius: '4px',
                    textAlign: 'center'
                  }}>
                    Query executed successfully but returned no results
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          <div style={{ 
            textAlign: 'center', 
            color: '#888', 
            fontSize: '16px',
            marginTop: '40px'
          }}>
            {loading ? (
              <div>
                <div style={{ marginBottom: '10px' }}>🤖</div>
                <div>AI is analyzing your question and querying the database...</div>
              </div>
            ) : (
              <div>
                <div style={{ marginBottom: '10px' }}>💬</div>
                <div>Ask a question about the patent database above to get started</div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}