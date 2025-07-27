# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import logging
import os
from typing import Optional, Dict, Any
import requests

logger = logging.getLogger(__name__)


class GeminiService:
    """Service for interacting with Google Gemini AI to generate SQL queries."""
    
    def __init__(self, api_key: Optional[str] = None):
        # Try to get API key from multiple sources
        self.api_key = api_key
        self.schema_context = None
        
        if not self.api_key:
            try:
                from flask import current_app
                self.api_key = current_app.config.get("GEMINI_API_KEY")
                self.schema_context = current_app.config.get("GEMINI_SCHEMA_CONTEXT")
            except RuntimeError:
                # Not in application context, try importing app
                try:
                    from superset import app
                    self.api_key = app.config.get("GEMINI_API_KEY")
                    self.schema_context = app.config.get("GEMINI_SCHEMA_CONTEXT")
                except Exception:
                    pass
        
        if not self.api_key:
            self.api_key = os.getenv("GEMINI_API_KEY")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
        
    def generate_sql_query(self, description: str, schema_info: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate SQL query from natural language description.
        
        Args:
            description: Natural language description of what user wants to query
            schema_info: Optional database schema information for context
            
        Returns:
            Dict containing the generated query and metadata
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "Gemini API key not configured",
                "query": None
            }
            
        prompt = self._build_prompt(description, schema_info)
        
        try:
            response = self._call_gemini_api(prompt)
            
            if response.get("candidates"):
                generated_text = response["candidates"][0]["content"]["parts"][0]["text"]
                sql_query = self._extract_sql_from_response(generated_text)
                
                return {
                    "success": True,
                    "query": sql_query,
                    "raw_response": generated_text,
                    "description": description
                }
            else:
                return {
                    "success": False,
                    "error": "No response from Gemini API",
                    "query": None
                }
                
        except Exception as e:
            logger.error(f"Error calling Gemini API: {str(e)}")
            return {
                "success": False,
                "error": f"API call failed: {str(e)}",
                "query": None
            }
    
    def _build_prompt(self, description: str, schema_info: Optional[str] = None) -> str:
        """Build the prompt for Gemini API."""
        # Use provided schema_info, or fall back to configured schema context
        schema_context = schema_info or self.schema_context
        
        base_prompt = f"""You are a SQL expert working with a patent application database. 

{schema_context if schema_context else ""}

Generate a SQL query for this request: {description}

Instructions:
- Use the exact table and column names from the schema above
- ALWAYS use dedicated entity tables when querying specific entities:
  * For examiner queries: Use the 'examiner' table, NOT application.examiner_name
    - Examiner names are in format "Last, First Middle" - use appropriate string functions
  * For attorney queries: Use the 'attorney' table
  * For inventor queries: Use the 'inventor' table
  * For applicant queries: Use the 'applicant' table
- Return only valid PostgreSQL syntax WITHOUT any comments or explanations
- Use ILIKE for case-insensitive string comparisons instead of LIKE or =
- Use LOWER() or UPPER() functions for case-insensitive string operations
- Use appropriate JOINs when accessing related data
- Consider using materialized views (app_m_view, att_firm_m_view) for complex queries
- For date ranges, use proper date formatting
- If the request involves analytics, consider using GROUP BY and aggregations

SQL Query:"""
        
        return base_prompt
    
    def _call_gemini_api(self, prompt: str) -> Dict[str, Any]:
        """Make API call to Gemini."""
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 1000,
            }
        }
        
        response = requests.post(self.base_url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        return response.json()
    
    def _extract_sql_from_response(self, response_text: str) -> str:
        """Extract SQL query from Gemini response."""
        # Simple extraction - look for SQL blocks or just return the response
        lines = response_text.strip().split('\n')
        
        # Remove markdown code blocks if present
        if lines[0].startswith('```'):
            lines = lines[1:]
        if lines[-1].startswith('```'):
            lines = lines[:-1]
            
        return '\n'.join(lines).strip()