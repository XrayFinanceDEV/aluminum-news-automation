"""
Test Notion Integration
"""

import logging
from notion_helper import NotionDatabaseHelper
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)

def test_notion_connection():
    """Test basic Notion connection and database access"""
    print("Testing Notion integration...")

    try:
        # Initialize Notion helper
        notion = NotionDatabaseHelper()
        print("✅ Notion client initialized successfully")

        # Get database info
        db_info = notion.get_database_info()
        if db_info:
            print(f"✅ Connected to database: {db_info.get('title', [{}])[0].get('plain_text', 'Unknown')}")

        # Test adding a sample article
        test_article = {
            'title': 'Test Article - Aluminum News Integration',
            'source': 'Test Source',
            'date': 'October 10, 2025',
            'summary': 'This is a test article to verify the Notion integration is working correctly.',
            'url': 'https://example.com/test',
            'category': 'aluminum',
            'query': 'test query',
            'fetched_at': datetime.now().isoformat()
        }

        print("\nAdding test article to Notion...")
        page_id = notion.create_article_page(test_article)

        if page_id:
            print(f"✅ Test article created successfully! Page ID: {page_id}")
            print("\n✅ Notion integration is working!")
            return True
        else:
            print("❌ Failed to create test article")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_notion_connection()
    if not success:
        exit(1)
