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
javascript:window.open('[http://192.168.0.117:7000/?url=](http://192.168.0.117:7000/?url=)' + encodeURIComponent(window.location.href) + '&name=' + encodeURIComponent(document.title));
📂 Project Structure
app.py: Main Streamlit application logic.

links_db.sqlite: Local database file (git-ignored for privacy).

requirements.txt: Python dependencies.

.streamlit/config.toml: Custom port and UI settings.

Created by Ludek