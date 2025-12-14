# Configuration

AutoLibrarian is configured primarily through environment variables. This makes it easy to deploy in containerized environments like Docker.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `INPUT_DIR` | The directory where AutoLibrarian watches for new files. | `/data/input` |
| `OUTPUT_DIR` | The directory where organized audiobooks will be moved. | `/data/output` |
| `ABS_URL` | The URL of your Audiobookshelf instance. | `http://localhost:8080` |
| `ABS_API_KEY` | The API key for Audiobookshelf, used to trigger scans. | *(empty)* |
| `STABILITY_CHECK_DURATION` | Time in seconds a file must remain unchanged before processing. | `60` |
| `PUID` | The User ID to assign to organized files (for permissions). | `1000` |
| `PGID` | The Group ID to assign to organized files (for permissions). | `1000` |
| `METADATA_PROVIDERS` | Comma-separated list of metadata providers to use (options: `openlibrary`, `googlebooks`, `audible`). | `openlibrary,googlebooks,audible` |
| `MATCH_THRESHOLD_AUTOMATIC` | Confidence score (0-100) required for automatic organization. (Internal config) | `90` |
| `MATCH_THRESHOLD_PROBABLE` | Confidence score (0-100) required to avoid manual intervention. (Internal config) | `70` |

## Allowed Extensions

AutoLibrarian automatically processes files with the following extensions:
- Audio: `.m4b`, `.mp3`, `.m4a`, `.flac`, `.opus`, `.wma`
- E-books: `.epub`, `.pdf`
- Images: `.jpg`, `.png`
- Archives: `.zip`, `.tar`, `.tar.gz` (automatically extracted)
