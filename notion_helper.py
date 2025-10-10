"""
Notion Database Helper for Aluminum News Automation
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Optional
from notion_client import Client
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()


class NotionDatabaseHelper:
    """Helper class to interact with Notion database for news articles"""

    def __init__(self):
        """Initialize Notion client"""
        self.logger = logging.getLogger(self.__class__.__name__)

        # Get credentials from environment
        self.api_key = os.getenv('NOTION_API_KEY')
        self.database_id = os.getenv('NOTION_DATABASE_ID')

        if not self.api_key or self.api_key == "YOUR_NOTION_INTEGRATION_TOKEN_HERE":
            raise ValueError("NOTION_API_KEY not found or not set in .env file")

        if not self.database_id:
            raise ValueError("NOTION_DATABASE_ID not found in .env file")

        # Initialize Notion client
        self.client = Client(auth=self.api_key)
        self.logger.info("Notion client initialized successfully")

    def parse_date_to_iso(self, date_str: str) -> str:
        """
        Parse various date formats to ISO 8601 (YYYY-MM-DD)

        Args:
            date_str: Date string in various formats

        Returns:
            ISO 8601 formatted date string
        """
        if not date_str:
            return datetime.now().strftime('%Y-%m-%d')

        try:
            # Try parsing common formats
            formats = [
                '%Y-%m-%d',  # 2025-10-10
                '%B %d, %Y',  # October 10, 2025
                '%b %d, %Y',  # Oct 10, 2025
                '%Y/%m/%d',  # 2025/10/10
                '%d/%m/%Y',  # 10/10/2025
                '%m/%d/%Y',  # 10/10/2025
            ]

            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str.strip(), fmt)
                    return dt.strftime('%Y-%m-%d')
                except ValueError:
                    continue

            # If nothing matches, try to extract year and use current date
            year_match = re.search(r'(\d{4})', date_str)
            if year_match:
                year = year_match.group(1)
                return f"{year}-01-01"  # Default to January 1st of that year

            # Fallback to current date
            return datetime.now().strftime('%Y-%m-%d')

        except Exception as e:
            self.logger.warning(f"Could not parse date '{date_str}': {e}, using current date")
            return datetime.now().strftime('%Y-%m-%d')

    def create_article_page(self, article: Dict) -> Optional[str]:
        """
        Create a new page in the Notion database for an article

        Args:
            article: Dictionary containing article data with keys:
                    - title: str
                    - source: str
                    - date: str
                    - summary: str
                    - url: str
                    - category: str
                    - query: str
                    - fetched_at: str (ISO format datetime)

        Returns:
            Page ID if successful, None otherwise
        """
        try:
            # Map category from English to Italian
            category_map = {
                'aluminum': 'Alluminio',
                'steel': 'Acciaio',
                'copper': 'Rame',
                'nickel': 'Nichel',
                'general': 'Big Player Internazionali'
            }

            category_it = category_map.get(article.get('category', 'general'), 'Big Player Internazionali')

            # Parse date to ISO format
            date_iso = self.parse_date_to_iso(article.get('date', ''))

            # Prepare properties for Notion page (using Italian column names)
            properties = {
                "Titolo": {
                    "title": [
                        {
                            "text": {
                                "content": article.get('title', 'Untitled')[:2000]  # Notion limit
                            }
                        }
                    ]
                },
                "Fonte/link": {
                    "url": article.get('url', '')
                },
                "Data": {
                    "date": {
                        "start": date_iso
                    }
                },
                "Breve estratto/sommario": {
                    "rich_text": [
                        {
                            "text": {
                                "content": article.get('summary', '')[:2000]
                            }
                        }
                    ]
                },
                "Argomento/Categoria": {
                    "multi_select": [
                        {"name": category_it}
                    ]
                }
            }

            # Create the page
            response = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )

            page_id = response.get('id')
            self.logger.info(f"Created Notion page for: {article.get('title', 'Untitled')[:50]}...")
            return page_id

        except Exception as e:
            self.logger.error(f"Error creating Notion page for {article.get('title', 'Unknown')}: {e}")
            return None

    def add_articles_bulk(self, articles: List[Dict]) -> Dict:
        """
        Add multiple articles to the Notion database

        Args:
            articles: List of article dictionaries

        Returns:
            Dictionary with statistics: total, successful, failed
        """
        stats = {
            'total': len(articles),
            'successful': 0,
            'failed': 0,
            'page_ids': []
        }

        self.logger.info(f"Adding {len(articles)} articles to Notion database...")

        for article in articles:
            page_id = self.create_article_page(article)
            if page_id:
                stats['successful'] += 1
                stats['page_ids'].append(page_id)
            else:
                stats['failed'] += 1

        self.logger.info(f"Notion sync complete: {stats['successful']} successful, {stats['failed']} failed")
        return stats

    def check_article_exists(self, title: str, url: str) -> bool:
        """
        Check if an article already exists in the database

        Args:
            title: Article title
            url: Article URL

        Returns:
            True if article exists, False otherwise
        """
        try:
            # Search by URL (more reliable than title)
            response = self.client.databases.query(
                database_id=self.database_id,
                filter={
                    "property": "Fonte/link",
                    "url": {
                        "equals": url
                    }
                }
            )

            return len(response.get('results', [])) > 0

        except Exception as e:
            self.logger.error(f"Error checking if article exists: {e}")
            return False

    def get_database_info(self) -> Optional[Dict]:
        """
        Get information about the database structure

        Returns:
            Database metadata or None if error
        """
        try:
            response = self.client.databases.retrieve(database_id=self.database_id)
            return response
        except Exception as e:
            self.logger.error(f"Error retrieving database info: {e}")
            return None

    def fetch_articles(self, limit: int = 100) -> List[Dict]:
        """
        Fetch the last N articles from Notion database, sorted by date

        Args:
            limit: Maximum number of articles to fetch (default: 100)

        Returns:
            List of article dictionaries
        """
        try:
            self.logger.info(f"Fetching last {limit} articles from Notion...")

            # Query database sorted by date (most recent first)
            response = self.client.databases.query(
                database_id=self.database_id,
                sorts=[
                    {
                        "property": "Data",
                        "direction": "descending"
                    }
                ],
                page_size=min(limit, 100)  # Notion API limit is 100 per page
            )

            articles = []

            for page in response.get('results', []):
                try:
                    properties = page.get('properties', {})

                    # Extract title
                    title_prop = properties.get('Titolo', {})
                    title = ''
                    if title_prop.get('title'):
                        title = title_prop['title'][0].get('text', {}).get('content', '')

                    # Extract URL
                    url = properties.get('Fonte/link', {}).get('url', '')

                    # Extract date
                    date_prop = properties.get('Data', {}).get('date', {})
                    date = date_prop.get('start', '') if date_prop else ''

                    # Extract summary
                    summary_prop = properties.get('Breve estratto/sommario', {})
                    summary = ''
                    if summary_prop.get('rich_text'):
                        summary = summary_prop['rich_text'][0].get('text', {}).get('content', '')

                    # Extract category (multi-select, take first one)
                    category_prop = properties.get('Argomento/Categoria', {})
                    category = ''
                    if category_prop.get('multi_select'):
                        category = category_prop['multi_select'][0].get('name', '')

                    # Map Italian category back to English for RSS
                    category_map_reverse = {
                        'Alluminio': 'aluminum',
                        'Acciaio': 'steel',
                        'Rame': 'copper',
                        'Nichel': 'nickel',
                        'Big Player Internazionali': 'general',
                        'Big Player Italiani': 'general'
                    }
                    category_en = category_map_reverse.get(category, 'general')

                    article = {
                        'title': title,
                        'url': url,
                        'date': date,
                        'summary': summary,
                        'category': category_en
                    }

                    articles.append(article)

                except Exception as e:
                    self.logger.warning(f"Error parsing article from Notion page: {e}")
                    continue

            self.logger.info(f"Successfully fetched {len(articles)} articles from Notion")
            return articles

        except Exception as e:
            self.logger.error(f"Error fetching articles from Notion: {e}")
            return []
