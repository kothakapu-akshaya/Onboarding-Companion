# Onboarding Companion — Frontend

React + TypeScript + Vite frontend for the Onboarding Companion: a
checklist app that walks interns through the Swecha Workbench setup tasks.

## Tech Stack

- React 19, TypeScript, Vite
- React Router, Axios
- CSS custom properties (design tokens), `data-theme` dark/light mode
- Vitest + Testing Library, ESLint, Prettier, Husky, lint-staged

## Features

- **Authentication** — phone-number + password login, JWT stored in the
  browser, session restored and validated on load, expired-token 401
  handling, route protection.
- **Onboarding checklist** — 16 tasks across 4 categories (System Setup,
  Git & GitLab, AI & Tooling, Swecha Ecosystem).
- **Evidence upload** — 1–6 screenshots per task (PNG/JPG/GIF, 5 MB
  max each) uploaded to the onboarding backend (stored in object storage),
  with a preview dialog and per-image removal.
- **Progress** — task completion state is stored on the onboarding backend
  (Postgres) and reflected on the dashboard progress card and checklist.
- **Legacy data migration** — previously browser-local progress/images are
  uploaded to the backend automatically once, then removed from
  `localStorage` (only after successful persistence).
- **Theme** — light/dark toggle persisted to `localStorage`; defaults to the
  OS preference.

## Architecture: Server-Backed Progress

Task definitions are static in the frontend (`src/data/onboardingTasks.ts`).
Progress and evidence are persisted on the **onboarding backend**, which is a
separate service from the Corpus API:

- Corpus API (`VITE_API_URL`) is used only for login, `/auth/me` and 404
  check; the onboarding API (`VITE_ONBOARDING_API_URL`) has its own client
  (`src/api/onboardingAxios.ts`) but reuses the **same JWT** stored under the
  `token` `localStorage` key, so there is no second login.
- Evidence files are sent as `multipart/form-data` uploads and never stored
  in `localStorage` as base64.
- Evidence previews use backend-signed URLs; the browser never constructs
  public MinIO/object-storage URLs.
- `localStorage["onboarding-progress"]` is only retained for the one-time
  migration of legacy data and is not used as the source of truth.

## Directory Structure

```text
src/
├── api/            # Axios instances (corpus auth + onboarding API, 401 handling)
├── components/     # Layout, Sidebar, TaskCard, ProgressCard, ProfileCard, ThemeToggle
├── context/        # AuthProvider/useAuth + OnboardingProvider/useOnboarding
├── data/           # onboardingTasks.ts (16 tasks)
├── Pages/          # Login, Dashboard, Tasks, TaskDetails, Profile
├── routes/         # AppRoutes, ProtectedRoute
├── services/       # auth.ts (login, getCurrentUser), onboarding.ts (progress + evidence)
├── styles/         # Component stylesheets using CSS design tokens
├── tests/          # Vitest unit tests
├── types/          # Shared TypeScript types (user, onboarding)
└── utils/          # taskStorage.ts (legacy local persistence), taskMigration.ts
```

## Environment

```env
VITE_API_URL=https://api.corpus.swecha.org/api/v1
VITE_ONBOARDING_API_URL=http://localhost:8000/api/v1
```

No secrets belong in `VITE_*` variables — they are exposed to the browser.

## Scripts

| Command              | Purpose                                    |
| -------------------- | ------------------------------------------ |
| `npm run dev`        | Start the Vite dev server                  |
| `npm run build`      | Type-check and produce a production build  |
| `npm run preview`    | Preview the production build locally       |
| `npm run lint`       | Run ESLint                                 |
| `npm run format`     | Format all files with Prettier             |
| `npm run type-check` | Run `tsc --noEmit`                         |
| `npm test`           | Run tests (use `-- --run` for single pass) |
| `npm run prepare`    | Install the Husky hook                     |

## Testing

```bash
npm test -- --run
```

Tests currently cover:

- ProgressCard percentage/display edge cases
- TaskCard pending vs completed states
- Login form validation and error handling
- Onboarding service calls and HTTP error mapping
- Legacy localStorage → backend migration (journaling, no duplicates)
- Task list and task detail pages backed by a mocked onboarding API
- Logout preserving server-side onboarding data

## Deployment

Deployed to Vercel: https://intern-onboarding-companion.vercel.app

```bash
vercel --prod
```

Rebuilding the same source twice produces byte-identical `dist/` output, so
the build is idempotent.
