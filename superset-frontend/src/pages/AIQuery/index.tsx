import React from 'react';

export default function AIQuery() {
  return (
    <div style={{ 
      height: '100vh', 
      display: 'flex', 
      flexDirection: 'column',
      padding: '20px', 
      maxWidth: '1200px', 
      margin: '0 auto' 
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
        <button style={{
          marginTop: '15px',
          padding: '10px 20px',
          background: '#1890ff',
          color: 'white',
          border: 'none',
          borderRadius: '4px',
          cursor: 'pointer',
          fontSize: '14px'
        }}>
          Generate Query
        </button>
      </div>
      
      <div style={{ 
        background: '#f0f0f0', 
        border: '1px solid #ddd', 
        borderRadius: '8px', 
        padding: '20px' 
      }}>
        <h3 style={{ marginTop: '0', color: '#555' }}>Results</h3>
        <p style={{ color: '#888', fontStyle: 'italic' }}>
          Generated query and results will appear here...
        </p>
      </div>
    </div>
  );
}