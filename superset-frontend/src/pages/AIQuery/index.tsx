import React, { useState } from 'react';
import { SupersetClient } from '@superset-ui/core';

export default function AIQuery() {
  const [description, setDescription] = useState('');
  const [generatedQuery, setGeneratedQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [executionResults, setExecutionResults] = useState(null);

  const handleGenerateQuery = async () => {
    setLoading(true);
    setExecutionResults(null);
    try {
      const response = await SupersetClient.post({
        endpoint: '/ai-query/generate',
        body: JSON.stringify({ description }),
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      setGeneratedQuery(response.json.query || 'No query generated');
    } catch (error) {
      setGeneratedQuery('Error generating query: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleExecuteQuery = async () => {
    if (!generatedQuery || generatedQuery.includes('Error')) {
      return;
    }

    setExecuting(true);
    try {
      const response = await SupersetClient.post({
        endpoint: '/ai-query/execute',
        body: JSON.stringify({
          database_id: 3, // USPTO database
          sql: generatedQuery,
          queryLimit: 1000,
          client_id: `ai_${Date.now().toString().slice(-8)}`,
          expand_data: true,
        }),
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      setExecutionResults(response.json);
    } catch (error) {
      setExecutionResults({
        success: false,
        error: error.message,
        data: null,
      });
    } finally {
      setExecuting(false);
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
          AI Query
        </h1>
        <p style={{ margin: '0', color: '#666', fontSize: '16px' }}>
          Use artificial intelligence to generate and execute SQL queries
        </p>
      </div>
      
      <div style={{ 
        background: '#f9f9f9', 
        border: '1px solid #ddd', 
        borderRadius: '8px', 
        padding: '20px',
        flexShrink: 0
      }}>
        <h2 style={{ marginTop: '0', marginBottom: '15px', color: '#444' }}>
          Query Input
        </h2>
        <textarea 
          placeholder="Describe what you want to query..." 
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          style={{
            width: '100%',
            height: '100px',
            padding: '10px',
            border: '1px solid #ccc',
            borderRadius: '4px',
            fontSize: '14px',
            resize: 'vertical'
          }}
        />
        <button 
          onClick={handleGenerateQuery}
          disabled={loading}
          style={{
            marginTop: '15px',
            padding: '10px 20px',
            background: loading ? '#ccc' : '#1890ff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: loading ? 'not-allowed' : 'pointer',
            fontSize: '14px'
          }}
        >
          {loading ? 'Generating...' : 'Generate Query'}
        </button>
      </div>
      
      {generatedQuery && (
        <div style={{ 
          background: '#f9f9f9', 
          border: '1px solid #ddd', 
          borderRadius: '8px', 
          padding: '20px',
          flexShrink: 0
        }}>
          <h3 style={{ marginTop: '0', color: '#555' }}>Generated SQL Query</h3>
          <pre style={{ 
            background: 'white', 
            padding: '15px', 
            borderRadius: '4px',
            border: '1px solid #ddd',
            fontSize: '14px',
            overflow: 'auto',
            marginBottom: '15px'
          }}>
            {generatedQuery}
          </pre>
          <button 
            onClick={handleExecuteQuery}
            disabled={executing || generatedQuery.includes('Error')}
            style={{
              padding: '10px 20px',
              background: executing ? '#ccc' : '#52c41a',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: executing || generatedQuery.includes('Error') ? 'not-allowed' : 'pointer',
              fontSize: '14px'
            }}
          >
            {executing ? 'Executing...' : 'Execute Query'}
          </button>
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
        <h3 style={{ marginTop: '0', color: '#555' }}>Query Results</h3>
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
          <p style={{ color: '#888', fontStyle: 'italic' }}>
            Query execution results will appear here...
          </p>
        )}
      </div>
    </div>
  );
}