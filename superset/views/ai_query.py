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
from typing import Any

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
        payload = {}
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
        """Execute SQL query using SqlLab's infrastructure."""
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
            
            if not sql or not database_id:
                return jsonify({
                    "success": False,
                    "error": "Missing required fields: sql and database_id",
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
            
            # Now let's try the real SqlLab execution
            try:
                schema = ExecutePayloadSchema()
                payload = schema.load(request_data)
                logger.info(f"Schema validation passed: {payload}")
                
                # Create execution context
                execution_context = SqlJsonExecutionContext(payload)
                logger.info(f"Execution context created successfully")
                
                # Create query DAO
                query_dao = QueryDAO()
                
                # Create SQL JSON executor
                if execution_context.is_run_asynchronous():
                    sql_json_executor = ASynchronousSqlJsonExecutor(query_dao, get_sql_results)
                else:
                    sql_json_executor = SynchronousSqlJsonExecutor(
                        query_dao,
                        get_sql_results,
                        getattr(config, "SQLLAB_TIMEOUT", 60),
                        is_feature_enabled("SQLLAB_BACKEND_PERSISTENCE"),
                    )
                logger.info(f"SQL executor created successfully")
                
                # Create execution context convertor
                execution_context_convertor = ExecutionContextConvertor()
                execution_context_convertor.set_max_row_in_display(
                    int(getattr(config, "DISPLAY_MAX_ROW", 10000))
                )
                
                # Create and run the command
                command = ExecuteSqlCommand(
                    execution_context,
                    query_dao,
                    DatabaseDAO(),
                    CanAccessQueryValidatorImpl(),
                    SqlQueryRenderImpl(get_template_processor),
                    sql_json_executor,
                    execution_context_convertor,
                    getattr(config, "SQLLAB_CTAS_NO_LIMIT", True),
                    None,  # log_params
                )
                logger.info(f"Command created, about to execute")
                
                # Execute the command
                command_result = command.run()
                logger.info(f"Command executed successfully: {type(command_result)}")
                
                # Use the same response format as SqlLab
                response_status = (
                    202
                    if command_result["status"] == SqlJsonExecutionStatus.QUERY_IS_RUNNING
                    else 200
                )
                
                # Return using json_success like SqlLab does
                return json_success(command_result["payload"], response_status)
                
            except Exception as sqllab_error:
                logger.error(f"SqlLab execution failed: {str(sqllab_error)}", exc_info=True)
                # Fall back to mock response for now
                return jsonify({
                    "success": False,
                    "error": f"SQL execution failed: {str(sqllab_error)}",
                    "fallback_data": [{"test": "fallback", "sql": sql[:50]}],
                    "columns": [{"name": "test"}, {"name": "sql"}]
                })
            
        except Exception as e:
            logger.error(f"AI Query execute error: {str(e)}", exc_info=True)
            return jsonify({
                "success": False,
                "error": f"Execution failed: {str(e)}",
                "query": None
            }), 500