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
import re
import uuid
from typing import Any, Dict, Optional

import google.generativeai as genai
from google.generativeai.types import HarmBlockThreshold, HarmCategory

logger = logging.getLogger(__name__)


class GeminiService:
    """
    Service for interacting with Google Gemini AI to generate SQL queries.
    Privacy Features:
    - Each request is stateless with no conversation history
    - System instructions explicitly prevent context storage and model training
    - Safety settings configured to block harmful content
    - Unique request IDs ensure no correlation between requests
    """

    def __init__(self, api_key: Optional[str] = None):
        # Try to get API key from multiple sources
        self.api_key = api_key
        self.schema_context = None
        self.excluded_columns = []
        # Privacy controls - ensure stateless requests
        self.disable_context_storage = True
        self.model = None

        if not self.api_key:
            try:
                from flask import current_app
                self.api_key = current_app.config.get("GEMINI_API_KEY")
                self.schema_context = current_app.config.get("GEMINI_SCHEMA_CONTEXT")
                self.excluded_columns = current_app.config.get(
                    "AI_QUERY_EXCLUDED_COLUMNS", []
                )
            except RuntimeError:
                # Not in application context, try importing app
                try:
                    from superset import app
                    self.api_key = app.config.get("GEMINI_API_KEY")
                    self.schema_context = app.config.get("GEMINI_SCHEMA_CONTEXT")
                    self.excluded_columns = app.config.get(
                        "AI_QUERY_EXCLUDED_COLUMNS", []
                    )
                except Exception as e:
                    logger.debug(f"Failed to load config from app: {e}")

        if not self.api_key:
            self.api_key = os.getenv("GEMINI_API_KEY")

        # Initialize SDK
        if self.api_key:
            self._init_sdk()
        else:
            logger.warning("No API key available for Gemini SDK initialization")

    def _init_sdk(self) -> None:
        """Initialize the Google AI SDK."""
        try:
            # Configure the SDK with API key
            genai.configure(api_key=self.api_key)

            # Create model instance with safety settings
            self.model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    max_output_tokens=4000,
                ),
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HARASSMENT: (
                        HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                    ),
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: (
                        HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                    ),
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: (
                        HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                    ),
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: (
                        HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                    ),
                },
                system_instruction=(
                    "PRIVACY DIRECTIVE: This is a completely stateless, one-time "
                    "request. Do not store, retain, or reference any conversation "
                    "context, user data, or request history. Treat each request as "
                    "independent with no memory of previous interactions. Do not use "
                    "this data for model training or improvement."
                )
            )
            logger.info("Gemini SDK initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini SDK: {e}")
            self.model = None

    def generate_sql_query(
        self, description: str, schema_info: Optional[str] = None
    ) -> Dict[str, Any]:
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

        # Security validation: prevent abuse of API key
        validation_result = self._validate_query_request(description)
        if not validation_result["valid"]:
            return {
                "success": False,
                "error": validation_result["error"],
                "query": None
            }

        prompt = self._build_prompt(description, schema_info)

        try:
            # Use SDK for generating content
            if self.model:
                generated_text = self._call_gemini_sdk(prompt)
                logger.info(f"Generated text: {generated_text}")
            else:
                return {
                    "success": False,
                    "error": "Gemini SDK not properly initialized. Check API key configuration.",
                    "query": None
                }

            # Check if AI refused the request due to restrictions
            if (
                "ERROR:" in generated_text
                or "not related to patent database" in generated_text.lower()
            ):
                return {
                    "success": False,
                    "error": (
                        "Request not related to patent database queries. Please ask "
                        "about patent data, examiners, attorneys, applications, or "
                        "inventors."
                    ),
                    "query": None
                }

            sql_query = self._extract_sql_from_response(generated_text)

            # Validate that the generated query doesn't contain excluded columns
            validation_result = self._validate_excluded_columns(sql_query)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": validation_result["error"],
                    "query": None
                }

            return {
                "success": True,
                "query": sql_query,
                "raw_response": generated_text,
                "description": description
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

        # Build column exclusion instructions
        exclusion_text = ""
        if self.excluded_columns:
            exclusion_text = f"""
COLUMN EXCLUSION POLICY:
- NEVER select or include these columns in any query: {', '.join(self.excluded_columns)}
- These columns contain sensitive, internal, or irrelevant data that should not be exposed to end users
- If a user request would require these columns, either omit them or suggest alternative columns
- Always prioritize user privacy and data security
"""

        base_prompt = f"""You are a specialized SQL generator for a patent application database. You ONLY generate SQL queries for database-related requests.

IMPORTANT RESTRICTIONS:
- ONLY respond to database query requests about patent data
- If the request is not about querying patent database data, respond with: "ERROR: Request not related to patent database queries"
- Do NOT provide general AI assistance, explanations, or answers to non-database questions
- Do NOT respond to requests for stories, essays, translations, or general information

DATABASE SCHEMA:
{schema_context if schema_context else ""}
{exclusion_text}
USER REQUEST: {description}

SQL GENERATION RULES:
- Use exact table and column names from schema above
- ALWAYS use dedicated entity tables:
  * examiner table (names: "Last, First Middle" format)
  * attorney table 
  * inventor table
  * applicant table
- Return ONLY valid PostgreSQL syntax without comments

STRING MATCHING RULES:
- For EXACT WORD matches, use word boundary patterns:
  * For single words: column_name ~* '\\y[search_term]\\y' or column_name ~* '\\b[search_term]\\b'
  * For space-separated words: column_name ILIKE '% [search_term] %' OR column_name ILIKE '[search_term] %' OR column_name ILIKE '% [search_term]'
  * For start/end of field: column_name ILIKE '[search_term]%' or column_name ILIKE '%[search_term]'
- For PARTIAL matches only when explicitly requested: column_name ILIKE '%[search_term]%'
- Use ILIKE for case-insensitive comparisons (preferred over LIKE)
- Use LOWER() or UPPER() functions for case-insensitive string operations when regex not available
- When searching names, consider both "Last, First" and "First Last" formats

QUERY STRUCTURE RULES:
- Use appropriate JOINs when accessing related data
- Consider using materialized views (app_m_view, att_firm_m_view) for complex queries
- For date ranges, use proper date formatting
- If the request involves analytics, consider using GROUP BY and aggregations
- STRICTLY AVOID selecting any excluded columns listed above

MATCHING EXAMPLES:
- User says "find Smith": Use word boundaries → examiner_name ~* '\\ySmith\\y'
- User says "companies with Tech": Use space patterns → company_name ILIKE '% Tech %' OR company_name ILIKE 'Tech %' OR company_name ILIKE '% Tech'
- User says "starts with Bio": Use prefix → company_name ILIKE 'Bio%'
- User says "contains partial word": Use full wildcard → company_name ILIKE '%search%'

RESPONSE FORMAT:
Return only the SQL query, no explanations or additional text.

SQL Query:"""

        return base_prompt

    def _generate_request_id(self) -> str:
        """Generate a unique request ID to ensure no correlation between requests."""
        return str(uuid.uuid4())

    def _call_gemini_sdk(self, prompt: str) -> str:
        """
        Call Gemini using the official SDK.

        Args:
            prompt: The prompt to send to Gemini

        Returns:
            Generated text response

        Raises:
            Exception: If the API call fails
        """
        if not self.model:
            raise Exception("Gemini SDK not initialized")

        try:
            # Generate response using SDK
            response = self.model.generate_content(prompt)

            # Extract text from response
            if response.text:
                return response.text
            else:
                # Handle cases where response is blocked
                if response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, "finish_reason"):
                        if candidate.finish_reason.name == "SAFETY":
                            raise Exception("Response blocked by safety filters")
                        elif candidate.finish_reason.name == "RECITATION":
                            raise Exception(
                                "Response blocked due to recitation concerns"
                            )
                        else:
                            raise Exception(
                                f"Response generation stopped: "
                                f"{candidate.finish_reason.name}"
                            )

                raise Exception("No text generated in response")

        except Exception as e:
            logger.error(f"SDK API call failed: {str(e)}")
            raise


    def _extract_sql_from_response(self, response_text: str) -> str:
        """Extract SQL query from Gemini response."""
        # Simple extraction - look for SQL blocks or just return the response
        lines = response_text.strip().split("\n")

        # Remove markdown code blocks if present
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines[-1].startswith("```"):
            lines = lines[:-1]

        return "\n".join(lines).strip()

    def _validate_query_request(self, description: str) -> Dict[str, Any]:
        """
        Validate the user input to prevent API abuse.

        Args:
            description: User's natural language description

        Returns:
            Dict with validation result and error message if invalid
        """
        # Check for empty input
        if not description or not description.strip():
            return {
                "valid": False,
                "error": "Query description cannot be empty"
            }

        # Length restrictions to prevent abuse
        description = description.strip()
        max_length = 800  # Reasonable limit for database queries
        min_length = 10    # Too short is likely not a real query

        if len(description) > max_length:
            return {
                "valid": False,
                "error": (
                    f"Query description too long (max {max_length} characters). "
                    "Please keep your question concise."
                )
            }

        if len(description) < min_length:
            return {
                "valid": False,
                "error": (
                    f"Query description too short (min {min_length} characters). "
                    "Please provide more details."
                )
            }

        # Content validation: must be database/query related
        database_keywords = [
            # Query intentions
            "find", "show", "list", "get", "select", "search", "display", "retrieve",
            "count", "sum", "total", "average", "min", "max", "group", "filter",
            # Database entities from our schema
            "examiner", "attorney", "patent", "application", "inventor", "applicant",
            "firm", "classification", "cpc", "uspc", "database", "table", "record",
            # Common query words
            "where", "with", "having", "by", "from", "in", "all", "any", "some",
            "name", "id", "date", "year", "status", "type", "number",
            # Question words
            "what", "which", "who", "when", "where", "how", "many", "much"
        ]

        # Convert to lowercase for case-insensitive checking
        description_lower = description.lower()

        # Check if description contains database/query related keywords
        has_database_keywords = any(
            keyword in description_lower for keyword in database_keywords
        )

        if not has_database_keywords:
            return {
                "valid": False,
                "error": (
                    "This appears to be a general question rather than a "
                    "database query. "
                    "Please ask about patent data, examiners, attorneys, "
                    "applications, or inventors."
                )
            }

        # Check for suspicious patterns that might indicate abuse
        suspicious_patterns = [
            # Non-query requests
            "write", "create", "generate", "make", "build", "develop", "code",
            "story", "essay", "article", "letter", "email", "report", "summary",
            "translate", "explain", "describe", "tell me about", "what is",
            # Attempts to bypass restrictions
            "ignore", "forget", "override", "bypass", "system", "prompt", "instruction",
            "pretend", "roleplay", "act as", "imagine",
            # Non-database domains
            "weather", "news", "stock", "recipe", "joke", "poem", "song"
        ]

        # Check for suspicious patterns
        for pattern in suspicious_patterns:
            if pattern in description_lower:
                return {
                    "valid": False,
                    "error": (
                    "Please ask questions specifically about the patent database. "
                    "General AI assistance is not available through this interface."
                )
                }

        return {
            "valid": True,
            "error": None
        }

    def _validate_excluded_columns(self, sql_query: str) -> Dict[str, Any]:
        """
        Validate that the generated SQL query doesn't contain any excluded columns.

        Args:
            sql_query: The SQL query to validate

        Returns:
            Dict with validation result and error message if invalid
        """
        if not self.excluded_columns:
            # No excluded columns configured, so validation passes
            return {
                "valid": True,
                "error": None
            }

        # Convert query to lowercase for case-insensitive checking
        sql_lower = sql_query.lower()

        # Check for excluded columns in the query
        found_excluded = []
        for column in self.excluded_columns:
            column_lower = column.lower()

            # Use word boundary patterns to match exact column names only
            # This prevents partial matches (e.g., 'eth' matching when
            # 'eth_prob' is excluded)

            # Pattern matches:
            # - column names after SELECT, comma, or whitespace
            # - table.column references
            # - quoted column names
            # - column names followed by word boundaries (space, comma, FROM, etc.)
            patterns = [
                rf"\bselect\s+.*?\b{re.escape(column_lower)}\b",  # SELECT ... column
                rf"\b{re.escape(column_lower)}\s*,",  # column,
                rf",\s*{re.escape(column_lower)}\b",  # , column
                rf"\.\s*{re.escape(column_lower)}\b",  # table.column
                rf"`{re.escape(column_lower)}`",  # `column`
                rf'"{re.escape(column_lower)}"',  # "column"
                rf"'{re.escape(column_lower)}'",  # 'column'
                rf"\b{re.escape(column_lower)}\s+(?:from|where|group|order|having)",
                # column FROM/WHERE/etc
            ]

            # Check if any pattern matches
            for pattern in patterns:
                if re.search(pattern, sql_lower, re.IGNORECASE):
                    found_excluded.append(column)
                    break

        if found_excluded:
            return {
                "valid": False,
                "error": (
                    f"Generated query contains excluded columns that cannot be "
                    f"exposed: {', '.join(found_excluded)}. Please rephrase your "
                    "request to avoid sensitive data."
                )
            }

        return {
            "valid": True,
            "error": None
        }

