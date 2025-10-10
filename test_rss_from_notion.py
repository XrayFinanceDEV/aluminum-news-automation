"""
Test RSS Generation from Notion
"""

import logging
from aluminum_news_automation import AluminumNewsAutomation

# Setup logging
logging.basicConfig(level=logging.INFO)

def test_rss_generation():
    """Test generating RSS feed from Notion"""
    print("Testing RSS generation from Notion...")

    try:
        automation = AluminumNewsAutomation()

        # Generate RSS feed from Notion
        automation.generate_rss_feed_from_notion()

        print("\n✅ RSS feed generated successfully from Notion!")
        print("Check: data/aluminum_news.rss")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_rss_generation()
    if not success:
        exit(1)
