# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Apache Superset is a modern, enterprise-ready business intelligence web application built with Python/Flask backend and React/TypeScript frontend. It provides data exploration and visualization capabilities with support for numerous SQL databases.

## Development Commands

### Frontend Development (superset-frontend/)
- `npm run dev` - Start development server with file watching
- `npm run dev-server` - Start webpack dev server (port varies)
- `npm run build` - Production build
- `npm run build-dev` - Development build
- `npm run test` - Run Jest tests (max 80% workers)
- `npm run test-loud` - Run tests with full output
- `npm run tdd` - Run tests in watch mode
- `npm run lint` - Run ESLint and TypeScript checks
- `npm run lint-fix` - Auto-fix linting issues
- `npm run type` - Run TypeScript type checking only
- `npm run format` - Format code with Prettier
- `npm run storybook` - Start Storybook development server

### Backend Development
- `pip install -e .` - Install in development mode
- `superset db upgrade` - Run database migrations
- `superset init` - Initialize database and create admin user
- `superset run` - Start Flask development server
- `pytest` - Run Python tests
- `pylint superset/` - Run Python linting
- `ruff check superset/` - Run fast Python linting

### Database Setup
- Database migrations are in `superset/migrations/versions/`
- Run `superset db upgrade` after pulling changes that include migrations
- Use `superset db downgrade` to rollback if needed

## Architecture Overview

### Frontend Architecture (superset-frontend/)
- **Monorepo Structure**: Uses Lerna workspaces with packages in `packages/` and `plugins/`
- **Core Packages**:
  - `packages/superset-ui-core/` - Core utilities and interfaces
  - `packages/superset-ui-chart-controls/` - Reusable chart controls
  - `plugins/` - Chart type implementations (legacy and modern)
- **Main App**: `src/` contains the main React application
- **State Management**: Redux with @reduxjs/toolkit
- **Styling**: Emotion CSS-in-JS with Ant Design components
- **Build**: Webpack with Babel, supports both development and production builds

### Backend Architecture (superset/)
- **Flask Application**: Main app factory in `superset/app.py`
- **Models**: SQLAlchemy models in `superset/models/`
- **APIs**: Flask-AppBuilder based REST APIs in various modules (`api.py` files)
- **Commands**: Business logic separated into command pattern in `superset/commands/`
- **Database Engines**: Abstraction layer in `superset/db_engine_specs/`
- **Security**: Flask-AppBuilder security with custom extensions
- **Caching**: Multi-layer caching with Redis/Memcached support
- **Async Queries**: Celery-based background task processing

### Key Modules
- **Charts**: `superset/charts/` - Chart CRUD and data API
- **Dashboards**: `superset/dashboards/` - Dashboard management
- **Datasets**: `superset/datasets/` - Data source management  
- **SQL Lab**: `superset/sqllab/` - Interactive SQL interface
- **Security**: `superset/security/` - Authentication and authorization
- **Database Connections**: `superset/databases/` - Database connectivity

### Frontend-Backend Integration
- **API Communication**: REST APIs with standardized error handling
- **Data Flow**: Frontend makes API calls to backend, which queries databases
- **Authentication**: JWT-based with Flask-Login integration
- **Real-time**: WebSocket support for live updates (superset-websocket/)

## Configuration

### Environment Setup
- Main config: `superset/config.py` (overridden by `superset_config.py`)
- Frontend config: Environment variables and webpack configuration
- Docker: `docker-compose.yml` for local development stack
- Database: Supports PostgreSQL, MySQL, SQLite for metadata

### Feature Flags
- Defined in `superset/config.py`
- Control experimental features and UI variations
- Can be environment-specific

## Testing Strategy

### Frontend Tests
- Jest for unit testing React components
- Testing Library for component testing
- Storybook for component documentation and visual testing
- Tests located in `spec/` directories alongside components

### Backend Tests
- Pytest for unit and integration tests
- Test fixtures in `tests/fixtures/`
- Integration tests in `tests/integration_tests/`
- Database testing with temporary test databases

## Docker Development

The project includes comprehensive Docker support:
- `docker-compose.yml` - Full development stack
- `Dockerfile` - Production container build
- `docker/` - Additional Docker configuration and scripts
- Supports both development and production deployment scenarios

## Security Considerations

- Uses Flask-AppBuilder's security framework
- Role-based access control (RBAC)
- Row-level security support
- SQL injection prevention through SQLAlchemy
- CSRF protection enabled
- Guest token support for embedded dashboards

## Performance

- Multi-level caching (query results, metadata)
- Async query execution with Celery
- Database query optimization
- Frontend code splitting and lazy loading
- Thumbnail generation for dashboard previews