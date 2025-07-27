import React, { useState } from 'react';
import { SupersetClient } from '@superset-ui/core';

export default function AIQuery() {
  const [description, setDescription] = useState('');
  const [result, setResult] = useState('');
  const [loading, setLoading] = useState(false);

  const handleGenerateQuery = async () => {
    setLoading(true);
    try {
      const response = await SupersetClient.post({
        endpoint: '/ai-query/generate',
        body: JSON.stringify({ description }),
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      setResult(response.json.query || 'No query generated');
    } catch (error) {
      setResult('Error generating query: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ 
      height: '100vh', 
      display: 'flex', 
      flexDirection: 'column',
      padding: '20px'
    }}>
      <h1 style={{ textAlign: 'center', marginBottom: '20px', color: '#333' }}>
        AI Query
      </h1>
      <p style={{ textAlign: 'center', color: '#666', fontSize: '16px', marginBottom: '40px' }}>
        Use artificial intelligence to generate and execute SQL queries
      </p>
      
      <div style={{ 
        background: '#f9f9f9', 
        border: '1px solid #ddd', 
        borderRadius: '8px', 
        padding: '30px',
        marginBottom: '20px'
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
      
      <div style={{ 
        background: '#f0f0f0', 
        border: '1px solid #ddd', 
        borderRadius: '8px', 
        padding: '20px',
        flex: '1',
        overflow: 'auto'
      }}>
        <h3 style={{ marginTop: '0', color: '#555' }}>Results</h3>
        {result ? (
          <pre style={{ 
            background: 'white', 
            padding: '10px', 
            borderRadius: '4px',
            border: '1px solid #ddd',
            fontSize: '14px',
            overflow: 'auto'
          }}>
            {result}
          </pre>
        ) : (
          <p style={{ color: '#888', fontStyle: 'italic' }}>
            Generated query and results will appear here...
          </p>
        )}
      </div>
    </div>
  );
}