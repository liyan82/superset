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
#
# This file is included in the final Docker image and SHOULD be overridden when
# deploying the image to prod. Settings configured here are intended for use in local
# development environments. Also note that superset_config_docker.py is imported
# as a final step as a means to override "defaults" configured here
#
import logging
import os
import sys
from datetime import timedelta
from celery.schedules import crontab
from cachelib.file import FileSystemCache
from flask_caching.backends.base import BaseCache

logger = logging.getLogger()

APP_NAME = "Patent 1024"

# Specify the App icon
APP_ICON = "/static/assets/images/patent-1024.png"

FAVICONS = [{"href": "/static/assets/images/p4-favicon.png"}]

# Enable user registration
AUTH_USER_REGISTRATION = True
AUTH_USER_REGISTRATION_ROLE = "Trial"
TRIAL_PERIOD_DAYS = 7
TRIAL_EXPIRED_ROLE = "Public"

# Feature flag for restricting registration to non-public email domains
ENABLE_REGISTRATION_EMAIL_DOMAIN_VALIDATION = True

# List of public email domains to blacklist for registration
REGISTRATION_EMAIL_DOMAIN_BLACKLIST = {
    "gmail.com",
    "yahoo.com",
    "hotmail.com",
    "aol.com",
    "outlook.com",
    "icloud.com",
    "live.com",
    "msn.com",
    # "duck.com",
    "protonmail.com",
}

SECRET_KEY = os.getenv("SECRET_KEY")

DATABASE_DIALECT = os.getenv("DATABASE_DIALECT")
DATABASE_USER = os.getenv("DATABASE_USER")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
DATABASE_HOST = os.getenv("DATABASE_HOST")
DATABASE_PORT = os.getenv("DATABASE_PORT")
DATABASE_DB = os.getenv("DATABASE_DB")

EXAMPLES_USER = os.getenv("EXAMPLES_USER")
EXAMPLES_PASSWORD = os.getenv("EXAMPLES_PASSWORD")
EXAMPLES_HOST = os.getenv("EXAMPLES_HOST")
EXAMPLES_PORT = os.getenv("EXAMPLES_PORT")
EXAMPLES_DB = os.getenv("EXAMPLES_DB")

# The SQLAlchemy connection string.
SQLALCHEMY_DATABASE_URI = (
    f"{DATABASE_DIALECT}://"
    f"{DATABASE_USER}:{DATABASE_PASSWORD}@"
    f"{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_DB}"
)

SQLALCHEMY_EXAMPLES_URI = (
    f"{DATABASE_DIALECT}://"
    f"{EXAMPLES_USER}:{EXAMPLES_PASSWORD}@"
    f"{EXAMPLES_HOST}:{EXAMPLES_PORT}/{EXAMPLES_DB}"
)

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_CELERY_DB = os.getenv("REDIS_CELERY_DB", "0")
REDIS_RESULTS_DB = os.getenv("REDIS_RESULTS_DB", "1")

RESULTS_BACKEND = FileSystemCache("/app/superset_home/sqllab")

CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX": "superset_",
    "CACHE_REDIS_HOST": REDIS_HOST,
    "CACHE_REDIS_PORT": REDIS_PORT,
    "CACHE_REDIS_DB": REDIS_RESULTS_DB,
}
DATA_CACHE_CONFIG = CACHE_CONFIG
THUMBNAIL_CACHE_CONFIG = CACHE_CONFIG


class CeleryConfig:
    broker_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_CELERY_DB}"
    imports = (
        "superset.sql_lab",
        "superset.tasks.scheduler",
        "superset.tasks.thumbnails",
        "superset.tasks.cache",
        "superset.tasks.expired_subscriptions",
        # "superset.tasks.sync_stripe",
    )
    result_backend = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_RESULTS_DB}"
    worker_prefetch_multiplier = 1
    task_acks_late = False
    beat_schedule = {
        "reports.scheduler": {
            "task": "reports.scheduler",
            "schedule": crontab(minute="*", hour="*"),
        },
        "reports.prune_log": {
            "task": "reports.prune_log",
            "schedule": crontab(minute=10, hour=0),
        },
        "expired_subscriptions.process_expirations": {
            "task": "expired_subscriptions.process_expirations",
            # "schedule": crontab(minute=0, hour=0),  # daily at midnight
            "schedule": timedelta(seconds=30),
        },
        # "sync_stripe.sync_stripe_data": {
        #     "task": "sync_stripe.sync_stripe_data",
        #     "schedule": timedelta(seconds=20),
        # },
    }


