"""
Check Notion Database Schema
"""

import json
from notion_helper import NotionDatabaseHelper

notion = NotionDatabaseHelper()
db_info = notion.get_database_info()

if db_info:
    print("Database Name:", db_info.get('title', [{}])[0].get('plain_text', 'Unknown'))
    print("\nExisting Properties (Columns):")
    print(json.dumps(db_info.get('properties', {}), indent=2))
