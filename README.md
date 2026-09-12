# Intern Onboarding Companion

A full-stack web application that guides new interns through the Swecha Workbench
onboarding checklist. Interns log in, work through 16 well-defined onboarding
tasks, and upload screenshot evidence for each one while tracking their overall
progress.

## Repository Layout

| Path        | Description                                                             |
| ----------- | ----------------------------------------------------------------------- |
| `frontend/` | React + TypeScript + Vite single-page application (deployed on Vercel). |
| `backend/`  | Existing FastAPI corpus backend (deployed at `api.corpus.swecha.org`).  |

The onboarding checklist is intentionally **frontend-owned**:

- The production backend exposes no onboarding-task endpoints
  (`GET/POST/PATCH /api/v1/tasks/` → 404), so task definitions and progress
  are kept entirely in the browser.
- Completed tasks and their screenshot evidence are stored in `localStorage`
  under `onboarding-progress`, sized against a local storage budget to avoid
  exceeding the browser quota.
- The backend `/records/upload*` endpoints belong to the corpus-contribution
  system and are **not** used for task evidence.

## Features

- Phone-number + password login using the shared backend (`POST /api/v1/auth/login`).
- Session validation and automatic 401 handling (expired tokens redirect to login).
- 16-task onboarding checklist grouped into categories (System Setup, Git &
  GitLab, AI & Tooling, Swecha Ecosystem), based on the official Workbench
  Setup guide.
- Per-task screenshot evidence (1–5 images) with an inline preview dialog.
- Progress dashboard derived from `completed / total` — never hardcoded.
- Light/dark theme with a sidebar toggle (persisted, respects system preference).
- Responsive layout and keyboard-accessible components.

## Running the Frontend

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

Create `frontend/.env`:

```env
VITE_API_URL=https://api.corpus.swecha.org/api/v1
```

## Quality Checks

```bash
cd frontend
npm run lint
npm run format
npm run type-check
npm test -- --run
npm run build
```

Unit tests cover the progress card, task card, login validation, and task
storage/quota handling. The root `.husky/pre-commit` hook runs
`lint-staged`, `type-check`, tests, and the build from the `frontend/` directory.

## Deployment

The frontend is deployed with Vercel:

- Live: https://intern-onboarding-companion.vercel.app
- The production build is deterministic — rebuilding the same source twice
  produces byte-identical output, so redeploys are idempotent.

```bash
cd frontend
vercel --prod
```

## Backend

The `backend/` directory is the shared Swecha corpus backend (FastAPI,
PostgreSQL/PostGIS, Redis, Celery, MinIO) with its own Docker Compose setup and
GitLab CI. It is consumed read-only by this frontend except for authentication.
