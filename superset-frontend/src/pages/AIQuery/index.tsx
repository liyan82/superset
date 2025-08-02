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
import { SupersetClient, useCSSTextTruncation } from '@superset-ui/core';
import { Tooltip } from '@superset-ui/core/components';
import aiQueryGif from 'src/assets/images/ai-query.gif';

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

interface TruncatedCellProps {
  value: any;
  maxWidth?: string;
}

interface QueryHistory {
  id: string;
  question: string;
  timestamp: number;
  generatedSQL?: string;
  resultCount?: number;
  executionTime?: number;
  status: 'success' | 'error';
  error?: string;
  cachedResults?: ExecutionResults;
}

const TruncatedCell = ({ value, maxWidth = '750px' }: TruncatedCellProps) => {
  const [ref, isTruncated] = useCSSTextTruncation<HTMLDivElement>();
  const displayValue =
    value !== null && value !== undefined ? String(value) : null;

  if (!displayValue) {
    return <span style={{ color: '#999', fontStyle: 'italic' }}>N/A</span>;
  }

  return (
    <Tooltip title={isTruncated ? displayValue : null}>
      <div
        ref={ref}
        style={{
          maxWidth,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}
      >
        {displayValue}
      </div>
    </Tooltip>
  );
};

export default function AIQuery() {
  const [description, setDescription] = useState('');
  const [currentPlaceholder, setCurrentPlaceholder] = useState(0);
  const [queryHistory, setQueryHistory] = useState<QueryHistory[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [lastSubmittedQuery, setLastSubmittedQuery] = useState('');
  const [isPlaceholderMode, setIsPlaceholderMode] = useState(false);
  const [isFromHistory, setIsFromHistory] = useState(false);
  const [originalHistoryQuestion, setOriginalHistoryQuestion] = useState('');
  const [generatedQuery, setGeneratedQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [executionResults, setExecutionResults] =
    useState<ExecutionResults | null>(null);
  const [databaseConfig, setDatabaseConfig] = useState<DatabaseConfig | null>(
    null,
  );
  const [configLoading, setConfigLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(50);
  const [paginationLoading, setPaginationLoading] = useState(false);

  // Sorting state
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc');

  // Stopwatch state
  const [executionStartTime, setExecutionStartTime] = useState<number | null>(
    null,
  );
  const [elapsedTime, setElapsedTime] = useState(0);
  const [timerInterval, setTimerInterval] = useState<NodeJS.Timeout | null>(
    null,
  );

  // Example questions
  const exampleQuestions = [
    'Find all patents filed by the attorney John Doe',
    "Show me granted patents filed in 2023",
    "List patents related to artificial intelligence filed in 2024",
    'Get patents filed by Apple in the last 5 years',
    'Show me expired patents in the technology field',
  ];

  // Timer management functions
  const startStopwatch = () => {
    const startTime = Date.now();
    setExecutionStartTime(startTime);
    setElapsedTime(0);

    const interval = setInterval(() => {
      setElapsedTime(Date.now() - startTime);
    }, 100); // Update every 100ms for smooth display

    setTimerInterval(interval);
  };

  const stopStopwatch = () => {
    if (timerInterval) {
      clearInterval(timerInterval);
      setTimerInterval(null);
    }
  };

  // Clean up timer on unmount
  useEffect(
    () => () => {
      if (timerInterval) {
        clearInterval(timerInterval);
      }
    },
    [timerInterval],
  );

  // Rotate placeholder examples
  useEffect(() => {
    if (description.length === 0 && !isPlaceholderMode) {
      const interval = setInterval(() => {
        setCurrentPlaceholder(prev => (prev + 1) % exampleQuestions.length);
      }, 3000);
      return () => clearInterval(interval);
    }
    return undefined;
  }, [description.length, isPlaceholderMode, exampleQuestions.length]);

  // Handle clicking example questions
  const handleExampleClick = (example: string) => {
    setDescription(example);
    setIsPlaceholderMode(false);
    setIsFromHistory(false);
    setOriginalHistoryQuestion('');
  };

  // Handle textarea changes with placeholder mode
  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value;

    if (isPlaceholderMode) {
      // If in placeholder mode, any typing clears the placeholder and starts fresh
      setDescription(newValue);
      setIsPlaceholderMode(false);
      setIsFromHistory(false);
    } else {
      setDescription(newValue);
      // Check if user has modified the history question
      if (isFromHistory && newValue !== originalHistoryQuestion) {
        setIsFromHistory(false);
      }
    }
  };

  // Handle textarea focus
  const handleTextareaFocus = () => {
    if (isPlaceholderMode) {
      // Don't clear immediately on focus, wait for typing
      return;
    }
  };

  // Handle keyboard shortcuts
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      const currentText = isPlaceholderMode ? lastSubmittedQuery : description;
      if (
        !loading &&
        !configLoading &&
        databaseConfig?.success &&
        !isFromHistory &&
        currentText.trim()
      ) {
        // If in placeholder mode, we need to set the description before submitting
        if (isPlaceholderMode) {
          setDescription(lastSubmittedQuery);
          setIsPlaceholderMode(false);
        }
        handleGenerateAndExecuteQuery();
      }
    } else if (isPlaceholderMode && e.key.length === 1) {
      // Handle regular typing in placeholder mode
      e.preventDefault();
      setDescription(e.key);
      setIsPlaceholderMode(false);
    }
  };

  // Handle selecting from history
  const handleHistorySelect = (historyItem: QueryHistory) => {
    setDescription(historyItem.question);
    setShowHistory(false);
    setIsPlaceholderMode(false);
    setIsFromHistory(true);
    setOriginalHistoryQuestion(historyItem.question);

    // Restore the cached results if available
    if (historyItem.cachedResults) {
      setExecutionResults(historyItem.cachedResults);
      setGeneratedQuery(historyItem.generatedSQL || '');
      // Reset pagination and sorting to match original query
      setCurrentPage(1);
      setSortColumn(null);
      setSortDirection('asc');
    }
  };

  // Format timestamp for display
  const formatTimestamp = (timestamp: number) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();

    if (diffMs < 60 * 1000) {
      return 'Just now';
    } else if (diffMs < 60 * 60 * 1000) {
      const minutes = Math.floor(diffMs / (60 * 1000));
      return `${minutes}m ago`;
    } else if (diffMs < 24 * 60 * 60 * 1000) {
      const hours = Math.floor(diffMs / (60 * 60 * 1000));
      return `${hours}h ago`;
    } else {
      return date.toLocaleDateString();
    }
  };

  // LocalStorage utilities for query history
  const HISTORY_STORAGE_KEY = 'ai-query-history';
  const MAX_HISTORY_ITEMS = 50;

  const loadHistoryFromStorage = (): QueryHistory[] => {
    try {
      const stored = localStorage.getItem(HISTORY_STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        return Array.isArray(parsed) ? parsed : [];
      }
    } catch (error) {
      console.warn('Failed to load query history from localStorage:', error);
    }
    return [];
  };

  const saveHistoryToStorage = (history: QueryHistory[]) => {
    try {
      // Keep only the most recent items
      let trimmedHistory = history.slice(0, MAX_HISTORY_ITEMS);

      // Try to save, if it fails due to size, reduce cache size
      let serializedData = JSON.stringify(trimmedHistory);

      // If the serialized data is too large (>3MB), reduce cached results
      if (serializedData.length > 3 * 1024 * 1024) {
        trimmedHistory = trimmedHistory.map(item => ({
          ...item,
          cachedResults:
            item.status === 'success' && item.cachedResults
              ? {
                  ...item.cachedResults,
                  data: item.cachedResults.data?.slice(0, 100), // Keep only first 100 rows
                }
              : item.cachedResults,
        }));
        serializedData = JSON.stringify(trimmedHistory);
      }

      localStorage.setItem(HISTORY_STORAGE_KEY, serializedData);
    } catch (error) {
      console.warn('Failed to save query history to localStorage:', error);
      // If still failing, save without cached results
      try {
        const historyWithoutCache = history
          .slice(0, MAX_HISTORY_ITEMS)
          .map(item => ({
            ...item,
            cachedResults: undefined,
          }));
        localStorage.setItem(
          HISTORY_STORAGE_KEY,
          JSON.stringify(historyWithoutCache),
        );
      } catch (fallbackError) {
        console.warn('Failed to save even basic query history:', fallbackError);
      }
    }
  };

  const addToHistory = (historyItem: QueryHistory) => {
    setQueryHistory(prev => {
      // Remove any existing entry with the same question to avoid duplicates
      const filtered = prev.filter(
        item => item.question !== historyItem.question,
      );
      const newHistory = [historyItem, ...filtered];
      saveHistoryToStorage(newHistory);
      return newHistory;
    });
  };

  const deleteHistoryItem = (itemId: string) => {
    setQueryHistory(prev => {
      const filtered = prev.filter(item => item.id !== itemId);
      saveHistoryToStorage(filtered);
      return filtered;
    });
  };

  const clearAllHistory = () => {
    setQueryHistory([]);
    localStorage.removeItem(HISTORY_STORAGE_KEY);
    setShowHistory(false);
  };

  // Format elapsed time for display
  const formatElapsedTime = (milliseconds: number) => {
    const seconds = Math.floor(milliseconds / 1000);
    const ms = Math.floor((milliseconds % 1000) / 100);
    return `${seconds}.${ms}s`;
  };

  // Handle column sorting
  const handleSort = (columnName: string) => {
    if (sortColumn === columnName) {
      // Toggle direction if same column
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      // New column, start with ascending
      setSortColumn(columnName);
      setSortDirection('asc');
    }
    // Reset to first page when sorting changes
    setCurrentPage(1);
  };

  // Sort data function
  const sortData = (data: Record<string, any>[]) => {
    if (!sortColumn || !data) return data;

    return [...data].sort((a, b) => {
      const aValue = a[sortColumn];
      const bValue = b[sortColumn];

      // Handle null/undefined values
      if (aValue == null && bValue == null) return 0;
      if (aValue == null) return sortDirection === 'asc' ? 1 : -1;
      if (bValue == null) return sortDirection === 'asc' ? -1 : 1;

      // Convert to strings for comparison
      const aStr = String(aValue).toLowerCase();
      const bStr = String(bValue).toLowerCase();

      // Try numeric comparison first
      const aNum = Number(aValue);
      const bNum = Number(bValue);

      if (!Number.isNaN(aNum) && !Number.isNaN(bNum)) {
        // Both are numbers
        return sortDirection === 'asc' ? aNum - bNum : bNum - aNum;
      }

      // String comparison
      if (aStr < bStr) return sortDirection === 'asc' ? -1 : 1;
      if (aStr > bStr) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  };

  // Load query history from localStorage on component mount
  useEffect(() => {
    const history = loadHistoryFromStorage();
    setQueryHistory(history);
  }, []);

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
          error: 'Failed to load database configuration',
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

    const queryStartTime = Date.now();
    const currentQuery = (
      isPlaceholderMode ? lastSubmittedQuery : description
    ).trim();

    setLoading(true);
    setExecutionResults(null);
    setGeneratedQuery('');
    setCurrentPage(1);
    // Reset sorting when new query is executed
    setSortColumn(null);
    setSortDirection('asc');
    setShowHistory(false);

    // Set placeholder mode after submitting
    setLastSubmittedQuery(currentQuery);
    setDescription(''); // Clear the actual description
    setIsPlaceholderMode(true);
    setIsFromHistory(false);
    setOriginalHistoryQuestion('');

    // Start the stopwatch
    startStopwatch();

    try {
      // Step 1: Generate SQL query
      const generateResponse = await SupersetClient.post({
        endpoint: '/ai-query/generate',
        body: JSON.stringify({ description: currentQuery }),
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const sqlQuery = generateResponse.json.query;
      setGeneratedQuery(sqlQuery || 'No query generated');

      if (!sqlQuery || generateResponse.json.success === false) {
        const errorResult = {
          success: false,
          error:
            generateResponse.json.error ||
            "I'm having trouble understanding that. Could you try asking differently?",
          data: null,
        };
        setExecutionResults(errorResult);

        // Save failed query to history
        addToHistory({
          id: `query_${Date.now()}`,
          question: currentQuery,
          timestamp: queryStartTime,
          status: 'error',
          error: errorResult.error,
          executionTime: Date.now() - queryStartTime,
          cachedResults: errorResult,
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

      const results = executeResponse.json;
      setExecutionResults(results);

      // Save successful query to history
      if (results.success !== false) {
        addToHistory({
          id: `query_${Date.now()}`,
          question: currentQuery,
          timestamp: queryStartTime,
          generatedSQL: sqlQuery,
          resultCount:
            results.data?.length || results.pagination?.total_count || 0,
          status: 'success',
          executionTime: Date.now() - queryStartTime,
          cachedResults: results,
        });
      } else {
        // Save failed execution to history
        addToHistory({
          id: `query_${Date.now()}`,
          question: currentQuery,
          timestamp: queryStartTime,
          generatedSQL: sqlQuery,
          status: 'error',
          error: results.error,
          executionTime: Date.now() - queryStartTime,
          cachedResults: results,
        });
      }
    } catch (error) {
      const errorResult = {
        success: false,
        error: error.message,
        data: null,
      };
      setExecutionResults(errorResult);

      // Save failed query to history
      addToHistory({
        id: `query_${Date.now()}`,
        question: currentQuery,
        timestamp: queryStartTime,
        status: 'error',
        error: error.message,
        executionTime: Date.now() - queryStartTime,
        cachedResults: errorResult,
      });
    } finally {
      setLoading(false);
      stopStopwatch();
    }
  };

  // Handle pagination for server-side paginated results
  const handlePageChange = async (newPage: number) => {
    if (!executionResults || !generatedQuery) return;

    const { pagination } = executionResults;
    if (pagination?.server_side) {
      // Server-side pagination: make new request
      setPaginationLoading(true);
      setCurrentPage(newPage);

      // Start stopwatch for pagination request
      startStopwatch();

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
        stopStopwatch();
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
      // Server-side pagination: data is already the current page, but we can still sort it
      const data = executionResults?.data || [];
      return sortData(data);
    }
    // Client-side pagination: sort first, then slice the data
    if (!executionResults?.data) return [];
    const sortedData = sortData(executionResults.data);
    const startIndex = (currentPage - 1) * pageSize;
    const endIndex = startIndex + pageSize;
    return sortedData.slice(startIndex, endIndex);
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
      const start = (currentPageNum - 1) * pageSize + 1;
      const end = Math.min(currentPageNum * pageSize, totalCount);
      return { start, end, total: totalCount };
    }
    const start = (currentPage - 1) * pageSize + 1;
    const end = Math.min(currentPage * pageSize, totalCount);
    return { start, end, total: totalCount };
  };

  return (
    <div
      style={{
        height: '100vh',
        display: 'flex',
        flexDirection: 'column',
        padding: '20px',
        gap: '20px',
      }}
    >
      <div style={{ textAlign: 'center', marginBottom: '20px', flexShrink: 0 }}>
        <h1 style={{ margin: '0 0 10px 0', color: '#333', fontSize: '28px' }}>
          AI Query Assistant
        </h1>
      </div>

      <div
        style={{
          background: '#f9f9f9',
          border: '1px solid #ddd',
          borderRadius: '8px',
          padding: '20px',
          flexShrink: 0,
        }}
      >
        <h2 style={{ marginTop: '0', marginBottom: '8px', color: '#444' }}>
          What would you like to know?
        </h2>
        <p style={{ margin: '0 0 15px 0', color: '#666', fontSize: '14px' }}>
          Ask questions about the patent database in plain English
        </p>
        <textarea
          placeholder={
            isPlaceholderMode ? '' : exampleQuestions[currentPlaceholder]
          }
          value={isPlaceholderMode ? lastSubmittedQuery : description}
          onChange={handleTextareaChange}
          onKeyDown={handleKeyDown}
          onFocus={e => {
            e.target.style.borderColor = '#1890ff';
            handleTextareaFocus();
          }}
          onBlur={e => (e.target.style.borderColor = '#e1e5e9')}
          style={{
            width: '100%',
            height:
              description.length > 0 || isPlaceholderMode ? '100px' : '60px',
            padding: '12px',
            border: '2px solid #e1e5e9',
            borderRadius: '6px',
            fontSize: '14px',
            resize: 'vertical',
            outline: 'none',
            transition: 'border-color 0.2s, height 0.2s',
            color: isPlaceholderMode ? '#999' : '#333',
            fontStyle: isPlaceholderMode ? 'italic' : 'normal',
          }}
        />

        <div style={{ marginTop: '15px' }}>
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '10px',
              minHeight: '18px',
            }}
          >
            <div>
              {description.length === 0 && !isPlaceholderMode && (
                <p style={{ margin: '0', color: '#666', fontSize: '13px' }}>
                  💡 Try these examples:
                </p>
              )}
            </div>
            <div>
              {queryHistory.length > 0 && (
                <button
                  onClick={() => setShowHistory(!showHistory)}
                  style={{
                    padding: '4px 8px',
                    background: 'transparent',
                    border: '1px solid #d9d9d9',
                    borderRadius: '4px',
                    color: '#666',
                    fontSize: '12px',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.borderColor = '#1890ff';
                    e.currentTarget.style.color = '#1890ff';
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.borderColor = '#d9d9d9';
                    e.currentTarget.style.color = '#666';
                  }}
                >
                  📝 History ({queryHistory.length})
                </button>
              )}
            </div>
          </div>

          {showHistory && queryHistory.length > 0 ? (
            <div>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '8px 12px',
                  background: '#f5f5f5',
                  borderBottom: '1px solid #e8e8e8',
                  fontSize: '12px',
                  color: '#666',
                }}
              >
                <span>Recent Queries</span>
                <button
                  onClick={clearAllHistory}
                  style={{
                    padding: '2px 6px',
                    background: 'transparent',
                    border: '1px solid #d9d9d9',
                    borderRadius: '3px',
                    color: '#666',
                    fontSize: '11px',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.borderColor = '#ff4d4f';
                    e.currentTarget.style.color = '#ff4d4f';
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.borderColor = '#d9d9d9';
                    e.currentTarget.style.color = '#666';
                  }}
                >
                  Clear All
                </button>
              </div>
              <div
                style={{
                  maxHeight: '200px',
                  overflowY: 'auto',
                  border: '1px solid #e8e8e8',
                  borderRadius: '0 0 4px 4px',
                  background: '#fafafa',
                }}
              >
                {queryHistory.slice(0, 10).map(item => (
                  <div
                    key={item.id}
                    style={{
                      padding: '8px 12px',
                      borderBottom: '1px solid #f0f0f0',
                      transition: 'background-color 0.2s',
                      position: 'relative',
                    }}
                    onMouseEnter={e => {
                      e.currentTarget.style.backgroundColor = '#e6f4ff';
                    }}
                    onMouseLeave={e => {
                      e.currentTarget.style.backgroundColor = 'transparent';
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'start',
                        gap: '8px',
                      }}
                    >
                      <div
                        style={{ flex: 1, minWidth: 0, cursor: 'pointer' }}
                        onClick={() => handleHistorySelect(item)}
                      >
                        <div
                          style={{
                            fontSize: '13px',
                            color: '#333',
                            marginBottom: '2px',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {item.question}
                        </div>
                        <div
                          style={{
                            fontSize: '11px',
                            color: '#999',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                          }}
                        >
                          <span>{formatTimestamp(item.timestamp)}</span>
                          {item.status === 'success' ? (
                            <span style={{ color: '#52c41a' }}>
                              ✓ {item.resultCount} results (cached)
                            </span>
                          ) : (
                            <span style={{ color: '#ff4d4f' }}>
                              ✗ Failed (cached)
                            </span>
                          )}
                        </div>
                      </div>
                      <button
                        onClick={e => {
                          e.stopPropagation();
                          deleteHistoryItem(item.id);
                        }}
                        style={{
                          padding: '2px 4px',
                          background: 'transparent',
                          border: 'none',
                          color: '#999',
                          fontSize: '12px',
                          cursor: 'pointer',
                          borderRadius: '2px',
                          transition: 'all 0.2s',
                          flexShrink: 0,
                        }}
                        onMouseEnter={e => {
                          e.currentTarget.style.background = '#fff2f0';
                          e.currentTarget.style.color = '#ff4d4f';
                        }}
                        onMouseLeave={e => {
                          e.currentTarget.style.background = 'transparent';
                          e.currentTarget.style.color = '#999';
                        }}
                        title="Delete this query"
                      >
                        ✕
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : description.length === 0 && !isPlaceholderMode ? (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {exampleQuestions.slice(0, 3).map((example, idx) => (
                <button
                  key={idx}
                  onClick={() => handleExampleClick(example)}
                  style={{
                    padding: '6px 12px',
                    background: '#f0f8ff',
                    border: '1px solid #d6e4ff',
                    borderRadius: '20px',
                    color: '#1890ff',
                    fontSize: '12px',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.background = '#e6f4ff';
                    e.currentTarget.style.borderColor = '#91caff';
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.background = '#f0f8ff';
                    e.currentTarget.style.borderColor = '#d6e4ff';
                  }}
                >
                  {example.length > 50 ? `${example.slice(0, 47)}...` : example}
                </button>
              ))}
            </div>
          ) : null}
        </div>
        <div
          style={{
            display: 'flex',
            justifyContent: 'flex-end',
            marginTop: '5px',
            fontSize: '12px',
            color: isPlaceholderMode
              ? '#ccc'
              : description.length > 720
                ? '#ff4d4f'
                : description.length > 640
                  ? '#fa8c16'
                  : '#999',
          }}
        >
          {isPlaceholderMode
            ? `${lastSubmittedQuery.length} characters (previous query)`
            : `${800 - description.length} characters remaining`}
        </div>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            marginTop: '15px',
          }}
        >
          <button
            onClick={handleGenerateAndExecuteQuery}
            disabled={
              loading ||
              configLoading ||
              !databaseConfig?.success ||
              isFromHistory
            }
            style={{
              padding: '12px 24px',
              background:
                loading ||
                configLoading ||
                !databaseConfig?.success ||
                isFromHistory
                  ? '#ccc'
                  : '#1890ff',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor:
                loading ||
                configLoading ||
                !databaseConfig?.success ||
                isFromHistory
                  ? 'not-allowed'
                  : 'pointer',
              fontSize: '16px',
              fontWeight: 'bold',
            }}
          >
            {loading
              ? 'Processing...'
              : configLoading
                ? 'Loading...'
                : !databaseConfig?.success
                  ? 'Database Unavailable'
                  : isFromHistory
                    ? 'Modify to Ask Again'
                    : 'Ask AI'}
          </button>
          {!loading &&
            !configLoading &&
            databaseConfig?.success &&
            !isFromHistory && (
              <span style={{ fontSize: '12px', color: '#999' }}>
                or press {navigator.platform.includes('Mac') ? '⌘' : 'Ctrl'}
                +Enter
              </span>
            )}
        </div>

        {databaseConfig && !databaseConfig.success && (
          <div
            style={{
              marginTop: '15px',
              padding: '10px',
              background: '#fff2f0',
              border: '1px solid #ffccc7',
              borderRadius: '4px',
              color: '#ff4d4f',
              fontSize: '14px',
            }}
          >
            <strong>Configuration Error:</strong> {databaseConfig.error}
          </div>
        )}
      </div>

      <div
        style={{
          background: '#f0f0f0',
          border: '1px solid #ddd',
          borderRadius: '8px',
          padding: '20px',
          flex: '1',
          minHeight: '400px',
          overflow: 'auto',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {(loading || paginationLoading) && executionStartTime && (
          <div
            style={{
              display: 'flex',
              justifyContent: 'flex-end',
              alignItems: 'center',
              marginBottom: '15px',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontSize: '14px',
              }}
            >
              <span style={{ color: '#666' }}>⏱️</span>
              <span
                style={{
                  color: elapsedTime > 60000 ? '#ff4d4f' : '#1890ff',
                  fontWeight: 'bold',
                  fontFamily: 'monospace',
                }}
              >
                {formatElapsedTime(elapsedTime)}
              </span>
            </div>
          </div>
        )}

        {/* Warning message when execution exceeds 1 minute */}
        {(loading || paginationLoading) && elapsedTime > 30000 && (
          <div
            style={{
              background: '#fff7e6',
              border: '1px solid #ffd591',
              borderRadius: '8px',
              padding: '16px',
              marginBottom: '16px',
              color: '#d48806',
            }}
          >
            <div
              style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}
            >
              <span style={{ fontSize: '18px', marginTop: '2px' }}>⚠️</span>
              <div>
                <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>
                  Query Taking Longer Than Expected
                </div>
                <div style={{ lineHeight: '1.5', fontSize: '14px' }}>
                  Your query has been running for over 1 minute. You can
                  continue waiting, but there's a possibility that the search
                  clause might be too complex for our AI interpreter to process
                  efficiently.
                </div>
                <div
                  style={{
                    marginTop: '12px',
                    padding: '12px',
                    background: '#fafafa',
                    borderRadius: '4px',
                    fontSize: '14px',
                    lineHeight: '1.5',
                  }}
                >
                  <strong>Need the dataset?</strong> If you really need this
                  specific data, please reach out to us at{' '}
                  <a
                    href="mailto:support@patent1024.com"
                    style={{ color: '#1890ff', textDecoration: 'none' }}
                    onMouseOver={e =>
                      ((e.target as HTMLAnchorElement).style.textDecoration =
                        'underline')
                    }
                    onMouseOut={e =>
                      ((e.target as HTMLAnchorElement).style.textDecoration =
                        'none')
                    }
                  >
                    support@patent1024.com
                  </a>{' '}
                  to get the dataset. We offer data mining services at
                  competitive prices below market rates.
                </div>
              </div>
            </div>
          </div>
        )}

        {executionResults ? (
          <div>
            {executionResults.error ? (
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                  height: '100%',
                  minHeight: '300px',
                }}
              >
                <div
                  style={{
                    color: '#ff4d4f',
                    background: '#fff2f0',
                    padding: '20px',
                    borderRadius: '8px',
                    border: '1px solid #ffccc7',
                    textAlign: 'center',
                    maxWidth: '400px',
                    fontSize: '16px',
                    lineHeight: '1.5',
                  }}
                >
                  {executionResults.error}
                </div>
              </div>
            ) : (
              <div>
                {executionResults.data && executionResults.data.length > 0 ? (
                  <div
                    style={{
                      background: 'white',
                      border: '1px solid #ddd',
                      borderRadius: '4px',
                      display: 'flex',
                      flexDirection: 'column',
                      height: '400px',
                      position: 'relative',
                    }}
                  >
                    {/* Table with sticky header and scrollable content */}
                    <div
                      style={{
                        flex: '1',
                        overflow: 'auto',
                        display: 'block',
                      }}
                    >
                      <table
                        style={{
                          width: '100%',
                          borderCollapse: 'collapse',
                          fontSize: '14px',
                          minWidth: `${(executionResults.columns?.length || 0) * 150}px`,
                        }}
                      >
                        <thead
                          style={{
                            position: 'sticky',
                            top: 0,
                            background: '#f8f9fa',
                            borderBottom: '2px solid #e0e0e0',
                            zIndex: 1,
                          }}
                        >
                          <tr>
                            {executionResults.columns &&
                              executionResults.columns.map(
                                (col: Column, idx: number) => (
                                  <th
                                    key={idx}
                                    onClick={() => handleSort(col.name)}
                                    style={{
                                      minWidth: '150px',
                                      padding: '12px 16px',
                                      textAlign: 'left',
                                      fontWeight: 'bold',
                                      fontSize: '14px',
                                      borderRight:
                                        idx <
                                        executionResults.columns!.length - 1
                                          ? '1px solid #e0e0e0'
                                          : 'none',
                                      whiteSpace: 'nowrap',
                                      cursor: 'pointer',
                                      userSelect: 'none',
                                      transition: 'background-color 0.2s',
                                      background: '#f8f9fa',
                                    }}
                                    onMouseEnter={e => {
                                      (
                                        e.target as HTMLElement
                                      ).style.backgroundColor = '#e9ecef';
                                    }}
                                    onMouseLeave={e => {
                                      (
                                        e.target as HTMLElement
                                      ).style.backgroundColor = '#f8f9fa';
                                    }}
                                  >
                                    <div
                                      style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'space-between',
                                      }}
                                    >
                                      <span>{col.name}</span>
                                      <span
                                        style={{
                                          marginLeft: '8px',
                                          opacity:
                                            sortColumn === col.name ? 1 : 0.3,
                                          fontSize: '12px',
                                        }}
                                      >
                                        {sortColumn === col.name
                                          ? sortDirection === 'asc'
                                            ? '▲'
                                            : '▼'
                                          : '▲'}
                                      </span>
                                    </div>
                                  </th>
                                ),
                              )}
                          </tr>
                        </thead>
                        <tbody>
                          {getCurrentPageData().map(
                            (row: Record<string, any>, rowIdx: number) => (
                              <tr
                                key={rowIdx}
                                style={{
                                  borderBottom: '1px solid #f0f0f0',
                                }}
                              >
                                {executionResults.columns!.map(
                                  (col: Column, colIdx: number) => (
                                    <td
                                      key={colIdx}
                                      style={{
                                        minWidth: '150px',
                                        padding: '12px 16px',
                                        borderRight:
                                          colIdx <
                                          executionResults.columns!.length - 1
                                            ? '1px solid #e0e0e0'
                                            : 'none',
                                      }}
                                    >
                                      <TruncatedCell value={row[col.name]} />
                                    </td>
                                  ),
                                )}
                              </tr>
                            ),
                          )}
                        </tbody>
                      </table>
                    </div>

                    {/* Fixed Pagination Controls */}
                    {getTotalPages() > 1 && (
                      <div
                        style={{
                          padding: '12px 16px',
                          borderTop: '1px solid #f0f0f0',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          background: '#fafafa',
                          fontSize: '14px',
                          flexShrink: 0,
                        }}
                      >
                        <div style={{ color: '#666' }}>
                          {(() => {
                            const range = getDisplayRange();
                            const pagination = executionResults?.pagination;
                            return (
                              <span>
                                Showing {range.start} to {range.end} of{' '}
                                {range.total} rows
                                {pagination?.server_side && (
                                  <span
                                    style={{
                                      marginLeft: '8px',
                                      fontStyle: 'italic',
                                    }}
                                  >
                                    (server-side pagination)
                                  </span>
                                )}
                              </span>
                            );
                          })()}
                        </div>
                        <div
                          style={{
                            display: 'flex',
                            gap: '8px',
                            alignItems: 'center',
                          }}
                        >
                          {paginationLoading && (
                            <div
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                marginRight: '8px',
                              }}
                            >
                              <img
                                src={aiQueryGif}
                                alt="Loading page..."
                                style={{
                                  width: '24px',
                                  height: '24px',
                                  borderRadius: '4px',
                                }}
                              />
                            </div>
                          )}
                          <button
                            onClick={() => handlePageChange(1)}
                            disabled={
                              getCurrentPage() === 1 || paginationLoading
                            }
                            style={{
                              padding: '4px 8px',
                              border: '1px solid #ddd',
                              background:
                                getCurrentPage() === 1 || paginationLoading
                                  ? '#f5f5f5'
                                  : 'white',
                              cursor:
                                getCurrentPage() === 1 || paginationLoading
                                  ? 'not-allowed'
                                  : 'pointer',
                              borderRadius: '3px',
                              fontSize: '12px',
                            }}
                          >
                            First
                          </button>
                          <button
                            onClick={() =>
                              handlePageChange(getCurrentPage() - 1)
                            }
                            disabled={
                              getCurrentPage() === 1 || paginationLoading
                            }
                            style={{
                              padding: '4px 8px',
                              border: '1px solid #ddd',
                              background:
                                getCurrentPage() === 1 || paginationLoading
                                  ? '#f5f5f5'
                                  : 'white',
                              cursor:
                                getCurrentPage() === 1 || paginationLoading
                                  ? 'not-allowed'
                                  : 'pointer',
                              borderRadius: '3px',
                              fontSize: '12px',
                            }}
                          >
                            Previous
                          </button>
                          <span style={{ padding: '0 8px', color: '#666' }}>
                            Page {getCurrentPage()} of {getTotalPages()}
                          </span>
                          <button
                            onClick={() =>
                              handlePageChange(getCurrentPage() + 1)
                            }
                            disabled={
                              getCurrentPage() === getTotalPages() ||
                              paginationLoading
                            }
                            style={{
                              padding: '4px 8px',
                              border: '1px solid #ddd',
                              background:
                                getCurrentPage() === getTotalPages() ||
                                paginationLoading
                                  ? '#f5f5f5'
                                  : 'white',
                              cursor:
                                getCurrentPage() === getTotalPages() ||
                                paginationLoading
                                  ? 'not-allowed'
                                  : 'pointer',
                              borderRadius: '3px',
                              fontSize: '12px',
                            }}
                          >
                            Next
                          </button>
                          <button
                            onClick={() => handlePageChange(getTotalPages())}
                            disabled={
                              getCurrentPage() === getTotalPages() ||
                              paginationLoading
                            }
                            style={{
                              padding: '4px 8px',
                              border: '1px solid #ddd',
                              background:
                                getCurrentPage() === getTotalPages() ||
                                paginationLoading
                                  ? '#f5f5f5'
                                  : 'white',
                              cursor:
                                getCurrentPage() === getTotalPages() ||
                                paginationLoading
                                  ? 'not-allowed'
                                  : 'pointer',
                              borderRadius: '3px',
                              fontSize: '12px',
                            }}
                          >
                            Last
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div
                    style={{
                      color: '#666',
                      background: '#f9f9f9',
                      padding: '15px',
                      borderRadius: '4px',
                      textAlign: 'center',
                    }}
                  >
                    Query executed successfully but returned no results
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          <div
            style={{
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              height: '100%',
              minHeight: '300px',
            }}
          >
            {loading ? (
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: '20px',
                }}
              >
                <img
                  src={aiQueryGif}
                  alt="AI processing animation"
                  style={{
                    width: '120px',
                    height: 'auto',
                    borderRadius: '8px',
                  }}
                />
                <div
                  style={{
                    color: '#888',
                    fontSize: '16px',
                    textAlign: 'center',
                  }}
                >
                  AI is analyzing your question and querying the database...
                </div>
              </div>
            ) : (
              <div
                style={{
                  textAlign: 'center',
                  color: '#888',
                  fontSize: '16px',
                }}
              >
                <div style={{ marginBottom: '10px' }}>💬</div>
                <div>
                  Ask a question about the patent database above to get started
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
