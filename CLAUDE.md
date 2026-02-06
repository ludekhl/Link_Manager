# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Link Manager is a single-file Python/Streamlit web application for managing personal link collections, backed by SQLite. Designed for self-hosted deployment on a Raspberry Pi.

## Commands

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run the app
streamlit run app.py --server.port 7000
```

There are no tests or linting configured for this project.

## Architecture

The entire application lives in `app.py` (~194 lines) with three logical layers:

1. **Data layer**: SQLite database (`links_db.sqlite`, git-ignored) with two tables:
   - `groups` (id, name UNIQUE) - link categories; "General" is the protected default group
   - `links` (id, name, url, group_name FK) - the actual links

2. **Business logic**: Standalone functions (`add_link`, `update_link`, `delete_links`, `add_group`, `rename_group`, `delete_group`, `get_links_df`, `get_all_groups`) that each open/close their own SQLite connection. Database path is resolved relative to the script via `BASE_DIR`.

3. **UI layer**: Streamlit reactive UI with sidebar (add link form, group management) and main area (search, editable data table, bulk delete). Uses `st.data_editor` with column configs for inline editing.

### Key behaviors

- **Bookmarklet integration**: The app reads `url` and `name` from `st.query_params` to pre-fill the "Add New Link" form when invoked from a browser bookmarklet.
- **Safe group deletion**: Deleting a group moves its links to "General" rather than deleting them.
- **Backup**: `backup.sh` uses rclone to copy the SQLite DB to Google Drive (`gdrive:Backups`), including dated history copies.
