# Backend for Kalio Creative Hub Admin Dashboard

This folder contains a minimal Flask application that provides API endpoints backed by MongoDB and can serve the frontend HTML files from the workspace.

## Setup

1. **Create a Python environment** (venv or conda) and activate it:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **MongoDB**
   - Make sure you have a running MongoDB instance (local or cloud).
   - Copy `.env.example` to `.env` and adjust the `MONGO_URI` if needed.
     ```bash
     cp .env.example .env
     ```
4. **Run the server**:
   ```bash
   python app.py
   ```
   The server will start on `http://localhost:5000`.

## Available API routes

- `GET /api/health` – simple health check.
- `GET /api/stats` – dynamic statistics (projects, clients, new messages computed from collections).
- `GET /api/recent/messages` – returns recent message records formatted for the dashboard.
- `GET /api/recent/projects` – returns recent project records formatted for the dashboard.
- `POST /api/messages` – create a new message document (internal use).
- `POST /api/contact` – public contact form submissions are stored in `messages`.
- `GET /api/portfolio` – returns the array of image filenames used by the public portfolio.
- `GET /api/notifications` – counts of unread alerts and messages for the dashboard badges.
- `GET /api/charts/projects` – data used to render the projects line chart.
- `GET /api/charts/services` – data used to render the services distribution chart.
- `GET /api/quick-actions` – definitions for the dashboard quick action buttons.

Additional CRUD routes can be added similarly.

The frontend HTML pages now fetch these endpoints to replace hard-coded data (stats cards, charts, notifications, recent lists, quick actions, portfolio, and contact form).
## Frontend integration

The existing HTML pages (e.g. `AdminScreen.html`) make `fetch` calls to these endpoints. When the server is running, open `http://localhost:5000/admin` in your browser to view the dashboard.

Adjust the front-end JavaScript to call any new endpoints as your features grow.

> **Tip:** You can use tools like [Postman](https://www.postman.com/) or `curl` to test the API while building.
