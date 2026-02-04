#!/bin/bash
# Copy the DB to GDrive with a date stamp
DB_PATH="/home/ludek/link_manager/links_db.sqlite"
REMOTE_PATH="gdrive:Backups"

# Sync the main file
/usr/bin/rclone copy $DB_PATH $REMOTE_PATH

# Optional: Keep a dated version too
/usr/bin/rclone copy $DB_PATH $REMOTE_PATH/history/links_db_$(date +%Y%m%d).sqlite