CELERY_CONFIG = CeleryConfig

# A mapping of Stripe product IDs to a list of features for each plan.
# Replace the placeholder keys with your actual Stripe product IDs.
#
# You can find your Stripe product IDs in your Stripe dashboard under
# "Products". They typically look like "prod_...".
SUBSCRIPTION_PLANS_FEATURES = {
    # Starter Plan - Essential Patent Analytics
    "prod_RxmzzUm05pwwlw": [
        "Interactive charts & dashboards",
        "Access curated patent datasets",
        "Export charts & data (PDF/PNG/CSV)",
        "Personal workspace with saved queries",
        "Guided data exploration",
    ],
    # Professional Plan - Advanced Patent Intelligence
    "prod_Rxn4SrqwJRkxTd": [
        "Interactive charts & dashboards",
        "Access curated patent datasets",
        "Export charts & data (PDF/PNG/CSV)",
        "Personal workspace with saved queries",
        "Guided data exploration",
        "Full SQL Lab access w/ cost estimation",
        "Upload & manage custom datasets",
        "Advanced sharing & team collaboration",
        "Row-level security & API access",
        "Automated reports, caching, & CSS templates",
    ],
}

FEATURE_FLAGS = {"ALERT_REPORTS": True}
ALERT_REPORTS_NOTIFICATION_DRY_RUN = True
WEBDRIVER_BASEURL = f"http://superset_app{os.environ.get('SUPERSET_APP_ROOT', '/')}/"  # When using docker compose baseurl should be http://superset_nginx{ENV{BASEPATH}}/  # noqa: E501
# The base URL for the email report hyperlinks.
WEBDRIVER_BASEURL_USER_FRIENDLY = (
    f"http://localhost:8888/{os.environ.get('SUPERSET_APP_ROOT', '/')}/"
)
SQLLAB_CTAS_NO_LIMIT = True

# ===================================================================
# AI Query Configuration
# ===================================================================

# AI Query Database Configuration
# Specify which database to use for AI Query Assistant
# If not set, system will auto-detect USPTO/patent database
# AI_QUERY_DATABASE_ID = 3  # Uncomment and set specific database ID if needed

# Columns that should never be included in AI query results for privacy/security
# These columns will be explicitly excluded from AI-generated SELECT statements
AI_QUERY_EXCLUDED_COLUMNS = [
    # Sensitive personal identifiers
    'ssn', 'social_security_number', 'tax_id', 'passport_number',
    # Internal system fields
    'password', 'password_hash', 'salt', 'token', 'api_key', 'secret',
    # Financial information
    'credit_card', 'bank_account', 'routing_number', 'payment_info',
    # Internal IDs that shouldn't be exposed
    'internal_id', 'system_id', 'uuid', 'guid',
    # Audit/tracking fields that are not user-relevant
    'created_by_system', 'modified_by_system', 'internal_notes',
    # Large binary/text fields that would clutter results
    'full_text_content', 'blob_data', 'binary_content', 'raw_data'
]

