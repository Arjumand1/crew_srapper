# Crew Scraper

A project built with Django Rest Framework (backend) and Vue 3 with TypeScript (frontend).

## Setup Instructions

### Prerequisites

- Docker and Docker Compose installed on your system

### Environment Setup

1. Make sure you have the `.env` files in the appropriate directories:
   - `backend/.env` - Contains Django and database settings
   - `frontend/.env` - Contains frontend configuration

### Starting the Services

To start all services (database, backend, and frontend), run:

```bash
docker-compose up
```

Or to run in detached mode:

```bash
docker-compose up -d
```

### Accessing the Services

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- Django Admin: http://localhost:8000/admin

### Stopping the Services

```bash
docker-compose down
```

To remove volumes when stopping:

```bash
docker-compose down -v
```
