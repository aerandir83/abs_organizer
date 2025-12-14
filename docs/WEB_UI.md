# Web UI Instructions

The Web UI allows you to manually review, edit, and process books detected by AutoLibrarian.

## Prerequisites

- Node.js installed (v18+)
- Python dependencies installed (`pip install -r requirements.txt`)

## Running the Application

1. **Start the Backend**:
   Run the AutoLibrarian as usual. It will now start a background API server on port 8000.
   ```bash
   python -m src.main
   ```
   *Ensure `WEB_UI_ENABLED=true` is set in your `.env` or defaults.*

2. **Start the Frontend**:
   Navigate to the UI directory and start the dev server:
   ```bash
   cd src/web/ui
   npm run dev
   ```
   Open your browser to the URL shown (usually `http://localhost:5173`).

## Features

- **Dashboard**: View all pending book imports.
- **Review**: See detected metadata and confidence score.
- **Edit**: Manually correct titles, authors, years, etc.
- **Search**: Query external providers (OpenLibrary, Google Books) to find the correct match.
- **Process**: detailed approval process moves the item to the final destination.

## Configuration

In `src/config.py` (or `.env`):
- `WEB_UI_ENABLED`: Set to `true` (default).
- `API_PORT`: Port for the backend API (default: 8000).
- `WEB_PORT`: Port hint for the frontend (Vite defaults to 5173).
