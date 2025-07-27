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
        
        if not self.api_key:
            try:
                from flask import current_app
                self.api_key = current_app.config.get("GEMINI_API_KEY")
            except RuntimeError:
                # Not in application context, try importing app
                try:
                    from superset import app
                    self.api_key = app.config.get("GEMINI_API_KEY")
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
        base_prompt = f"""
Generate a SQL query based on this description: {description}

Instructions:
- Return only valid SQL syntax
- Use standard SQL that works with most databases
- Include comments to explain the query logic
- If the request is unclear, make reasonable assumptions

"""
        
        if schema_info:
            base_prompt += f"""
Database Schema Context:
{schema_info}

"""
        
        base_prompt += "SQL Query:"
        
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