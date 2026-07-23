# Intern Onboarding Companion

## Overview

The Intern Onboarding Companion is a full-stack web application designed to simplify the onboarding process for new employees. Instead of relying on scattered emails, messages, and documents, the application provides a centralized platform where employees can securely log in, access onboarding information, monitor their progress, view company events, and manage their profile.

The frontend is built using React, TypeScript, and Vite, while the backend is powered by FastAPI. The application communicates with the backend through REST APIs and provides a responsive and secure onboarding experience.

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
- Vercel

---

## Features

- Secure JWT Authentication
- Protected Routes
- Employee Dashboard
- User Profile
- Company Events
- Onboarding Progress Tracking
- REST API Integration
- Responsive User Interface
- Production Deployment with Vercel

---

## Backend Integration

The frontend is integrated with the following backend APIs:

| API | Status |
|------|--------|
| POST `/api/v1/auth/login` |  Completed |
| GET `/api/v1/auth/me` |  Completed |
| GET `/api/v1/events` |  Completed |
| GET `/api/v1/users/{user_identifier}/profile` |  Completed |

---

## API Configuration

The frontend communicates with the backend using an environment variable.

Create a `.env` file inside the frontend directory:

```env
VITE_API_URL=https://api.corpus.swecha.org/api/v1
```

---

## Authentication

- Users log in using their phone number and password.
- JWT authentication is implemented using the backend Login API.
- Access tokens are stored in the browser.
- Protected routes prevent unauthorized access to application pages.
- Authenticated requests automatically include the JWT token.

---

## Dashboard

The Dashboard provides an overview of the onboarding process by displaying:

- Logged-in user information
- Onboarding progress
- Company events
- User profile summary

All information is retrieved dynamically from the backend through REST APIs.

---

## Profile

The Profile page displays user information fetched from the backend, including:

- Username
- Name
- Email
- Phone Number
- Profession
- Organization
- User Roles

Additional profile details are displayed whenever available from the backend response.

---

## Events

The Events page retrieves company events from the backend and displays:

- Event Name
- Event Description
- Event Date
- Event Status

---

## Running the Project

### Clone the Repository

```bash
git clone <repository-url>
```

---

### Backend Setup

```bash
cd backend
docker compose up --build
```

Backend:

```
http://localhost:8000
```

Swagger Documentation:

```
http://localhost:8000/docs
```

---

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend:

```
http://localhost:5173
```

---

## Production Build

Create a production build:

```bash
npm run build
```

Preview the production build locally:

```bash
npm run preview
```

---

## Deployment

The frontend is deployed using **Vercel**.

### Live Demo

https://intern-onboarding-companion.vercel.app

To deploy manually:

```bash
npm install -g vercel

vercel

vercel --prod
```

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
- Successful production build

---

## Project Structure

```text
onboarding-companion/

├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── routes/
│   │   ├── styles/
│   │   └── tests/
│   ├── public/
│   ├── package.json
│   └── vite.config.ts
│
└── backend/
    ├── app/
    ├── alembic/
    ├── Dockerfile
    ├── docker-compose.yml
    └── pyproject.toml
```

---

## Development Notes

- Axios is used for API communication.
- React Router is used for client-side routing.
- JWT-based authentication secures protected pages.
- REST APIs are documented using Swagger.
- Docker Compose is used for local backend development.
- Vercel is used for frontend deployment.
- TypeScript provides static type checking.

---

## Current Implementation Status

| Feature | Status |
|----------|--------|
| Login |  Completed |
| JWT Authentication |  Completed |
| Protected Routes |  Completed |
| Dashboard |  Completed |
| Profile |  Completed |
| Events |  Completed |
| REST API Integration |  Completed |
| Production Build |  Completed |
| Vercel Deployment |  Completed |

---

## Current Limitations

- Some backend endpoints are accessible only to authorized roles.
- Certain features depend on backend permissions and available APIs.
- The application relies on the production backend for data.

---

## Future Improvements

- Enhanced dashboard analytics
- Improved responsive design
- Better loading and error states
- Expanded unit testing
- Continuous Integration and Continuous Deployment (CI/CD)

---

## Author

**Akshaya Kothakapu**