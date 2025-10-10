#!/usr/bin/env python3
"""
Aluminum News Automation
Automatically fetch and generate RSS feed for aluminum industry news using Perplexity API

Modules required: requests, pandas, feedgen, python-dotenv, pytz, beautifulsoup4
"""

import os
import sys
import json
import logging
import csv
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pytz

# Third-party imports
try:
    import requests
    import pandas as pd
    from feedgen.feed import FeedGenerator
    from dotenv import load_dotenv
    from bs4 import BeautifulSoup
except ImportError as e:
    print(f"Missing required module: {e}")
    print("Install with: pip install requests pandas feedgen python-dotenv pytz beautifulsoup4")
    sys.exit(1)

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv('PERPLEXITY_API_KEY')
API_URL = 'https://api.perplexity.ai/chat/completions'
CSV_FILE = 'data/aluminum_news_database.csv'
RSS_FILE = 'data/aluminum_news_feed.xml'
LOG_FILE = 'data/automation.log'
MAX_RECORDS = 500
TIMEZONE = pytz.timezone('UTC')

# Categories for classification
NEWS_CATEGORIES = {
    'prices': ['price', 'cost', 'trading', 'market', 'exchange', 'futures', 'commodity'],
    'production': ['production', 'output', 'capacity', 'plant', 'smelter', 'refinery'],
    'supply_chain': ['supply', 'demand', 'inventory', 'logistics', 'transport', 'shipping'],
    'technology': ['technology', 'innovation', 'research', 'development', 'patent', 'sustainability'],
    'mergers': ['merger', 'acquisition', 'partnership', 'joint venture', 'deal', 'investment'],
    'regulation': ['regulation', 'policy', 'government', 'trade', 'tariff', 'sanction'],
    'general': []
}

