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
import os
from typing import Any

from flask import request, jsonify
from flask_appbuilder import permission_name
from flask_appbuilder.api import expose
from flask_appbuilder.security.decorators import has_access

from superset import event_logger
from superset.constants import MODEL_API_RW_METHOD_PERMISSION_MAP
from superset.superset_typing import FlaskResponse

from .base import BaseSupersetView


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