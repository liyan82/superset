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
import time
from typing import Any, Optional

from flask import request, jsonify
from flask_appbuilder import permission_name
from flask_appbuilder.api import expose
from flask_appbuilder.security.decorators import has_access
from marshmallow import ValidationError

from superset import event_logger, db
from superset.commands.sql_lab.execute import ExecuteSqlCommand
from superset.constants import MODEL_API_RW_METHOD_PERMISSION_MAP
from superset.daos.database import DatabaseDAO
from superset.daos.query import QueryDAO
from superset.sqllab.execution_context_convertor import ExecutionContextConvertor
from superset.sqllab.query_render import SqlQueryRenderImpl
from superset.sqllab.schemas import ExecutePayloadSchema
from superset.sqllab.sql_json_executer import SynchronousSqlJsonExecutor, ASynchronousSqlJsonExecutor
from superset.sqllab.sqllab_execution_context import SqlJsonExecutionContext
from superset.sqllab.command_status import SqlJsonExecutionStatus
from superset.sqllab.validators import CanAccessQueryValidatorImpl
from superset.sql_lab import get_sql_results
from superset import is_feature_enabled
from superset.superset_typing import FlaskResponse
from superset.utils import json
from superset.views.error_handling import handle_api_exception
from superset.jinja_context import get_template_processor
from superset.views.base import json_success
from superset import config

from .base import BaseSupersetView

logger = logging.getLogger(__name__)


