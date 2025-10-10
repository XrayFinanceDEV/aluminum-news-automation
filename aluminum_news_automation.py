#!/usr/bin/env python3
"""
Aluminum News Automation
Automated news aggregation and RSS feed generation for metals industry
"""

import os
import json
import logging
import requests
import pandas as pd
from datetime import datetime, timedelta
from feedgen.feed import FeedGenerator
from typing import List, Dict, Optional
import re
from pathlib import Path
from dotenv import load_dotenv
from notion_helper import NotionDatabaseHelper

# Load environment variables from .env file
load_dotenv()

# Configuration
API_KEY = os.getenv('PERPLEXITY_API_KEY')
DATA_DIR = Path('./data')
CSV_FILE = DATA_DIR / 'aluminum_news.csv'
RSS_FILE = DATA_DIR / 'aluminum_news.rss'
LOG_FILE = DATA_DIR / 'automation.log'

# Create data directory if it doesn't exist
DATA_DIR.mkdir(exist_ok=True)

# Metal categories
METAL_CATEGORIES = {
    'aluminum': ['aluminum', 'aluminium', 'bauxite', 'alumina'],
    'steel': ['steel', 'iron ore', 'coking coal'],
    'copper': ['copper', 'cathode'],
    'nickel': ['nickel', 'laterite']
}


