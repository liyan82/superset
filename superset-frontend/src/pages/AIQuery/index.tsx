import React, { useState, useEffect } from 'react';
import { SupersetClient } from '@superset-ui/core';

export default function AIQuery() {
  const [description, setDescription] = useState('');
  const [generatedQuery, setGeneratedQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [executionResults, setExecutionResults] = useState(null);
  const [showSQL, setShowSQL] = useState(false);
  const [databaseConfig, setDatabaseConfig] = useState(null);
  const [configLoading, setConfigLoading] = useState(true);

  // Fetch database configuration on component mount
  useEffect(() => {
    const fetchDatabaseConfig = async () => {
      try {
        const response = await SupersetClient.get({
          endpoint: '/ai-query/config',
        });
        setDatabaseConfig(response.json);
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
    setShowSQL(false);
    
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
      
      {generatedQuery && showSQL && (
        <div style={{ 
          background: '#f9f9f9', 
          border: '1px solid #ddd', 
          borderRadius: '8px', 
          padding: '20px',
          flexShrink: 0
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
            <h3 style={{ margin: '0', color: '#555' }}>Generated SQL Query</h3>
            <button 
              onClick={() => setShowSQL(false)}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#666',
                cursor: 'pointer',
                fontSize: '18px',
                padding: '0'
              }}
              title="Hide SQL"
            >
              ✕
            </button>
          </div>
          <pre style={{ 
            background: 'white', 
            padding: '15px', 
            borderRadius: '4px',
            border: '1px solid #ddd',
            fontSize: '14px',
            overflow: 'auto',
            margin: '0'
          }}>
            {generatedQuery}
          </pre>
        </div>
      )}
      
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
          {generatedQuery && !showSQL && executionResults && (
            <button 
              onClick={() => setShowSQL(true)}
              style={{
                padding: '6px 12px',
                background: '#f8f9fa',
                border: '1px solid #ddd',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '12px',
                color: '#666'
              }}
              title="View generated SQL query"
            >
              Show SQL
            </button>
          )}
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
                    overflow: 'auto',
                    flex: '1',
                    minHeight: '300px'
                  }}>
                    <table style={{ 
                      width: '100%', 
                      borderCollapse: 'collapse',
                      fontSize: '14px',
                      height: '100%'
                    }}>
                      <thead>
                        <tr style={{ background: '#fafafa' }}>
                          {executionResults.columns && executionResults.columns.map((col, idx) => (
                            <th key={idx} style={{ 
                              padding: '12px 16px', 
                              textAlign: 'left',
                              borderBottom: '2px solid #e0e0e0',
                              fontWeight: 'bold',
                              background: '#f8f9fa',
                              fontSize: '14px'
                            }}>
                              {col.name}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {executionResults.data.slice(0, 50).map((row, rowIdx) => (
                          <tr key={rowIdx} style={{ 
                            borderBottom: '1px solid #f0f0f0'
                          }}>
                            {executionResults.columns.map((col, colIdx) => (
                              <td key={colIdx} style={{ 
                                padding: '12px 16px',
                                maxWidth: '250px',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap',
                                borderBottom: '1px solid #f0f0f0'
                              }}>
                                {row[col.name] !== null ? String(row[col.name]) : 'NULL'}
                              </td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {executionResults.data.length > 50 && (
                      <div style={{ 
                        padding: '10px', 
                        textAlign: 'center', 
                        color: '#666',
                        borderTop: '1px solid #f0f0f0'
                      }}>
                        Showing first 50 of {executionResults.data.length} rows
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