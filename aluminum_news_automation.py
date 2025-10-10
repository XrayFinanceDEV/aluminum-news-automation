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
