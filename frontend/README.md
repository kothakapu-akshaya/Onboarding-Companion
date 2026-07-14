# Intern Onboarding Companion

## Overview

The Intern Onboarding Companion is a full-stack web application designed to simplify the onboarding process for new employees. Instead of relying on scattered emails, messages, and documents, the application provides a centralized platform where employees can access onboarding information, monitor their progress, view assigned tasks, participate in company events, and manage their profile.

The frontend is built using React and TypeScript, while the backend is developed using FastAPI. The application communicates with the backend through REST APIs and provides a secure and responsive onboarding experience.

---

## Tech Stack

### Frontend

- React
- TypeScript
- Vite
- React Router
- Axios
- CSS

### Backend

- FastAPI
- PostgreSQL
- Redis
- Celery
- MinIO
- Docker Compose

### Development Tools

- Git
- GitLab
- Swagger (OpenAPI)
- ESLint
- Prettier
- Husky
- lint-staged
- Vitest

---

## Features

- Secure JWT Authentication
- Protected Routes
- Employee Dashboard
- Employee Profile
- Task Management
- Company Events
- Onboarding Progress Tracking
- REST API Integration
- Responsive User Interface

---

## Backend Integration

The following backend APIs have been integrated into the frontend:

| API | Status |
|------|--------|
| Login (`POST /api/v1/auth/login`) | Completed |
| Current User (`GET /api/v1/auth/me`) | Completed |
| Tasks (`GET /api/v1/tasks`) | Completed |
| Events (`GET /api/v1/events`) | Completed |

---

## Authentication

- Users authenticate using the backend Login API.
- JWT tokens are securely stored in the browser.
- Axios automatically attaches the authentication token to protected requests.
- Protected routes prevent unauthorized users from accessing application pages.

---

## Dashboard

The Dashboard provides an overview of the employee onboarding process by displaying:

- Logged-in employee information
- Overall onboarding progress
- Assigned onboarding tasks
- Upcoming company events

All dashboard information is fetched dynamically from the backend through REST APIs.

---

## Tasks

The Tasks module is fully integrated with the backend Task APIs.

Users can:

- View assigned onboarding tasks
- View task status
- Display task information dynamically from the backend
- Access updated task information without relying on hardcoded or mock data

The Dashboard also displays a summary of onboarding tasks retrieved from the backend.

---

## Profile

The Profile page retrieves employee information from the backend and displays details such as:

- Name
- Email Address
- Phone Number
- Role
- Profession
- Organization

Additional profile information is displayed whenever it is available from the backend response.

---

## Events

The Events page retrieves company events from the backend and displays:

- Event Name
- Event Date
- Event Description

Upcoming events displayed on the Dashboard are also fetched from the backend.

---

## Running the Project

### Clone the Repository

```bash
git clone <repository-url>
```

### Backend Setup

```bash
cd backend
docker compose up --build
```

The backend will be available at:

```text
http://localhost:8000
```

Swagger Documentation:

```text
http://localhost:8000/docs
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at:

```text
http://localhost:5173
```

---

## Development Credentials

The backend provides seeded users for local development and testing.

### Admin User

Phone:

```text
+919900000000
```

Password:

```text
SeedAdmin@123
```

### Regular User

Phone:

```text
+919900000001
```

Password:

```text
SeedUser@123
```

These credentials are intended only for development and testing.

---

## Quality Checks

The frontend uses Husky and lint-staged to perform automated quality checks before every commit.

The following commands are executed:

```bash
npm run lint
npm run format
npm run type-check
npm test -- --run
npm run build
```

These checks ensure:

- Consistent code formatting
- ESLint validation
- TypeScript type safety
- Unit testing
- Successful production build

---

## Project Structure

```text
onboarding-companion-fullstack/

├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── Pages/
│   │   ├── services/
│   │   ├── routes/
│   │   └── styles/
│   └── package.json
│
└── backend/
    ├── app/
    ├── scripts/
    ├── alembic/
    ├── Dockerfile
    ├── docker-compose.yml
    └── pyproject.toml
```

---

## Development Notes

- Axios is used for API communication.
- Route protection is implemented using React Router.
- Reusable components are used throughout the application.
- The frontend communicates with the backend using REST APIs.
- Docker Compose is used for local backend development.
- Swagger is used for API testing and verification.

---

## Current Implementation Status

| Feature | Status |
|----------|--------|
| Login | Completed |
| Authentication | Completed |
| Protected Routes | Completed |
| Dashboard | Completed |
| Profile | Completed |
| Events | Completed |
| Tasks UI | Completed |
| Task Backend Integration | Completed |

---

## Future Improvements

- Task status updates from the frontend
- Event registration functionality
- Profile editing
- Dashboard analytics
- Improved responsive design
- Production deployment
- Continuous Integration and Continuous Deployment (CI/CD)

---

## Deployment

Deployment is currently in progress. The live application URL will be added after deployment.

---

## Author

**Akshaya Kothakapu**