class AluminumNewsAutomation:
    """Main automation class for metals news aggregation"""

    def __init__(self):
        """Initialize the automation system"""
        self.logger = self.setup_logging()
        self.perplexity_api_url = "https://api.perplexity.ai/chat/completions"

        # Initialize Notion helper
        try:
            self.notion_helper = NotionDatabaseHelper()
            self.logger.info("Notion integration initialized")
        except Exception as e:
            self.logger.warning(f"Notion integration not available: {e}")
            self.notion_helper = None
    
    def setup_logging(self) -> logging.Logger:
        """Setup logging configuration"""
        logger = logging.Logger('AluminumNewsAutomation')
        logger.setLevel(logging.INFO)
        
        # File handler
        fh = logging.FileHandler(LOG_FILE)
        fh.setLevel(logging.INFO)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        logger.addHandler(fh)
        logger.addHandler(ch)
        
        return logger
    
    def get_news_from_perplexity(self, query: str, hours_back: int = 24) -> List[Dict]:
        """Fetch news articles using Perplexity API"""
        if not API_KEY:
            self.logger.error("API key not found")
            return []
        
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        
        time_range = datetime.now() - timedelta(hours=hours_back)
        prompt = f"""
Find the latest news articles about {query} from the past {hours_back} hours.
For each article, provide:
1. Title
2. Source/Publication
3. Date (if available)
4. Brief summary (2-3 sentences)
5. URL (if available)

Format the response as a JSON array with objects containing: title, source, date, summary, url
"""
        
        payload = {
            "model": "sonar",
            "messages": [
                {"role": "system", "content": "You are a news aggregation assistant. Return only valid JSON arrays."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 4000
        }
        
        try:
            response = requests.post(
                self.perplexity_api_url,
                headers=headers,
                json=payload,
                timeout=30
            )

            # Log response details for debugging
            if response.status_code != 200:
                try:
                    error_detail = response.json()
                    self.logger.error(f"Perplexity API error (status {response.status_code}): {error_detail}")
                except:
                    self.logger.error(f"Perplexity API error (status {response.status_code}): {response.text}")

            response.raise_for_status()

            result = response.json()
            content = result['choices'][0]['message']['content']

            # Extract JSON from response
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                articles = json.loads(json_match.group())

                # Add metadata
                for article in articles:
                    article['query'] = query
                    article['category'] = self.classify_news_category(article.get('title', '') + ' ' + article.get('summary', ''))
                    article['fetched_at'] = datetime.now().isoformat()

                    # Clean and validate date
                    if 'date' not in article or not article['date']:
                        article['date'] = datetime.now().isoformat()

                return articles
            else:
                self.logger.warning(f"No JSON found in response for query: {query}")
                return []

        except Exception as e:
            self.logger.error(f"Error fetching news for '{query}': {e}")
            return []
    
    def classify_news_category(self, text: str) -> str:
        """Classify news into metal categories"""
        text_lower = text.lower()
        
        for category, keywords in METAL_CATEGORIES.items():
            if any(keyword in text_lower for keyword in keywords):
                return category
        
        return 'general'
    
    def load_existing_data(self) -> pd.DataFrame:
        """Load existing news data from CSV"""
        if CSV_FILE.exists():
            try:
                df = pd.read_csv(CSV_FILE)
                self.logger.info(f"Loaded {len(df)} existing articles from {CSV_FILE}")
                return df
            except Exception as e:
                self.logger.error(f"Error loading CSV: {e}")
                return pd.DataFrame()
        else:
            self.logger.info("No existing data file found. Starting fresh.")
            return pd.DataFrame()
    
    def deduplicate_and_save(self, existing_df: pd.DataFrame, new_articles: List[Dict]) -> pd.DataFrame:
        """Deduplicate and save articles to Notion and CSV"""
        if not new_articles:
            self.logger.info("No new articles to save")
            return existing_df

        new_df = pd.DataFrame(new_articles)

        # Combine with existing data
        if not existing_df.empty:
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df

        # Deduplicate based on title and source
        combined_df = combined_df.drop_duplicates(subset=['title', 'source'], keep='first')

        # Sort by date (most recent first)
        if 'date' in combined_df.columns:
            combined_df = combined_df.sort_values('date', ascending=False)

        # Save to CSV (backup)
        combined_df.to_csv(CSV_FILE, index=False)
        self.logger.info(f"Saved {len(combined_df)} articles to {CSV_FILE}")

        # Save new articles to Notion
        if self.notion_helper:
            # Find truly new articles (not in existing_df)
            if not existing_df.empty:
                # Get titles from existing data
                existing_titles = set(existing_df['title'].values)
                articles_to_add = [
                    article for article in new_articles
                    if article['title'] not in existing_titles
                ]
            else:
                articles_to_add = new_articles

            if articles_to_add:
                self.logger.info(f"Adding {len(articles_to_add)} new articles to Notion...")
                stats = self.notion_helper.add_articles_bulk(articles_to_add)
                self.logger.info(f"Notion sync: {stats['successful']} added, {stats['failed']} failed")
            else:
                self.logger.info("No new articles to add to Notion (all duplicates)")
        else:
            self.logger.warning("Notion integration not available - articles saved to CSV only")

        return combined_df
    
    def generate_rss_feed_from_notion(self):
        """Generate RSS feed from Notion database (last 100 articles)"""
        if not self.notion_helper:
            self.logger.warning("Notion integration not available - cannot generate RSS feed")
            return

        # Fetch articles from Notion
        articles = self.notion_helper.fetch_articles(limit=100)

        if not articles:
            self.logger.warning("No articles fetched from Notion for RSS feed")
            return

        fg = FeedGenerator()
        fg.title('Metals Industry News Feed')
        fg.link(href='https://github.com/XrayFinanceDEV/aluminum-news-automation', rel='alternate')
        fg.description('Automated news feed for aluminum, steel, copper, and nickel industries')
        fg.language('en')

        # Add articles to feed
        for article in articles:
            fe = fg.add_entry()
            fe.title(article.get('title', 'No title'))
            fe.link(href=article.get('url', '#'))
            fe.description(article.get('summary', 'No summary available'))

            # Parse date
            try:
                if article.get('date'):
                    pub_date = pd.to_datetime(article['date'])
                    fe.published(pub_date)
            except:
                pass

            # Add category
            if article.get('category'):
                fe.category(term=article['category'])

        # Write RSS file
        fg.rss_file(str(RSS_FILE))
        self.logger.info(f"Generated RSS feed at {RSS_FILE} with {len(articles)} articles from Notion")
    
    def get_statistics(self, df: pd.DataFrame) -> Dict:
        """Get statistics about collected news"""
        stats = {
            'total_articles': len(df),
            'by_category': df['category'].value_counts().to_dict() if 'category' in df.columns else {},
            'sources': df['source'].nunique() if 'source' in df.columns else 0,
            'date_range': {
                'earliest': str(df['date'].min()) if 'date' in df.columns and not df.empty else None,
                'latest': str(df['date'].max()) if 'date' in df.columns and not df.empty else None
            }
        }
        return stats

    def run_automation(self):
        """Main automation workflow"""
        self.logger.info("Starting Metals News Automation")

        if not API_KEY:
            self.logger.error("PERPLEXITY_API_KEY not found in environment")
            return False

        if not self.notion_helper:
            self.logger.error("Notion integration required but not available")
            return False

        try:
            # Define search queries for different aspects
            queries = [
                # Aluminum
                "aluminum prices and market trends",
                "aluminum production and capacity",
                "aluminum technology innovation sustainability",
                # Steel
                "steel prices and market trends",
                "steel production and capacity",
                "steel technology innovation sustainability",
                # Copper
                "copper prices and market trends",
                "copper production and capacity",
                "copper technology innovation sustainability",
                # Nickel
                "nickel prices and market trends",
                "nickel production and capacity",
                "nickel technology innovation sustainability",
                # Italian companies in metals sector
                "Cogne Acciai Speciali news aluminum steel italy",
                "Tenaris news steel italy",
                "Prysmian news copper cables italy"
            ]

            all_new_articles = []

            # Fetch news for each query
            for query in queries:
                articles = self.get_news_from_perplexity(query, hours_back=24)
                count = len(articles)
                self.logger.info(f"Collected {count} articles for query: '{query}'")
                if count == 0:
                    self.logger.warning(f"Zero articles returned for query: '{query}'")
                all_new_articles.extend(articles)

                # Rate limiting
                import time
                time.sleep(2)

            # Get existing articles from Notion to check for duplicates
            self.logger.info("Fetching existing articles from Notion for duplicate check...")
            existing_articles = self.notion_helper.fetch_articles(limit=100)
            existing_titles = {article['title'] for article in existing_articles}

            # Filter out duplicates
            articles_to_add = [
                article for article in all_new_articles
                if article['title'] not in existing_titles
            ]

            self.logger.info(f"Found {len(articles_to_add)} new articles (filtered {len(all_new_articles) - len(articles_to_add)} duplicates)")

            # Save new articles to Notion
            if articles_to_add:
                stats = self.notion_helper.add_articles_bulk(articles_to_add)
                self.logger.info(f"Added {stats['successful']} new articles to Notion")
            else:
                self.logger.info("No new articles to add to Notion")

            # Optional: Save to CSV as backup
            df = pd.DataFrame(all_new_articles)
            if not df.empty:
                df.to_csv(CSV_FILE, index=False)
                self.logger.info(f"Saved {len(df)} articles to CSV backup")

            # Generate RSS feed from Notion
            self.generate_rss_feed_from_notion()

            # Log statistics from Notion
            notion_articles = self.notion_helper.fetch_articles(limit=100)
            if notion_articles:
                stats = {
                    'total_articles_in_notion': len(notion_articles),
                    'new_articles_added': len(articles_to_add),
                    'by_category': {}
                }
                # Count by category
                from collections import Counter
                category_counts = Counter([article['category'] for article in notion_articles])
                stats['by_category'] = dict(category_counts)

                self.logger.info(f"Automation completed. Statistics: {json.dumps(stats, indent=2)}")

            return True

        except Exception as e:
            self.logger.error(f"Automation failed: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False

def main():
    """Main function"""
    automation = AluminumNewsAutomation()
    success = automation.run_automation()
    
    if success:
        print("✅ Automation completed successfully")
    else:
        print("❌ Automation failed")
        exit(1)

if __name__ == "__main__":
    main()