# Patent Database Schema for AI Query Generation
GEMINI_SCHEMA_CONTEXT = """
PATENT APPLICATION DATABASE SCHEMA:

=== CORE ENTITY TABLES ===

- application: Main patent applications table (PRIMARY DATA SOURCE)
  * app_num (int, primary) - Application number (unique identifier)
  * filing_date (date) - Application filing date
  * cat (text) - Category. The valid values are: REGULAR (meaning a new application), and REISSUE (meaning a reissue of an existing application)
  * group_art (text) - Art group. The USPTO uses one signle art group number to classify all applications in the same art group. almost all of them are numbers, with several exceptions.. The USPTO uses one signle art group number to classify all applications in the same art group. almost all of them are numbers, with several exceptions.
  * inv_title (text) - Invention title describes what the invention is.
  * app_status (text) - Application status is the status of the application, identifying if the application is pending, granted, or abandoned.
  * status_code (text) - Status code. USPTO uses numbers to identify the status of the application. This is the correpondent number to the app_status.
  * patent_num (text) - Patent number if granted
  * grant_date (date) - Grant date
  * type_code (text) - Application type. The valid values are: DES (design patent), UTL (utility patent), and PLT (meaning plant patent).
  * class_num (text) - Classification number is the standard of Unite States Patent Classification. It is distinguished from CPC classification.
  * examiner_name (text) - Examiner name (denormalized, prefer examiner table)
  * customer_num (int) - Links to customer_add for firm information
  * first_applicant_name, first_inventor_name (text) - Denormalized names

- attorney: Patent attorneys/agents (MASTER ATTORNEY DATA)
  * id (serial, primary)
  * reg_num (int, unique) - Registration number (USE THIS for attorney searches)
  * first_name, middle_name, last_name (text) - Attorney name components
  * practitioner_type (enum) - Attorney or agent
  * active (boolean) - Active status
  * gender (int), eth (text), nat (text) - Demographics
  * org_id (int) - Organization reference

- examiner: Patent examiners (PREFERRED for examiner queries)
  * id (serial, primary)
  * name (text) - Full examiner name in format: "Last, First Middle"
  * gender (int), eth (text), nat (text) - Demographics

- inventor: Patent inventors (MASTER INVENTOR DATA)
  * id (serial, primary)
  * first_name, middle_name, last_name, full_name (text) - Name components
  * gender (int), nat (int), eth (text) - Demographics with probability scores
  * city, country (text) - Geographic location

- applicant: Patent applicants/organizations (MASTER APPLICANT DATA)
  * id (serial, primary)
  * org_name (text) - Organization name (USE THIS for company searches)
  * org_norm (text) - Normalized organization name
  * name_line_1, name_line_2 (text) - Name lines
  * address_line_1, address_line_2 (text) - Address
  * city, state, country, postal_code (text) - Location
  * fingerprint (text, unique) - Unique identifier for linking
  * type (postal_address_type) - Address type

- customer_add: Customer/firm addresses (FIRM INFORMATION)
  * id (serial, primary)
  * customer_num (int, unique) - Customer number (links from application.customer_num)
  * firm_name (text) - Law firm name (USE THIS for firm searches)
  * url (text) - Firm website
  * name_line_1, name_line_2 (text) - Contact names
  * address_line_1, address_line_2 (text) - Address
  * city, state, country, postal_code (text) - Location

=== CRITICAL DISTINCTION: FILING vs REPRESENTATION ===

**IMPORTANT: Choose the correct table based on the question intent:**

1. **For "applications FILED BY attorney X" or "documents filed by attorney X":**
   - USE: doc_attorney table (tracks actual document filing activity)
   - This shows WHO FILED specific documents/applications
   - JOIN: doc_attorney → attorney ON doc_attorney.attorney_num = attorney.reg_num

2. **For "applications WHERE attorney X represents the applicant":**
   - USE: app_attorney table (tracks representation relationships)
   - This shows ongoing attorney-client relationships
   - JOIN: app_attorney → attorney ON app_attorney.att_num = attorney.reg_num

3. **For "applications by firm X" (most common):**
   - USE: application → customer_add JOIN ON application.customer_num = customer_add.customer_num
   - Search by customer_add.firm_name
   - This shows applications where the firm is the customer of record

=== RELATIONSHIP TABLES (Use carefully based on intent) ===

- doc_attorney: FILING ACTIVITY (WHO FILED WHAT)
  * id (serial, primary)
  * app_num (int) - Application number
  * doc_code (text) - Document type code
  * doc_identifier (text) - Unique document identifier
  * doc_date (date) - Filing date
  * attorney_num (int) - Attorney registration number who FILED this document
  * confidence_rate (double) - Data confidence score
  ➤ USE THIS when asking about "filed by" or "submitted by" attorney

- app_attorney: REPRESENTATION RELATIONSHIP (WHO REPRESENTS WHOM: which attorneys are in the Power of Attorney (POA) list. doesn't mean the attorney actually represents the applicant. doc_attorney table is the correct table to use for this.)
  * app_num (int) - Application number
  * att_num (int) - Attorney registration number
  ➤ USE THIS when asking about attorney representation on applications

- app_customer: APPLICATION-CUSTOMER LINKS. Customers are probably the law firms. Some of them are the law departments of the companies that filed the applications.
  * app_num (int) - Application number  
  * customer_num (int) - Customer number
  ➤ Links applications to customers/firms

- app_inventor: APPLICATION-INVENTOR LINKS. Inventors are the people who invented the invention.
  * app_num (int) - Application number
  * inventor_id (int) - Inventor ID
  * add_fingerprint (text) - Address fingerprint
  * add_type (postal_address_type) - Address type

- app_applicant: APPLICATION-APPLICANT LINKS. Applicant is the entity that actually filed the application. most of them are represented by law firms (which are customers for the USPTO).
  * app_num (int) - Application number
  * applicant_fp (text) - Applicant fingerprint (links to applicant.fingerprint)

=== CLASSIFICATION TABLES ===

- app_cpc: Application CPC classifications (CURRENT CLASSIFICATIONS)
  * app_num (int) - Application number
  * cpc_class (text) - Full CPC classification
  * category (text) - CPC category (e.g., A01B)
  * top_level (text) - Top level classification
  * level_0 (text) - Level 0 classification

- cpc_class: CPC classification definitions (REFERENCE DATA)
  * symbol (text, unique) - CPC symbol (e.g., A01B1/00)
  * level (int) - Classification level
  * title (text) - Classification title
  * parent (text) - Parent classification
  * class_desc (text) - Detailed description

- uspc_class: US Patent Classification (LEGACY SYSTEM)
  * id (text, primary) - USPC class ID
  * number (text) - Class number
  * title (text) - Class title
  * description (text) - Detailed description

=== OPTIMIZED MATERIALIZED VIEWS (Use for complex queries) ===

- app_m_view: Comprehensive application view
  ➤ Pre-joined application data with firm, applicant, and CPC info
  ➤ USE THIS for complex queries needing multiple entity data

- att_firm_m_view: Attorneys with their firms
  ➤ Pre-joined attorney and firm information
  ➤ USE THIS for "attorneys at firm X" queries

- app_attorney_m_view: Applications with attorney and classification
  ➤ Pre-joined application, attorney, and classification data
  ➤ USE THIS for complex attorney-application analytics

=== QUERY GUIDANCE BY COMMON QUESTIONS ===

❓ "Applications filed by attorney with reg number 12345"
➤ USE: doc_attorney JOIN attorney WHERE attorney.reg_num = 12345

❓ "Applications where attorney John Smith represents the applicant"  
➤ USE: app_attorney JOIN attorney WHERE attorney.first_name = 'John' AND attorney.last_name = 'Smith'

❓ "Applications by firm 'ABC Law'"
➤ USE: application JOIN customer_add WHERE customer_add.firm_name ILIKE '%ABC Law%'

❓ "Patents filed in 2023"
➤ USE: application WHERE filing_date BETWEEN '2023-01-01' AND '2023-12-31'

❓ "Applications by inventor named David"
➤ USE: app_inventor JOIN inventor WHERE inventor.first_name ILIKE '%David%'

❓ "Applications by Apple Inc"
➤ USE: app_applicant JOIN applicant WHERE applicant.org_name ILIKE '%Apple%'

❓ "Applications in CPC class A01B"
➤ USE: app_cpc WHERE category = 'A01B' OR cpc_class LIKE 'A01B%'

=== Warnings ===

- Never use "select *" in your queries. Always specify the columns you want to select.
- Never use "where 1=1" in your queries. Always specify the columns you want to select.
"""

log_level_text = os.getenv("SUPERSET_LOG_LEVEL", "INFO")
LOG_LEVEL = getattr(logging, log_level_text.upper(), logging.INFO)

if os.getenv("CYPRESS_CONFIG") == "true":
    # When running the service as a cypress backend, we need to import the config
    # located @ tests/integration_tests/superset_test_config.py
    base_dir = os.path.dirname(__file__)
    module_folder = os.path.abspath(
        os.path.join(base_dir, "../../tests/integration_tests/")
    )
    sys.path.insert(0, module_folder)
    from superset_test_config import *  # noqa

    sys.path.pop(0)

#
# Optionally import superset_config_docker.py (which will have been included on
# the PYTHONPATH) in order to allow for local settings to be overridden
#
try:
    import superset_config_docker
    from superset_config_docker import *  # noqa

    logger.info(
        f"Loaded your Docker configuration at [{superset_config_docker.__file__}]"
    )
except ImportError:
    logger.info("Using default Docker config...")
