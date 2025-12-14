# Deployment

AutoLibrarian can be deployed using Docker (recommended) or run natively on a system with Python 3.

## Docker Compose (Recommended)

The easiest and recommended way to run AutoLibrarian is using Docker Compose. This encapsulates the application and its dependencies, providing a consistent and isolated environment.

```yaml
version: "3.8"
services:
  autolibrarian:
    build: .
    image: autolibrarian:latest
    container_name: autolibrarian
    environment:
      - INPUT_DIR=/input
      - OUTPUT_DIR=/output
      - ABS_URL=http://audiobookshelf:80
      - ABS_API_KEY=your_api_key_here
      - PUID=1000
      - PGID=1000
    volumes:
      - /path/to/your/input:/input
      - /path/to/your/audiobooks:/output
    restart: unless-stopped
```

### Volumes

-   `/input`: Map this to the folder where you will drop new audiobooks.
-   `/output`: Map this to your organized audiobook library (the same one Audiobookshelf watches).

### Permissions

Ensure the `PUID` and `PGID` environment variables match the user that owns the `/output` directory on your host machine. This ensures that AutoLibrarian can write to the directory and that Audiobookshelf can read the files.

### Running

1.  Create `docker-compose.yml`.
2.  Run `docker-compose up -d`.
3.  Check logs with `docker-compose logs -f`.

## Native Installation (Without Docker)

For users who prefer not to use Docker, AutoLibrarian can be run directly on a host machine.

### Prerequisites

-   Python 3.8 or higher
-   Pip (Python package installer)

### Steps

1.  **Clone the Repository**:

    ```bash
    git clone https://github.com/aerandir83/maglibrarian.git
    cd maglibrarian
    ```

2.  **Set up Virtual Environment**:

    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # macOS/Linux
    source .venv/bin/activate
    ```

3.  **Install Dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

4.  **Configuration**:

    -   Create a `.env` file from the example:
        ```bash
        cp config.env.example .env
        ```
    -   Edit the `.env` file to set your `INPUT_DIR`, `OUTPUT_DIR`, and other configuration variables. Ensure the user running the script has read/write permissions for these directories.

5.  **Run the Application**:

    ```bash
    python src/main.py
    ```

    The application will start monitoring the `INPUT_DIR` for new audiobook files.
