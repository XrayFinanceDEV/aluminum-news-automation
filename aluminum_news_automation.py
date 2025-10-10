#!/usr/bin/env python3
"""
Metals News Automation
Automatically fetch and generate RSS feed for metals industry news (aluminum, steel, copper, nickel) using Perplexity API
Modules required: requests, pandas, feedgen, python-dotenv, pytz, beautifulsoup4
"""
import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict
import pytz
# Third-party imports
try:
    import requests
    import pandas as pd
    from feedgen.feed import FeedGenerator
    from dotenv import load_dotenv
    from bs4 import BeautifulSoup  # noqa: F401 (kept for potential future parsing)
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
    'prices': ['price', 'cost', 'trading', 'market', 'exchange', 'futures', 'commodity', 'benchmark', 'lme'],
    'production': ['production', 'output', 'capacity', 'plant', 'smelter', 'refinery', 'mill', 'foundry'],
    'supply_chain': ['supply', 'demand', 'inventory', 'logistics', 'transport', 'shipping', 'port', 'warehouse'],
    'technology': ['technology', 'innovation', 'research', 'development', 'patent', 'sustainability', 'decarbonization', 'hydrogen', 'electrification'],
    'mergers': ['merger', 'acquisition', 'partnership', 'joint venture', 'deal', 'investment', 'funding'],
    'regulation': ['regulation', 'policy', 'government', 'trade', 'tariff', 'sanction', 'duties', 'quota'],
    'general': []
}
# Metals and Italian companies dictionaries for tagging
METALS = ['aluminum', 'aluminium', 'steel', 'copper', 'nickel']
VALUE_CHAIN = {
    'cat:prices': NEWS_CATEGORIES['prices'],
    'cat:production': NEWS_CATEGORIES['production'],
    'cat:supply_chain': NEWS_CATEGORIES['supply_chain'],
    'cat:technology': NEWS_CATEGORIES['technology'],
    'cat:mergers': NEWS_CATEGORIES['mergers'],
    'cat:regulation': NEWS_CATEGORIES['regulation']
}
ITALIAN_COMPANIES = {
    'Cogne': ['cogne', 'cogne acciai speciali'],
    'Tenaris': ['tenaris'],
    'Prysmian': ['prysmian'],
    'Enel X': ['enel x', 'enelx', 'enel x way', 'enel'],
    'Italbronze': ['italbronze', 'ital bronze'],
    'Acciai Speciali Terni': ['acciai speciali terni', 'ast terni', 'ast', 'acciaierie terni'],
    'Arvedi': ['arvedi'],
    'Danieli': ['danieli'],
    "Ilva/Acciaierie d'Italia": ["ilva", "acciaierie d'italia", 'adi'],
    'Feralpi': ['feralpi'],
    'KME': ['kme', 'kme italy'],
    'Alcoa Italia': ['alcoa italia', 'alcoa italy']
}
class AluminumNewsAutomation:
    """Main class for metals news automation"""
    
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
        
        messages = [
            {
                "role": "user",
                "content": (
                    f"Find recent metals industry news from the last {hours_back} hours about {query}. "
                    f"Include title, summary, source, publication date, and URL for each article. "
                    f"Format as JSON with fields: title, summary, source, date, url, relevance_score"
                )
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
    
    def auto_tags(self, title: str, summary: str) -> List[str]:
        """Assign automatic tags: company, metal, value chain category"""
        text = f"{title} {summary}".lower()
        tags = set()
        # Metal tags
        for m in METALS:
            if m in text:
                # normalize aluminium to aluminum
                metal_norm = 'aluminum' if m in ['aluminium', 'aluminum'] else m
                tags.add(f"metallo:{metal_norm}")
        # Company tags
        for company, patterns in ITALIAN_COMPANIES.items():
            for p in patterns:
                if p in text:
                    tags.add(f"azienda:{company}")
                    break
        # Value chain tags via keywords
        for cat_tag, keywords in VALUE_CHAIN.items():
            if any(k in text for k in keywords):
                tags.add(cat_tag)
        return sorted(tags)
    
    def load_existing_data(self) -> pd.DataFrame:
        """Load existing CSV database or create new one"""
        columns = ['id', 'title', 'summary', 'source', 'date', 'url', 'category', 'relevance_score', 'created_at', 'tags']
        
        if os.path.exists(CSV_FILE):
            try:
                df = pd.read_csv(CSV_FILE)
                # Backward compatibility: ensure tags column exists
                if 'tags' not in df.columns:
                    df['tags'] = ''
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
            # Compute tags
            tags_list = self.auto_tags(article.get('title', ''), article.get('summary', ''))
            tags_str = ';'.join(tags_list)
            
            new_row = {
                'id': article_id,
                'title': article.get('title', ''),
                'summary': article.get('summary', ''),
                'source': article.get('source', ''),
                'date': article.get('date', datetime.now(TIMEZONE).isoformat()),
                'url': article.get('url', ''),
                'category': category,
                'relevance_score': article.get('relevance_score', 50),
                'created_at': datetime.now(TIMEZONE).isoformat(),
                'tags': tags_str,
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
        fg.title('Metals Industry News')
        fg.link(href='https://github.com/XrayFinanceDEV/aluminum-news-automation')
        fg.description('Automated news feed for metals industry updates (Al, Fe, Cu, Ni)')
        fg.language('en')
        fg.lastBuildDate(datetime.now(TIMEZONE))
        fg.generator('Metals News Automation')
        
        # Add items (limit to most recent 50 for RSS performance)
        recent_articles = df.head(50)
        
        for _, row in recent_articles.iterrows():
            fe = fg.add_entry()
            fe.id(str(row['id']))
            fe.title(row['title'])
            # Include tags in description footer
            description = row['summary'] if pd.notna(row['summary']) else ''
            if 'tags' in row and pd.notna(row['tags']) and str(row['tags']).strip():
                description += f"\n\nTags: {row['tags']}"
            fe.description(description)
            fe.link(href=row['url'] if pd.notna(row['url']) else '')
            if pd.notna(row['source']) and str(row['source']).strip():
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
        self.logger.info("Starting Metals News Automation")
        
        if not API_KEY:
            self.logger.error("PERPLEXITY_API_KEY not found in environment")
            return False
        
        try:
            # Load existing data
            df = self.load_existing_data()
            
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
                "Prysmian news copper cables italy",
                "Enel X news energy storage metals italy",
                "Italbronze news bronze copper italy",
                "Acciai Speciali Terni news steel italy",
                "Arvedi news steel italy",
                "Danieli news steel plants italy",
                "Ilva Acciaierie d'Italia news steel italy",
                "KME Italy news copper italy"
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
   
