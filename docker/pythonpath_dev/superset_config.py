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

{
  "database_name": "patent_database",
  "description": "USPTO Patent Application Database Schema",
  "tables": {
    "application": {
      "description": "Main patent applications table (PRIMARY DATA SOURCE)",
      "columns": {
        "app_num": {
          "type": "int",
          "constraints": ["primary"],
          "description": "Application number (unique identifier)"
        },
  "materialized_views": {
    "app_m_view": {
      "description": "Comprehensive application view with denormalized data (OPTIMIZED FOR QUERIES)",
      "purpose": "Flattened view combining application data with CPC classifications, firm information, and applicant details",
      "columns": {
        "app_num": {
          "source": "application.app_num",
          "type": "int",
          "description": "Application number (unique identifier)"
        },
        "filing_date": {
          "source": "application.filing_date",
          "type": "date",
          "description": "Application filing date"
        },
        "cat": {
          "source": "application.cat",
          "type": "text",
          "description": "Category (REGULAR/REISSUE)"
        },
        "group_art": {
          "source": "application.group_art",
          "type": "text",
          "description": "Art group classification"
        },
        "inv_title": {
          "source": "application.inv_title",
          "type": "text",
          "description": "Invention title"
        },
        "app_status": {
          "source": "application.app_status",
          "type": "text",
          "description": "Application status"
        },
        "status_code": {
          "source": "application.status_code",
          "type": "text",
          "description": "USPTO status code"
        },
        "patent_num": {
          "source": "application.patent_num",
          "type": "text",
          "description": "Patent number if granted"
        },
        "grant_date": {
          "source": "application.grant_date",
          "type": "date",
          "description": "Grant date"
        },
        "type_code": {
          "source": "application.type_code",
          "type": "text",
          "description": "Application type (DES/UTL/PLT)"
        },
        "class_num": {
          "source": "application.class_num",
          "type": "text",
          "description": "Classification number"
        },
        "subclass_num": {
          "source": "application.subclass_num",
          "type": "text",
          "description": "Subclass number"
        },
        "type_label": {
          "source": "application.type_label",
          "type": "text",
          "description": "Type label"
        },
        "customer_num": {
          "source": "application.customer_num",
          "type": "int",
          "description": "Customer number"
        },
        "examiner_name": {
          "source": "application.examiner_name",
          "type": "text",
          "description": "Examiner name. All capital letters with format: 'Last, First Middle'."
        },
        "cpc_class": {
          "source": "app_cpc.category",
          "type": "text",
          "description": "CPC classification category"
        },
        "cpc_desc": {
          "source": "cpc_class.class_desc",
          "type": "text",
          "description": "CPC classification description"
        },
        "firm_name": {
          "source": "customer_add.firm_name",
          "type": "text",
          "description": "Law firm name"
        },
        "url": {
          "source": "customer_add.url",
          "type": "text",
          "description": "Firm website URL"
        },
        "org_name": {
          "source": "applicant.org_name",
          "type": "text",
          "description": "Applicant organization name"
        },
        "country": {
          "source": "applicant.country",
          "type": "text",
          "description": "Applicant country"
        }
      },
      "joins": [
        "application (base)",
        "app_cpc (LEFT JOIN DISTINCT on app_num)",
        "cpc_class (JOIN on category = symbol)",
        "customer_add (LEFT JOIN on customer_num)",
        "app_applicant (LEFT JOIN on app_num)",
        "applicant (LEFT JOIN on applicant_fp = fingerprint)"
      ],
      "usage_notes": "Preferred for complex queries requiring application data with related entities. Eliminates need for multiple joins in most common queries."
    },
    "att_firm_m_view": {
      "description": "Attorney-firm relationship view (OPTIMIZED FOR ATTORNEY-FIRM QUERIES)",
      "purpose": "Shows attorneys and their associated law firms through application relationships",
      "columns": {
        "reg_num": {
          "source": "attorney.reg_num",
          "type": "int",
          "description": "Attorney registration number (DISTINCT)"
        },
        "first_name": {
          "source": "attorney.first_name",
          "type": "text",
          "description": "Attorney first name. All capital letters."
        },
        "middle_name": {
          "source": "attorney.middle_name",
          "type": "text",
          "description": "Attorney middle name. All capital letters."
        },
        "last_name": {
          "source": "attorney.last_name",
          "type": "text",
          "description": "Attorney last name. All capital letters."
        },
        "practitioner_type": {
          "source": "attorney.practitioner_type",
          "type": "enum",
          "description": "Attorney or agent",
          "valid_values": ["ATTORNEY", "AGENT", "DESIGN", "DESIGN AGENT", "LIMITED"],
        },
        "gender": {
          "source": "attorney.gender",
          "type": "int",
          "description": "Gender demographics"
        },
        "eth": {
          "source": "attorney.eth",
          "type": "text",
          "description": "Ethnicity demographics"
        },
        "nat": {
          "source": "attorney.nat",
          "type": "text",
          "description": "Nationality demographics"
        },
        "firm_name": {
          "source": "customer_add.firm_name",
          "type": "text",
          "description": "Associated law firm name"
        }
      },
      "joins": [
        "attorney (base)",
        "app_attorney (LEFT JOIN on reg_num = att_num)",
        "application (LEFT JOIN on app_num)",
        "customer_add (LEFT JOIN on customer_num)"
      ],
      "usage_notes": "Use for queries about attorney-firm relationships. Shows which attorneys work with which firms based on application representations. Uses DISTINCT to avoid duplicate attorney records."
    }
        "filing_date": {
          "type": "date",
          "description": "Application filing date"
        },
        "cat": {
          "type": "text",
          "description": "Category",
          "valid_values": ["REGULAR", "REISSUE"],
          "notes": "REGULAR = new application, REISSUE = reissue of existing application"
        },
        "group_art": {
          "type": "text",
          "description": "Art group. USPTO uses one single art group number to classify all applications in the same art group. Almost all are numbers, with several exceptions."
        },
        "inv_title": {
          "type": "text",
          "description": "Invention title describes what the invention is"
        },
        "app_status": {
          "type": "text",
          "description": "Application status text description - See status_code for more details. Valid text descriptions are defined in status_code's mapping."
        },
        "status_code": {
          "type": "text",
          "description": "Status code. USPTO uses numbers to identify the status of the application. Corresponds to app_status.",
          "mapping": {
            "1": "Missassigned Application Number",
            "100": "Awaiting TC Resp, Issue Fee Payment Verified",
            "116": "Appeal Ready for Review",
            "119": "TC Return of Appeal",
            "120": "Notice of Appeal Filed",
            "121": "Appeal Brief (or Supplemental Brief) Entered and Forwarded to Examiner",
            "122": "Examiner's Answer to Appeal Brief Counted",
            "123": "Examiner's Answer to Appeal Brief Mailed",
            "124": "On Appeal -- Awaiting Decision by the Board of Appeals",
            "127": "Amendment after notice of appeal",
            "128": "Reply Brief (or Supplemental Reply Brief) Forwarded to Examiner",
            "130": "Examiner's Answer to Reply Brief or Response to Remand Mailed",
            "131": "Reply Brief (or Supplemental Reply Brief) Filed - Not Entered",
            "132": "Appeal Awaiting BPAI Docketing",
            "133": "Reply Brief filed and forwarded to BPAI",
            "135": "Board of Appeals Decision Rendered",
            "136": "Amendment / Argument after Board of Appeals Decision",
            "139": "Appeal Dismissed / Withdrawn",
            "140": "Prosecution Suspended",
            "143": "Request Reconsideration after Board of Appeals Decision",
            "144": "Board of Appeals Decision Rendered after Request for Reconsideration",
            "150": "Patented Case",
            "151": "Patented File - (Old Case Added for File Tracking Purposes)",
            "160": "Abandoned  --  Incomplete Application (Pre-examination)",
            "161": "Abandoned  --  Failure to Respond to an Office Action",
            "162": "Expressly Abandoned  --  During Publication Process",
            "163": "Abandoned  --  After Examiner's Answer or Board of Appeals Decision",
            "164": "Abandoned  --  Failure to Pay Issue Fee",
            "165": "ABANDONED - RESTORED",
            "166": "Abandoned  --  File-Wrapper-Continuation Parent Application",
            "167": "Abandonment for Failure to Correct Drawings/Oath/NonPub Request",
            "168": "Expressly Abandoned  --  During Examination",
            "169": "Abandoned  --  Incomplete (Filing Date Under Rule 53 (b) - PreExam)",
            "17": "Sent to Classification contractor",
            "172": "Interference -- Initial Memorandum",
            "174": "Interference -- Declared by Board of Interferences",
            "18": "Application Returned back to Preexam",
            "180": "Interference -- Decision on Priority Rendered by Board of Interferences",
            "19": "Application Undergoing Preexam Processing",
            "195": "Application Involved in Court Proceedings",
            "197": "Court Proceedings Terminated",
            "20": "Application Dispatched from Preexam, Not Yet Docketed",
            "250": "Patent Expired Due to NonPayment of Maintenance Fees Under 37 CFR 1.362",
            "3": "Proceedings Terminated",
            "30": "Docketed New Case - Ready for Examination",
            "31": "AWAITING RESPONSE FOR INFORMALITY, FEE DEFICIENCY OR CRF ACTION",
            "37": "Special New",
            "38": "Rocket Docket",
            "40": "Non Final Action Counted, Not Yet Mailed",
            "41": "Non Final Action Mailed",
            "423": "Non-Final Action Mailed",
            "424": "Response after Non-Final Action Entered (or Ready for Examiner Action)",
            "432": "Notice of Appeal Filed",
            "435": "Examiner's Answer Mailed",
            "439": "Reexamination forwarded to Board for Decision on Appeal",
            "50": "Ex parte Quayle Action Counted, Not Yet Mailed",
            "51": "Ex parte Quayle Action Mailed",
            "60": "Final Rejection Counted, Not Yet Mailed",
            "61": "Final Rejection Mailed",
            "66": "Withdrawn Abandonment, awaiting examiner action",
            "660": "Ready for Reexam -- Certificate in IFW",
            "71": "Response to Non-Final Office Action Entered and Forwarded to Examiner",
            "77": "Response to Ex parte Quayle Action Entered and Forwarded to Examiner",
            "80": "Response after Final Action Forwarded to Examiner",
            "82": "Advisory Action Counted, Not Yet Mailed",
            "83": "Advisory Action Mailed",
            "865": "Supplemental examiner's answer to appeal brief",
            "90": "Allowed -- Notice of Allowance Not Yet Mailed",
            "91": "Withdraw from issue awaiting action",
            "93": "Notice of Allowance Mailed -- Application Received in Office of Publications",
            "94": "Publications -- Issue Fee Payment Received",
            "95": "Publications -- Issue Fee Payment Verified",
            "98": "Awaiting TC Resp., Issue Fee Not Paid",
            "99": "Awaiting TC Resp, Issue Fee Payment Received"
          }
        },
        "patent_num": {
          "type": "text",
          "description": "Patent number if granted"
        },
        "grant_date": {
          "type": "date",
          "description": "Grant date"
        },
        "type_code": {
          "type": "text",
          "description": "Application type",
          "valid_values": ["DES", "UTL", "PLT"],
          "notes": "DES = design patent, UTL = utility patent, PLT = plant patent"
        },
        "class_num": {
          "type": "text",
          "description": "Classification number using United States Patent Classification (distinct from CPC classification)"
        },
        "examiner_name": {
          "type": "text",
          "description": "Examiner name (denormalized, prefer examiner table)"
        },
        "customer_num": {
          "type": "int",
          "description": "Links to customer_add for firm information"
        },
        "first_applicant_name": {
          "type": "text",
          "description": "Denormalized first applicant name"
        },
        "first_inventor_name": {
          "type": "text",
          "description": "Denormalized first inventor name"
        }
      }
    },
    "attorney": {
      "description": "Patent attorneys/agents (MASTER ATTORNEY DATA)",
      "columns": {
        "id": {
          "type": "serial",
          "constraints": ["primary"]
        },
        "reg_num": {
          "type": "int",
          "constraints": ["unique"],
          "description": "Registration number (USE THIS for attorney searches)"
        },
        "first_name": {
          "type": "text",
          "description": "Attorney first name. All capital letters."
        },
        "middle_name": {
          "type": "text",
          "description": "Attorney middle name. All capital letters."
        },
        "last_name": {
          "type": "text",
          "description": "Attorney last name. All capital letters."
        },
        "practitioner_type": {
          "type": "enum",
          "valid_values": ["ATTORNEY", "AGENT", "DESIGN", "DESIGN AGENT", "LIMITED"],
          "description": "Attorney or agent"
        },
        "active": {
          "type": "boolean",
          "description": "Active status"
        },
        "gender": {
          "type": "int",
          "description": "Gender demographics"
        },
        "eth": {
          "type": "text",
          "description": "Ethnicity demographics"
        },
        "nat": {
          "type": "text",
          "description": "Nationality demographics"
        },
        "org_id": {
          "type": "int",
          "description": "Organization reference"
        }
      }
    },
    "examiner": {
      "description": "Patent examiners (PREFERRED for examiner queries)",
      "columns": {
        "id": {
          "type": "serial",
          "constraints": ["primary"]
        },
        "name": {
          "type": "text",
          "description": "Full examiner name in format: 'Last, First Middle'"
        },
        "gender": {
          "type": "int",
          "description": "Gender demographics"
        },
        "eth": {
          "type": "text",
          "description": "Ethnicity demographics"
        },
        "nat": {
          "type": "text",
          "description": "Nationality demographics"
        }
      }
    },
    "inventor": {
      "description": "Patent inventors (MASTER INVENTOR DATA)",
      "columns": {
        "id": {
          "type": "serial",
          "constraints": ["primary"]
        },
        "first_name": {
          "type": "text",
          "description": "Inventor first name. All capital letters."
        },
        "middle_name": {
          "type": "text",
          "description": "Inventor middle name. All capital letters."
        },
        "last_name": {
          "type": "text",
          "description": "Inventor last name. All capital letters."
        },
        "full_name": {
          "type": "text",
          "description": "Inventor full name. All capital letters. Format: 'First Middle Last'. Use separate fields for first, middle, and last names for purpose of searching."
        },
        "gender": {
          "type": "int",
          "description": "Gender demographics with probability scores"
        },
        "nat": {
          "type": "int",
          "description": "Nationality demographics with probability scores"
        },
        "eth": {
          "type": "text",
          "description": "Ethnicity demographics with probability scores"
        },
        "city": {
          "type": "text",
          "description": "Geographic location - city"
        },
        "country": {
          "type": "text",
          "description": "Geographic location - country"
        }
      }
    },
    "applicant": {
      "description": "Patent applicants/organizations (MASTER APPLICANT DATA)",
      "columns": {
        "id": {
          "type": "serial",
          "constraints": ["primary"]
        },
        "org_name": {
          "type": "text",
          "description": "Organization name (USE THIS for company searches)"
        },
        "org_norm": {
          "type": "text",
          "description": "Normalized organization name"
        },
        "name_line_1": {
          "type": "text",
          "description": "Name line 1"
        },
        "name_line_2": {
          "type": "text",
          "description": "Name line 2"
        },
        "address_line_1": {
          "type": "text",
          "description": "Address line 1"
        },
        "address_line_2": {
          "type": "text",
          "description": "Address line 2"
        },
        "city": {
          "type": "text",
          "description": "City"
        },
        "state": {
          "type": "text",
          "description": "State"
        },
        "country": {
          "type": "text",
          "description": "Country"
        },
        "postal_code": {
          "type": "text",
          "description": "Postal code"
        },
        "fingerprint": {
          "type": "text",
          "constraints": ["unique"],
          "description": "Unique identifier for linking"
        },
        "type": {
          "type": "postal_address_type",
          "description": "Address type"
        }
      }
    },
    "customer_add": {
      "description": "Customer/firm addresses (FIRM INFORMATION)",
      "columns": {
        "id": {
          "type": "serial",
          "constraints": ["primary"]
        },
        "customer_num": {
          "type": "int",
          "constraints": ["unique"],
          "description": "Customer number (links from application.customer_num)"
        },
        "firm_name": {
          "type": "text",
          "description": "Law firm name (USE THIS for firm searches)"
        },
        "url": {
          "type": "text",
          "description": "Firm website"
        },
        "name_line_1": {
          "type": "text",
          "description": "Contact name line 1"
        },
        "name_line_2": {
          "type": "text",
          "description": "Contact name line 2"
        },
        "address_line_1": {
          "type": "text",
          "description": "Address line 1"
        },
        "address_line_2": {
          "type": "text",
          "description": "Address line 2"
        },
        "city": {
          "type": "text",
          "description": "City"
        },
        "state": {
          "type": "text",
          "description": "State"
        },
        "country": {
          "type": "text",
          "description": "Country"
        },
        "postal_code": {
          "type": "text",
          "description": "Postal code"
        }
      }
    },
    "doc_attorney": {
      "description": "FILING ACTIVITY (WHO FILED WHAT) - Use when asking about 'filed by' or 'submitted by' attorney",
      "columns": {
        "id": {
          "type": "serial",
          "constraints": ["primary"]
        },
        "app_num": {
          "type": "int",
          "description": "Application number"
        },
        "doc_code": {
          "type": "text",
          "description": "Document type code"
        },
        "doc_identifier": {
          "type": "text",
          "description": "Unique document identifier"
        },
        "doc_date": {
          "type": "date",
          "description": "Filing date"
        },
        "attorney_num": {
          "type": "int",
          "description": "Attorney registration number who FILED this document"
        },
        "confidence_rate": {
          "type": "double",
          "description": "Data confidence score"
        }
      }
    },
    "app_attorney": {
      "description": "REPRESENTATION RELATIONSHIP (WHO REPRESENTS WHOM) - Power of Attorney (POA) list. Use when asking about attorney representation on applications",
      "columns": {
        "app_num": {
          "type": "int",
          "description": "Application number"
        },
        "att_num": {
          "type": "int",
          "description": "Attorney registration number"
        }
      }
    },
    "app_customer": {
      "description": "APPLICATION-CUSTOMER LINKS. Links applications to customers/firms",
      "columns": {
        "app_num": {
          "type": "int",
          "description": "Application number"
        },
        "customer_num": {
          "type": "int",
          "description": "Customer number"
        }
      }
    },
    "app_inventor": {
      "description": "APPLICATION-INVENTOR LINKS. Links applications to inventors",
      "columns": {
        "app_num": {
          "type": "int",
          "description": "Application number"
        },
        "inventor_id": {
          "type": "int",
          "description": "Inventor ID"
        },
        "add_fingerprint": {
          "type": "text",
          "description": "Address fingerprint"
        },
        "add_type": {
          "type": "postal_address_type",
          "valid_values": ["POSTAL", "RESIDENCE"],
          "description": "when joining to other tables, ONLY use POSTAL addresses type as the necessary default value.",
          "default": "POSTAL",
          "example": "... inventor join app_inventor on app_inventor.add_type = 'POSTAL' and app_inventor.inventor_id = inventor.id"
        }
      }
    },
    "app_applicant": {
      "description": "APPLICATION-APPLICANT LINKS. Links applications to applicants",
      "columns": {
        "app_num": {
          "type": "int",
          "description": "Application number"
        },
        "applicant_fp": {
          "type": "text",
          "description": "Applicant fingerprint (links to applicant.fingerprint)"
        }
      }
    },
    "app_cpc": {
      "description": "Application CPC classifications (CURRENT CLASSIFICATIONS)",
      "columns": {
        "app_num": {
          "type": "int",
          "description": "Application number"
        },
        "cpc_class": {
          "type": "text",
          "description": "Full CPC classification"
        },
        "category": {
          "type": "text",
          "description": "CPC category (e.g., A01B)"
        },
        "top_level": {
          "type": "text",
          "description": "Top level classification"
        },
        "level_0": {
          "type": "text",
          "description": "Level 0 classification"
        }
      }
    },
    "cpc_class": {
      "description": "CPC classification definitions (REFERENCE DATA)",
      "columns": {
        "symbol": {
          "type": "text",
          "constraints": ["unique"],
          "description": "CPC symbol (e.g., A01B1/00)"
        },
        "level": {
          "type": "int",
          "description": "Classification level"
        },
        "title": {
          "type": "text",
          "description": "Classification title"
        },
        "parent": {
          "type": "text",
          "description": "Parent classification"
        },
        "class_desc": {
          "type": "text",
          "description": "Detailed description"
        }
      }
    },
    "uspc_class": {
      "description": "US Patent Classification (LEGACY SYSTEM)",
      "columns": {
        "id": {
          "type": "text",
          "constraints": ["primary"],
          "description": "USPC class ID"
        },
        "number": {
          "type": "text",
          "description": "Class number"
        },
        "title": {
          "type": "text",
          "description": "Class title"
        },
        "description": {
          "type": "text",
          "description": "Detailed description"
        }
      }
    }
  },
  "relationships": {
    "application_to_customer": {
      "type": "one_to_one",
      "from": "application.customer_num",
      "to": "customer_add.customer_num",
      "description": "Links applications to law firms/customers"
    },
    "doc_attorney_to_attorney": {
      "type": "many_to_one",
      "from": "doc_attorney.attorney_num",
      "to": "attorney.reg_num",
      "description": "Links document filings to attorneys"
    },
    "app_attorney_to_attorney": {
      "type": "many_to_one",
      "from": "app_attorney.att_num",
      "to": "attorney.reg_num",
      "description": "Links applications to representing attorneys"
    },
    "app_inventor_to_inventor": {
      "type": "many_to_one",
      "from": "app_inventor.inventor_id",
      "to": "inventor.id",
      "description": "Links applications to inventors"
    },
    "app_applicant_to_applicant": {
      "type": "many_to_one",
      "from": "app_applicant.applicant_fp",
      "to": "applicant.fingerprint",
      "description": "Links applications to applicants"
    }
  },
  "usage_guidelines": {
    "critical_distinctions": {
      "filing_vs_representation": {
        "description": "Choose the correct table based on question intent",
        "filing_activity": {
          "use_table": "doc_attorney",
          "when": "For 'applications FILED BY attorney X' or 'documents filed by attorney X'",
          "description": "Shows WHO FILED specific documents/applications",
          "join": "doc_attorney → attorney ON doc_attorney.attorney_num = attorney.reg_num"
        },
        "representation": {
          "use_table": "app_attorney",
          "when": "For 'applications WHERE attorney X represents the applicant'",
          "description": "Shows ongoing attorney-client relationships",
          "join": "app_attorney → attorney ON app_attorney.att_num = attorney.reg_num"
        },
        "firm_applications": {
          "use_table": "application → customer_add",
          "when": "For 'applications by firm X' (most common)",
          "description": "Shows applications where the firm is the customer of record",
          "join": "application → customer_add ON application.customer_num = customer_add.customer_num",
          "search_by": "customer_add.firm_name"
        }
      }
    },
    "search_recommendations": {
      "attorney_searches": "Use attorney.reg_num for attorney searches",
      "abbreviation" : "When user searches for an abbreviation, you should know the common name of the company and use both the abbreviation and the common name in your SQL in case you miss records in the database. For example, 'NVDA' is the common name for 'NVIDIA'",
      "company_searches": "Use applicant.org_name for company searches",
      "firm_searches": "Use customer_add.firm_name for firm searches",
      "examiner_queries": "Prefer examiner table over denormalized examiner_name in application table",
      "status_queries": "Use status_code column for convenience when finding application status (see mappings in application.status_code field)",
      "optimized_queries": "Always consider using materialized views for better performance before you write a query with connecting tables: app_m_view for comprehensive application data, att_firm_m_view for attorney-firm relationships"
    }
  },

  "notes": {
    "customers": "Customers are probably the law firms. Some are law departments of companies that filed applications.",
    "inventors": "Inventors are the people who invented the invention.",
    "applicants": "Applicant is the entity that actually filed the application. Most are represented by law firms (which are customers for the USPTO).",
    "app_attorney_caveat": "app_attorney shows attorneys in the Power of Attorney (POA) list, doesn't mean the attorney actually represents the applicant. doc_attorney is the correct table for actual filing activity."
  }
}

=== QUERY GUIDANCE BY COMMON QUESTIONS ===

❓ "Applications filed by attorney with reg number 12345"
➤ USE: doc_attorney JOIN attorney WHERE attorney.reg_num = 12345

❓ "Applications where attorney John Smith represents the applicant"  
➤ USE: app_attorney JOIN attorney WHERE attorney.first_name = 'JOHN' AND attorney.last_name = 'SMITH'

❓ "Applications by firm 'ABC, CDE & FGH Law'"
➤ USE: application JOIN customer_add WHERE customer_add.firm_name ILIKE '%ABC%' and customer_add.firm_name ILIKE '%CDE%' and customer_add.firm_name ILIKE '%FGH%'

❓ "Patents filed in 2023"
➤ USE: application WHERE filing_date BETWEEN '2023-01-01' AND '2023-12-31'

❓ "Applications by inventor named David"
➤ USE: app_inventor JOIN inventor WHERE inventor.first_name ILIKE '%DAVID%'

❓ "Applications by Apple Inc"
➤ USE: app_applicant JOIN applicant WHERE applicant.org_name ILIKE '%APPLE%'

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
    from superset_config_docker import *  # noqa: F403

    logger.info(
        f"Loaded your Docker configuration at [{superset_config_docker.__file__}]"
    )
except ImportError:
    logger.info("Using default Docker config...")
