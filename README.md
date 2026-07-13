# Intern Onboarding Companion

## Overview

The Intern Onboarding Companion is a web application designed to simplify the onboarding process for new employees. Instead of relying on scattered emails, messages, and documents, the application provides a centralized platform where employees can access onboarding information, monitor their progress, view assigned tasks, participate in company events, and manage their profile.

This project is the frontend of the application and communicates with a FastAPI backend using REST APIs.

---

## Tech Stack

### Frontend

* React
* TypeScript
* React Router
* Axios
* CSS

### Backend

* FastAPI

---

## Features

* Secure user authentication using JWT
* Protected routes for authenticated users
* Personalized dashboard
* Employee profile page
* Company events page
* Task management interface
* Progress overview
* Logout functionality

---

## Backend Integration

The following backend APIs have been integrated into the frontend:

| API                                  | Status |
| ------------------------------------ | ------ |
| Login (`POST /api/v1/auth/login`)    | ✅      |
| Current User (`GET /api/v1/auth/me`) | ✅      |
| Events (`GET /api/v1/events`)        | ✅      |

### Authentication

* Users authenticate using the backend Login API.
* JWT tokens are securely stored in the browser and automatically attached to authenticated requests.
* Protected routes prevent unauthorized access to application pages.

---

## Dashboard

The dashboard provides a quick overview of the onboarding process by displaying:

* Logged-in information
* Overall onboarding progress
* Today's tasks
* Upcoming company events

User information and events are fetched dynamically from the backend.

---

## Tasks

The task interface has been fully developed on the frontend.

At present, task data is displayed using placeholder data because the available backend does not expose task retrieval or update APIs. The application has been structured so that backend task integration can be added with minimal changes once those endpoints become available.

---

## Profile

The Profile page retrieves employee information from the backend and displays details such as:

* Name
* Phone Number
* Email Address
* Role
* Profession
* Organization

Additional profile information is displayed whenever it is available from the backend response.

---

## Events

The Events page retrieves company events from the backend and displays:

* Event name
* Event date
* Event description

---

## Running the Project

### Install dependencies

```bash
npm install
```

### Start the development server

```bash
npm run dev
```

The application will be available at:

```text
http://localhost:5173
```

---

## Backend Requirements

Before running the frontend, ensure the FastAPI backend is running.

Default backend URL:

```text
http://localhost:8000
```

---

## Development Notes

* Authentication was tested using a seed user available in the backend environment.
* Axios is used for API communication.
* Route protection is implemented using React Router.
* Components have been designed to be reusable across multiple pages.

---

## Current Implementation Status

| Feature                  | Status                        |
| ------------------------ | ----------------------------- |
| Login                    | ✅ Completed                   |
| Authentication           | ✅ Completed                   |
| Protected Routes         | ✅ Completed                   |
| Dashboard                | ✅ Integrated                  |
| Profile                  | ✅ Integrated                  |
| Events                   | ✅ Integrated                  |
| Tasks UI                 | ✅ Completed                   |
| Task Backend Integration | ⏳ Pending (API not available) |

---

## Future Improvements

* Integrate backend task management APIs
* Enable task completion updates
* Event registration functionality
* Profile editing
* Dashboard analytics
* Improved responsive design

---

## Author

**Akshaya Kothakapu**
