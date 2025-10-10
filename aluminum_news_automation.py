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
            "model": "llama-3.1-sonar-small-128k-online",
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
        """Deduplicate and save articles to CSV"""
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
        
        # Save to CSV
        combined_df.to_csv(CSV_FILE, index=False)
        self.logger.info(f"Saved {len(combined_df)} articles to {CSV_FILE}")
        
        return combined_df
    
    def generate_rss_feed(self, df: pd.DataFrame):
        """Generate RSS feed from articles"""
        fg = FeedGenerator()
        fg.title('Metals Industry News Feed')
        fg.link(href='https://github.com/XrayFinanceDEV/aluminum-news-automation', rel='alternate')
        fg.description('Automated news feed for aluminum, steel, copper, and nickel industries')
        fg.language('en')
        
        # Add articles to feed (most recent 50)
        for _, row in df.head(50).iterrows():
            fe = fg.add_entry()
            fe.title(row.get('title', 'No title'))
            fe.link(href=row.get('url', '#'))
            fe.description(row.get('summary', 'No summary available'))
            
            # Parse date
            try:
                if pd.notna(row.get('date')):
                    pub_date = pd.to_datetime(row['date'])
                    fe.published(pub_date)
            except:
                pass
            
            # Add category
            if 'category' in row and pd.notna(row['category']):
                fe.category(term=row['category'])
        
        # Write RSS file
        fg.rss_file(str(RSS_FILE))
        self.logger.info(f"Generated RSS feed at {RSS_FILE}")
    
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
                count = len(articles)
                self.logger.info(f"Collected {count} articles for query: '{query}'")
                if count == 0:
                    self.logger.warning(f"Zero articles returned for query: '{query}'")
                all_new_articles.extend(articles)
                
                # Rate limiting
                import time
                time.sleep(2)
            
            # Process and save articles
            before_len = 0 if df.empty else len(df)
            df = self.deduplicate_and_save(df, all_new_articles)
            after_len = len(df)
            added = max(0, after_len - before_len)
            if added == 0:
                self.logger.warning("No new rows written to CSV after deduplication step")
            else:
                self.logger.info(f"Added {added} new rows to CSV database")
            
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
    else:
        print("❌ Automation failed")
        exit(1)

if __name__ == "__main__":
    main()
