# 🔗 Link Manager

A lightweight, high-density link management application built with **Python**, **Streamlit**, and **SQLite**. Designed to run on a Raspberry Pi to serve as a private, searchable database for all your important web links.

## ✨ Features
* **High-Density View**: View dozens of links at once using a compact table interface.
* **Inline Editing**: Rename links or change categories directly in the table.
* **Group Management**: Create, rename, and delete groups. Links are safely moved to "General" if a group is deleted.
* **Instant Search**: Filter through hundreds of links by name or URL in real-time.
* **Bookmarklet Support**: Save links directly from Chrome with a single click.
* **Persistent Storage**: Powered by SQLite for reliable data management on your Pi.

## 🛠️ Installation

### 1. Clone the repository
```bash
git clone git@github.com:ludekhl/link_manager.git
cd link_manager
2. Setup Environment
Bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
3. Run Locally
Bash
streamlit run app.py --server.port 7000
🚀 Deployment (Raspberry Pi Systemd)
To keep the app running 24/7 as a service:

Copy the service file to systemd: sudo nano /etc/systemd/system/linkmanager.service

Paste the configuration (ensure the User and Paths match your Pi setup).

Enable and start:

Bash
sudo systemctl daemon-reload
sudo systemctl enable linkmanager.service
sudo systemctl start linkmanager.service
🔖 Chrome Bookmarklet
To save links instantly, create a new bookmark in Chrome and paste the following into the URL field (replace the IP with your Pi's IP):

JavaScript
javascript:window.open('http://10.169.196.2:7000/?url=' + encodeURIComponent(window.location.href) + '&name=' + encodeURIComponent(document.title));

> The bookmarklet points at the Pi's ZeroTier address (`10.169.196.2`) so it works from any device joined to the ZeroTier network. On the local LAN the Pi is also reachable at `192.168.0.117:7000`.
## 🔌 REST API (`api.py`)

A Flask REST API runs alongside the Streamlit UI and shares the same SQLite
database, so links created via the API appear in the UI and vice versa. It powers
the `linkmanager` MCP server (used by Claude on M3 and the Briefing Dashboard on
M2).

- **Runs on:** Pi4 (ServerL01, `10.169.196.2`), port `7001`, as `linkmanager-api.service`.
- **Auth:** every `/api/*` request needs header `X-API-Key: <LINKMANAGER_API_KEY>` (set in `.env`). `/health` is open.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness + link count (no auth) |
| GET | `/api/links?q=&group=&limit=` | List / search links (matches name OR url) |
| GET | `/api/links/<id>` | Get one link |
| POST | `/api/links` | Create link — JSON `{name, url, group}` (group auto-created) |
| PATCH | `/api/links/<id>` | Update link — any of `{name, url, group}` |
| DELETE | `/api/links/<id>` | Delete link |
| GET | `/api/groups` | List groups (categories) with link counts |
| POST | `/api/groups` | Create group — `{name}` |
| PATCH | `/api/groups/<old>` | Rename group — `{name}` (links move with it) |
| DELETE | `/api/groups/<name>` | Delete group (its links fall back to `General`) |

"Category" in everyday terms == the `group` field. `General` cannot be renamed or deleted.

## 📂 Project Structure
app.py: Main Streamlit application logic.

links_db.sqlite: Local database file (git-ignored for privacy).

requirements.txt: Python dependencies.

.streamlit/config.toml: Custom port and UI settings.

## ☁️ Backup Configuration (Google Drive)
This project uses **Rclone** for automated backups.

1. Install Rclone: `sudo apt install rclone`
2. Configure: `rclone config` (Remote name must be `gdrive`)
3. Automated via Crontab:
   - Script: `backup.sh`
   - Schedule: Daily at 02:00

Created by Ludek