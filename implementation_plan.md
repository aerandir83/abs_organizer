# Implementation Plan - Upgrade maglibrarian

This plan incorporates the following features from `audiobook-forge`:
1.  **Merging & Conversion**: Combine multi-file audiobooks into a single `.m4b` with chapters.
2.  **Performance**: Parallel processing and hardware acceleration options.
4.  **Enhanced Metadata**: Integration with Audnexus for better data reliability.

## Proposed Changes

### 1. New Dependency: `ffmpeg`
We will assume `ffmpeg` is installed on the system.
We will add `ffmpeg-python` to `requirements.txt` to help with probing files, though `subprocess` will be used for the heavy lifting to ensure control over flags.

### 2. New Module: `src/converter.py`
This module will handle determining if conversion is needed and performing it.

**Features:**
-   **`M4BConverter` Class**:
    -   `merge_files(input_files, output_file, metadata)`: The main entry point.
    -   **Chapter Generation**: We will inspect each input file's duration using `mutagen` or `ffprobe`. We will construct a valid `FFMETADATA` file defining chapters (Chapter 1 starts at 0, ends at File1.duration, Chapter 2 starts at File1.duration, etc.).
    -   **Hardware Acceleration**: Check `config.FFMPEG_HW_ACCEL` (e.g., `auto`, `videotoolbox` (apple), `cuda`, or `none`). For audio, this is mostly about the encoder (`aac_at` vs `aac`).
    -   **Parallel Book Processing**: Implemented via a `ProcessPoolExecutor` in the main workflow if multiple books are ready.

### 3. Review & Update `src/providers.py`
-   Add `AudnexusProvider` class.
-   Audnexus is an API that scrapes/proxies Audible. It is often more reliable and easier to use than scraping Audible directly.
-   We will set it as a high-priority provider.

### 4. Integration into `src/organizer.py`
-   Modify `Organizer.organize`:
    -   Check `config.CONVERT_TO_M4B` (default: True).
    -   If True and there are multiple files (or even one), pass them to `M4BConverter`.
    -   The `M4BConverter` returns the path to the temporary M4B file.
    -   The `Organizer` then moves *that* file to the final destination instead of individual files.

### 5. Configuration Updates (`src/config.py`)
-   Add `CONVERT_TO_M4B: bool`
-   Add `FFMPEG_PATH: str` (optional)
-   Add `FFMPEG_HW_ACCEL: str`
-   Add `AUDNEXUS_URL: str`

## Step-by-Step Execution

1.  **Install/Update requirements**: Add `ffmpeg-python`.
2.  **Create `src/converter.py`**: Implement the merging and chapter logic.
3.  **Update `src/config.py`**: Add new config variables.
4.  **Update `src/providers.py`**: Add `AudnexusProvider`.
5.  **Update `src/organizer.py`**: Integrate conversion into the pipeline.