class AIQueryView(BaseSupersetView):
    route_base = "/ai-query"
    class_permission_name = "AIQuery"

    method_permission_name = MODEL_API_RW_METHOD_PERMISSION_MAP

    @expose("/", methods=["GET"])
    @has_access
    @permission_name("read")
    @event_logger.log_this
    def root(self, **kwargs: Any) -> FlaskResponse:
        """Handles the default AI Query page."""
        payload = {
            "ai_query_database_id": self._get_ai_query_database_id()
        }
        return self.render_app_template(payload)

    @expose("/generate", methods=["POST"])
    @has_access
    @permission_name("read")
    @event_logger.log_this
    def generate_query(self, **kwargs: Any) -> FlaskResponse:
        """Generate SQL query from natural language description."""
        from superset.ai_query.gemini_service import GeminiService
        from datetime import datetime
        
        data = request.get_json()
        description = data.get("description", "") if data else ""
        
        if not description.strip():
            return jsonify({
                "success": False,
                "error": "Description is required",
                "query": None
            })
        
        # Initialize Gemini service
        gemini_service = GeminiService()
        
        # Debug: Check if API key is available
        if not gemini_service.api_key:
            return jsonify({
                "success": False,
                "error": "Gemini API key not configured. Please set GEMINI_API_KEY in superset_config_docker.py or environment variable.",
                "query": None,
                "debug_info": {
                    "config_has_key": hasattr(request, 'current_app') and 'GEMINI_API_KEY' in request.current_app.config,
                    "env_has_key": bool(os.getenv("GEMINI_API_KEY"))
                }
            })
        
        # Generate SQL query using Gemini
        result = gemini_service.generate_sql_query(description)
        
        # Add timestamp to response
        result["timestamp"] = datetime.now().isoformat()
        result["description"] = description
        
        return jsonify(result)

    @expose("/execute", methods=["POST"])
    @has_access
    @permission_name("read")
    @event_logger.log_this
    def execute_sql(self, **kwargs: Any) -> FlaskResponse:
        """Execute SQL query using SqlLab's infrastructure with smart pagination."""
        try:
            # Parse and validate request data
            request_data = request.get_json()
            logger.info(f"AI Query execute request: {request_data}")
            
            # Simple validation first
            if not request_data:
                return jsonify({
                    "success": False,
                    "error": "No request data provided",
                    "query": None
                }), 400
                
            sql = request_data.get("sql")
            database_id = request_data.get("database_id")
            page = request_data.get("page", 1)
            page_size = request_data.get("page_size", 50)
            
            if not sql or not database_id:
                return jsonify({
                    "success": False,
                    "error": "Missing required fields: sql and database_id",
                    "query": None
                }), 400
                
            # Validate pagination parameters
            try:
                page = max(1, int(page))
                page_size = max(1, min(int(page_size), 100))  # Cap at 100 per page
            except (ValueError, TypeError):
                return jsonify({
                    "success": False,
                    "error": "Invalid pagination parameters",
                    "query": None
                }), 400
            
            # Check if database exists
            from superset.models.core import Database
            database = db.session.query(Database).filter_by(id=database_id).first()
            if not database:
                # Get list of available databases for debugging
                available_dbs = db.session.query(Database.id, Database.database_name).all()
                return jsonify({
                    "success": False,
                    "error": f"Database with id {database_id} not found. Available databases: {available_dbs}",
                    "query": None
                }), 400
            
            # Smart pagination: check result count first
            PAGINATION_THRESHOLD = 500
            total_count = self._get_query_count(sql, database_id)
            
            if total_count is None:
                return jsonify({
                    "success": False,
                    "error": "Failed to determine result count",
                    "query": None
                }), 500
            
            # Use direct SQL execution for all queries to avoid session management issues
            # This bypasses SqlLab's complex infrastructure which has user session dependencies
            try:
                # Determine if we need server-side pagination
                use_server_pagination = total_count > PAGINATION_THRESHOLD
                
                if use_server_pagination:
                    # Modify SQL with LIMIT and OFFSET for server-side pagination
                    paginated_sql = self._add_pagination_to_sql(sql, page, page_size)
                    sql_to_execute = paginated_sql
                else:
                    # Use original SQL for small result sets
                    sql_to_execute = sql
                
                # Execute SQL directly against the database
                payload = self._execute_sql_direct(database_id, sql_to_execute, page, page_size, total_count)
                
                # For client-side pagination, modify the pagination metadata
                if not use_server_pagination:
                    data_count = len(payload.get("data", []))
                    payload["pagination"] = {
                        "page": 1,
                        "page_size": data_count,
                        "total_count": total_count,
                        "total_pages": 1,
                        "has_next": False,
                        "has_prev": False,
                        "server_side": False
                    }
                
                logger.info(f"Final payload structure: {type(payload)}, keys: {list(payload.keys()) if isinstance(payload, dict) else 'not dict'}")
                
                # Return the payload as JSON directly since json_success might be causing formatting issues
                return jsonify(payload)
                
            except Exception as execution_error:
                logger.error(f"Direct SQL execution failed: {str(execution_error)}", exc_info=True)
                return jsonify({
                    "success": False,
                    "error": f"SQL execution failed: {str(execution_error)}",
                    "query": None
                }), 500
            
        except Exception as e:
            logger.error(f"AI Query execute error: {str(e)}", exc_info=True)
            return jsonify({
                "success": False,
                "error": f"Execution failed: {str(e)}",
                "query": None
            }), 500

    @expose("/config", methods=["GET"])
    @has_access
    @permission_name("read")
    @event_logger.log_this
    def get_config(self, **kwargs: Any) -> FlaskResponse:
        """Get AI Query configuration including database ID."""
        try:
            database_id = self._get_ai_query_database_id()
            if not database_id:
                return jsonify({
                    "success": False,
                    "error": "No suitable database found for AI Query"
                }), 404
                
            return jsonify({
                "success": True,
                "database_id": database_id,
                "database_name": self._get_database_name(database_id)
            })
        except Exception as e:
            logger.error(f"AI Query config error: {str(e)}", exc_info=True)
            return jsonify({
                "success": False,
                "error": f"Configuration error: {str(e)}"
            }), 500

    def _get_ai_query_database_id(self) -> Optional[int]:
        """
        Get the database ID for AI Query.
        Tries multiple approaches to find the appropriate database.
        """
        from superset.models.core import Database
        
        # Approach 1: Check configuration
        configured_db_id = getattr(config, "AI_QUERY_DATABASE_ID", None)
        if configured_db_id:
            # Verify the database exists
            database = db.session.query(Database).filter_by(id=configured_db_id).first()
            if database:
                return configured_db_id
            else:
                logger.warning(f"Configured AI_QUERY_DATABASE_ID {configured_db_id} not found")
        
        # Approach 2: Look for USPTO database by name
        uspto_db = db.session.query(Database).filter(
            Database.database_name.ilike('%uspto%')
        ).first()
        if uspto_db:
            return uspto_db.id
            
        # Approach 3: Look for patent-related database names
        patent_keywords = ['patent', 'intellectual', 'ip', 'trademark']
        for keyword in patent_keywords:
            patent_db = db.session.query(Database).filter(
                Database.database_name.ilike(f'%{keyword}%')
            ).first()
            if patent_db:
                return patent_db.id
        
        # Approach 4: Use the first available database as fallback
        fallback_db = db.session.query(Database).first()
        if fallback_db:
            logger.warning(f"Using fallback database: {fallback_db.database_name} (id: {fallback_db.id})")
            return fallback_db.id
            
        return None

    def _get_database_name(self, database_id: int) -> Optional[str]:
        """Get database name by ID."""
        from superset.models.core import Database
        database = db.session.query(Database).filter_by(id=database_id).first()
        return database.database_name if database else None

    def _get_query_count(self, sql: str, database_id: int) -> Optional[int]:
        """
        Get the total count of records that would be returned by the query.
        Converts SELECT query to COUNT query to determine result size.
        """
        try:
            # Convert SELECT query to COUNT query
            count_sql = self._convert_to_count_query(sql)
            
            # Execute count query using SqlLab infrastructure
            count_request = {
                "database_id": database_id,
                "sql": count_sql,
                "queryLimit": 1,
                "client_id": f"cnt_{int(time.time()) % 10000000}",  # Keep it under 11 chars
                "expand_data": True,
            }
            
            # Execute count query
            from superset.sqllab.execution_context_convertor import ExecutionContextConvertor
            from superset.sqllab.query_render import SqlQueryRenderImpl
            from superset.sqllab.sqllab_execution_context import SqlJsonExecutionContext
            from superset.sqllab.schemas import ExecutePayloadSchema
            from superset.commands.sql_lab.execute import ExecuteSqlCommand
            from superset.daos.database import DatabaseDAO
            from superset.daos.query import QueryDAO
            from superset.sqllab.validators import CanAccessQueryValidatorImpl
            from superset.sqllab.sql_json_executer import SynchronousSqlJsonExecutor
            from superset.sql_lab import get_sql_results
            from superset.jinja_context import get_template_processor
            
            schema = ExecutePayloadSchema()
            payload = schema.load(count_request)
            
            execution_context = SqlJsonExecutionContext(payload)
            query_dao = QueryDAO()
            
            sql_json_executor = SynchronousSqlJsonExecutor(
                query_dao,
                get_sql_results,
                getattr(config, "SQLLAB_TIMEOUT", 60),
                is_feature_enabled("SQLLAB_BACKEND_PERSISTENCE"),
            )
            
            execution_context_convertor = ExecutionContextConvertor()
            execution_context_convertor.set_max_row_in_display(
                int(getattr(config, "DISPLAY_MAX_ROW", 10000))
            )
            
            command = ExecuteSqlCommand(
                execution_context,
                query_dao,
                DatabaseDAO(),
                CanAccessQueryValidatorImpl(),
                SqlQueryRenderImpl(get_template_processor),
                sql_json_executor,
                execution_context_convertor,
                getattr(config, "SQLLAB_CTAS_NO_LIMIT", True),
                None,
            )
            
            result = command.run()
            logger.info(f"Count query result type: {type(result)}, content: {result}")
            
            if result and isinstance(result, dict):
                payload = result.get("payload")
                if payload:
                    # Handle case where payload might be a string (JSON) or dict
                    if isinstance(payload, str):
                        try:
                            import json
                            payload = json.loads(payload)
                        except (json.JSONDecodeError, ValueError):
                            logger.error(f"Failed to parse payload JSON: {payload}")
                            return None
                    
                    if isinstance(payload, dict) and payload.get("data"):
                        count_data = payload["data"]
                        if count_data and len(count_data) > 0:
                            # Extract count from first row, first column
                            count_value = list(count_data[0].values())[0]
                            return int(count_value)
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to get query count: {str(e)}", exc_info=True)
            return None

    def _convert_to_count_query(self, sql: str) -> str:
        """
        Convert a SELECT query to a COUNT query.
        Handles various SQL formats safely.
        """
        sql = sql.strip()
        
        # Remove trailing semicolon if present (causes parsing issues in subqueries)
        if sql.endswith(';'):
            sql = sql[:-1]
        
        # Simple approach: wrap the original query in a COUNT subquery
        # This is safer than trying to parse and modify complex SQL
        count_sql = f"SELECT COUNT(*) as total_count FROM ({sql}) AS count_subquery"
        
        return count_sql

    def _add_pagination_to_sql(self, sql: str, page: int, page_size: int) -> str:
        """
        Add LIMIT and OFFSET clauses to SQL query for server-side pagination.
        Safely appends pagination without breaking existing query structure.
        """
        sql = sql.strip()
        
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Remove trailing semicolon if present
        if sql.endswith(';'):
            sql = sql[:-1]
        
        # Add LIMIT and OFFSET
        paginated_sql = f"{sql} LIMIT {page_size} OFFSET {offset}"
        
        return paginated_sql

    def _execute_sql_direct(self, database_id: int, sql: str, page: int, page_size: int, total_count: int) -> dict:
        """
        Execute SQL query directly against the database for server-side pagination.
        This bypasses the complex SqlLab infrastructure to avoid session issues.
        """
        try:
            # Get database engine directly - handle context manager
            from sqlalchemy import text
            from superset.models.core import Database
            
            # Get a fresh database object from the current session using the database_id
            database = db.session.query(Database).filter_by(id=database_id).first()
            if not database:
                raise Exception(f"Database with id {database_id} not found")
            
            # database.get_sqla_engine() returns a context manager
            with database.get_sqla_engine() as engine:
                with engine.connect() as connection:
                    result = connection.execute(text(sql))
                    
                    # Get column names
                    column_names = list(result.keys())
                    columns = [{"column_name": col, "name": col, "type": "STRING", "is_dttm": False} for col in column_names]
                    
                    # Fetch all rows for this page
                    rows = result.fetchall()
                    
                    # Convert rows to list of dictionaries
                    data = []
                    for row in rows:
                        row_dict = {}
                        for i, col_name in enumerate(column_names):
                            # Ensure JSON serializable values
                            value = row[i]
                            if value is None:
                                row_dict[col_name] = None
                            else:
                                # Convert to string to ensure JSON serialization works
                                row_dict[col_name] = str(value)
                        data.append(row_dict)
            
            # Calculate pagination info (outside the connection context)
            total_pages = (total_count + page_size - 1) // page_size
            
            # Build response payload in SqlLab format - match the expected frontend structure
            payload = {
                "query_id": None,
                "status": "success",
                "data": data,
                "columns": columns,
                "selected_columns": columns,
                "expanded_columns": columns,
                "query": {
                    "sql": sql,
                    "executed_sql": sql
                },
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1,
                    "server_side": True
                }
            }
            
            logger.info(f"Direct SQL execution successful: {len(data)} rows returned")
            
            # Return in the same format as json_success - just the payload, not wrapped
            return payload
                
        except Exception as e:
            logger.error(f"Direct SQL execution error: {str(e)}", exc_info=True)
            raise e