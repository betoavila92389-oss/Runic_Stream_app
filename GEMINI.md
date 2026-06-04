# Runic Stream App

Runic Stream App is a desktop application built with Python and PyQt6 designed for searching, streaming, and downloading media (audio and video) from various online platforms using `yt-dlp`. It features a local library managed with SQLite to track downloaded content.

## Project Overview

- **Technologies:** Python 3.x, PyQt6 (GUI), yt-dlp (Media Extraction), SQLite (Database), FFmpeg (Post-processing).
- **Architecture:**
    - `src/main.py`: Entry point, application initialization, and global styling (QSS).
    - `src/ui/`: Package containing UI modules.
        - `src/ui/main_window.py`: Orchestrates the main application window and shared logic.
        - `src/ui/common.py`: Shared UI components (ImageLoader, PlaylistWidgetItem).
        - `src/ui/tabs/`: Individual tab implementations (Downloads, Videos, Music, Streaming).
    - `src/downloader.py`: Handles asynchronous extraction and downloading tasks using `QThread`.
    - `src/db.py`: Manages the SQLite database (`runic_stream.db`) for the media library.
    - `src/utils.py`: Helper functions for OS-specific path management.
- **Data Storage:**
    - `runic_stream.db`: SQLite database storing media metadata (title, file path, URL, quality).
    - Media files are stored in `~/Videos/RunicVideos` or `~/Music/RunicMusic` (with localized fallbacks).

## Building and Running

### Prerequisites

- Python 3.10+
- FFmpeg installed and available in the system PATH (required for media post-processing).
- A virtual environment is recommended.

### Installation

1.  **Clone the repository.**
2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Linux/macOS
    # or
    .venv\Scripts\activate     # On Windows
    ```
3.  **Install dependencies:**
    *Note: A `requirements.txt` file was not found during the initial scan. You may need to install them manually:*
    ```bash
    pip install PyQt6 yt-dlp
    ```

### Running the Application

To start the application, run:

```bash
python src/main.py
```

## Development Conventions

- **UI Framework:** Uses PyQt6. Custom styling is applied via QSS in `src/main.py`.
- **Threading:** Long-running tasks (extraction, downloading, streaming) must be performed in separate threads (see `src/downloader.py`) to keep the UI responsive.
- **Database:** Uses a singleton `DatabaseManager` instance in `src/db.py` for all library interactions.
- **File Management:** Downloaded media is automatically organized into "RunicVideos" and "RunicMusic" folders within the user's standard video/music directories.
- **Naming:** Follows standard Python `PEP 8` naming conventions (snake_case for functions/variables, PascalCase for classes).

## TODOs

- [ ] Create a `requirements.txt` file for easier dependency management.
- [ ] Implement unit tests for database and downloader logic.
- [ ] Add support for more advanced `yt-dlp` options (e.g., authentication).