class AluminumNewsAutomation:
    """Main class for aluminum news automation"""
    
    def __init__(self):
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {API_KEY}',
            'Content-Type': 'application/json'
        })
        
        # Create data directory
        os.makedirs('data', exist_ok=True)
        
    def setup_logging(self):
        """Configure logging system"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(LOG_FILE),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def get_news_from_perplexity(self, query: str, hours_back: int = 24) -> List[Dict]:
        """Fetch news from Perplexity API with time filtering"""
        self.logger.info(f"Fetching news for query: {query}")
        
        # Calculate time window
        now = datetime.now(TIMEZONE)
        time_filter = now - timedelta(hours=hours_back)
        
        messages = [
            {
                "role": "user",
                "content": f"Find recent aluminum industry news from the last {hours_back} hours about {query}. "
                          f"Include title, summary, source, publication date, and URL for each article. "
                          f"Format as JSON with fields: title, summary, source, date, url, relevance_score"
            }
        ]
        
        payload = {
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": messages,
            "max_tokens": 2000,
            "temperature": 0.2
        }
        
        try:
            response = self.session.post(API_URL, json=payload)
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Try to extract JSON from response
            try:
                news_data = json.loads(content)
                if isinstance(news_data, list):
                    return news_data
                elif isinstance(news_data, dict) and 'articles' in news_data:
                    return news_data['articles']
            except json.JSONDecodeError:
                self.logger.warning("Could not parse JSON from API response")
                return []
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {e}")
            return []
        
        return []
    
    def classify_news_category(self, title: str, summary: str) -> str:
        """Automatically classify news into categories"""
        text = f"{title} {summary}".lower()
        
        category_scores = {}
        for category, keywords in NEWS_CATEGORIES.items():
            if category == 'general':
                continue
            score = sum(1 for keyword in keywords if keyword in text)
            if score > 0:
                category_scores[category] = score
        
        if category_scores:
            return max(category_scores.keys(), key=category_scores.get)
        return 'general'
    
    def load_existing_data(self) -> pd.DataFrame:
        """Load existing CSV database or create new one"""
        columns = ['id', 'title', 'summary', 'source', 'date', 'url', 'category', 'relevance_score', 'created_at']
        
        if os.path.exists(CSV_FILE):
            try:
                df = pd.read_csv(CSV_FILE)
                self.logger.info(f"Loaded {len(df)} existing records")
                return df
            except Exception as e:
                self.logger.error(f"Error loading CSV: {e}")
        
        # Create empty DataFrame with proper columns
        df = pd.DataFrame(columns=columns)
        return df
    
    def deduplicate_and_save(self, df: pd.DataFrame, new_articles: List[Dict]) -> pd.DataFrame:
        """Add new articles, deduplicate, and maintain record limit"""
        new_rows = []
        
        for article in new_articles:
            # Create unique ID based on title and source
            article_id = hash(f"{article.get('title', '')}{article.get('source', '')}")
            
            # Skip if already exists
            if not df.empty and article_id in df['id'].values:
                continue
                
            category = self.classify_news_category(
                article.get('title', ''), 
                article.get('summary', '')
            )
            
            new_row = {
                'id': article_id,
                'title': article.get('title', ''),
                'summary': article.get('summary', ''),
                'source': article.get('source', ''),
                'date': article.get('date', datetime.now(TIMEZONE).isoformat()),
                'url': article.get('url', ''),
                'category': category,
                'relevance_score': article.get('relevance_score', 50),
                'created_at': datetime.now(TIMEZONE).isoformat()
            }
            new_rows.append(new_row)
        
        if new_rows:
            # Add new rows
            df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
            
            # Convert date column to datetime for sorting
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            
            # Sort by date descending and keep only latest records
            df = df.sort_values('date', ascending=False)
            df = df.head(MAX_RECORDS)
            
            # Save to CSV
            df.to_csv(CSV_FILE, index=False)
            self.logger.info(f"Saved {len(new_rows)} new articles. Total: {len(df)}")
        
        return df
    
    def generate_rss_feed(self, df: pd.DataFrame):
        """Generate RSS 2.0 feed from DataFrame"""
        self.logger.info("Generating RSS feed")
        
        # Create feed generator
        fg = FeedGenerator()
        fg.title('Aluminum Industry News')
        fg.link(href='https://github.com/XrayFinanceDEV/aluminum-news-automation')
        fg.description('Automated news feed for aluminum industry updates')
        fg.language('en')
        fg.lastBuildDate(datetime.now(TIMEZONE))
        fg.generator('Aluminum News Automation')
        
        # Add items (limit to most recent 50 for RSS performance)
        recent_articles = df.head(50)
        
        for _, row in recent_articles.iterrows():
            fe = fg.add_entry()
            fe.id(str(row['id']))
            fe.title(row['title'])
            fe.description(row['summary'])
            fe.link(href=row['url'] if pd.notna(row['url']) else '')
            fe.author({'name': row['source']})
            
            # Handle date conversion
            try:
                if pd.notna(row['date']):
                    pub_date = pd.to_datetime(row['date'])
                    if pub_date.tzinfo is None:
                        pub_date = TIMEZONE.localize(pub_date)
                    fe.pubDate(pub_date)
            except Exception as e:
                self.logger.warning(f"Date parsing error: {e}")
            
            # Add category
            if pd.notna(row['category']):
                fe.category(term=row['category'])
        
        # Generate RSS XML
        rss_xml = fg.rss_str(pretty=True)
        
        # Save to file
        with open(RSS_FILE, 'wb') as f:
            f.write(rss_xml)
        
        self.logger.info(f"RSS feed generated with {len(recent_articles)} items")
    
    def get_statistics(self, df: pd.DataFrame) -> Dict:
        """Generate execution statistics"""
        stats = {
            'total_articles': len(df),
            'categories': df['category'].value_counts().to_dict() if not df.empty else {},
            'last_update': datetime.now(TIMEZONE).isoformat(),
            'sources': df['source'].value_counts().head(10).to_dict() if not df.empty else {}
        }
        
        # Articles in last 24 hours
        if not df.empty:
            last_24h = datetime.now(TIMEZONE) - timedelta(hours=24)
            recent = df[pd.to_datetime(df['date']) > last_24h]
            stats['articles_last_24h'] = len(recent)
            
        return stats
    
    def run_automation(self):
        """Main automation workflow"""
        self.logger.info("Starting Aluminum News Automation")
        
        if not API_KEY:
            self.logger.error("PERPLEXITY_API_KEY not found in environment")
            return False
        
        try:
            # Load existing data
            df = self.load_existing_data()
            
            # Define search queries for different aspects
            queries = [
                "aluminum prices and market trends",
                "aluminum production and capacity",
                "aluminum supply chain and logistics",
                "aluminum technology and sustainability",
                "aluminum industry mergers and acquisitions"
            ]
            
            all_new_articles = []
            
            # Fetch news for each query
            for query in queries:
                articles = self.get_news_from_perplexity(query, hours_back=24)
                all_new_articles.extend(articles)
                
                # Rate limiting
                import time
                time.sleep(2)
            
            # Process and save articles
            df = self.deduplicate_and_save(df, all_new_articles)
            
            # Generate RSS feed
            if not df.empty:
                self.generate_rss_feed(df)
            
            # Log statistics
            stats = self.get_statistics(df)
            self.logger.info(f"Automation completed. Statistics: {json.dumps(stats, indent=2)}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Automation failed: {e}")
            return False

def main():
    """Main function"""
    automation = AluminumNewsAutomation()
    success = automation.run_automation()
    
    if success:
        print("✅ Automation completed successfully")
        sys.exit(0)
    else:
        print("❌ Automation failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
