# AutoLibrarian

**AutoLibrarian** is an automated audiobook organizer designed to work seamlessly with [Audiobookshelf](https://www.audiobookshelf.org/). It watches an input directory, identifies audiobooks, enriches metadata using external providers, and organizes them into a structured library.

## Features

- **Automated Monitoring**: Watches an input directory for new files.
- **Smart Ingestion**:
  - Automatically extracts `.zip`, `.tar`, and `.tar.gz` archives.
  - Groups related files together.
  - Waits for file transfers to complete before processing.
- **Intelligent Identification**:
  - Extracts metadata from embedded tags (ID3, MP4).
  - Parses filenames and directory names.
  - Merges data to get the best starting point.
- **Metadata Enrichment**:
  - Fetches details from **OpenLibrary**, **Google Books**, and **Audible**.
  - Retrieves Title, Author, Description, Year, ISBN, and Cover Art.
- **Organization**:
  - Moves files to a structured library: `Author/Series/Title` or `Author/Title`.
  - Embeds correct tags into audio files.
  - Generates `metadata.json` for Audiobookshelf.
  - Downloads cover art.
  - Handles manual intervention for low-confidence matches.
- **Integration**:
  - Triggers Audiobookshelf library scans upon completion.

## Documentation

- [Configuration](docs/configuration.md) - Environment variables and settings.
- [Architecture](docs/architecture.md) - How it works under the hood.
- [Deployment](docs/deployment.md) - Docker and installation guide.
- [Contributing](CONTRIBUTING.md) - Development guide.

## Quick Start (Docker)

1. Create a `docker-compose.yml`:

```yaml
version: "3.8"
services:
  autolibrarian:
    image: autolibrarian:latest
    build: .
    environment:
      - INPUT_DIR=/input
      - OUTPUT_DIR=/output
      - ABS_URL=http://your-abs-instance:80
      - ABS_API_KEY=your_api_key
    volumes:
      - ./input:/input
      - ./library:/output
```

2. Run the container:
   ```bash
   docker-compose up -d
   ```

3. Drop an audiobook file or folder into `./input`. AutoLibrarian will process it and move it to `./library`.

## Running Natively (Without Docker)

1.  **Prerequisites**: Ensure you have Python 3 installed on your system.
2.  **Clone the Repository**:
    ```bash
    git clone https://github.com/your-username/AutoLibrarian.git
    cd AutoLibrarian
    ```
3.  **Set up Virtual Environment**:
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # macOS/Linux
    source .venv/bin/activate
    ```
4.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
5.  **Configure**:
    - Create a `.env` file by copying the example: `cp config.env.example .env`
    - Edit the `.env` file to match your setup (e.g., `INPUT_DIR`, `OUTPUT_DIR`).
6.  **Run the Application**:
    ```bash
    python src/main.py
    ```

## License

[MIT License](LICENSE)
