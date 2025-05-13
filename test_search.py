import json
import asyncio
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_search():
    # Load the constitution data directly
    file_path = Path("src/data/processed/constitution_final.json")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            logger.info(f"Constitution data loaded from file")
    except Exception as e:
        logger.error(f"Error loading constitution data: {e}")
        return
    
    # Search for "the national flag" in Article 9
    logger.info("Searching for 'the national flag' in Article 9")
    
    found_article_9 = False
    for chapter in data.get("chapters", []):
        if chapter["chapter_number"] == 2:  # Chapter 2 contains Article 9
            logger.info(f"Found Chapter 2: {chapter['chapter_title']}")
            for article in chapter.get("articles", []):
                if article["article_number"] == 9:
                    found_article_9 = True
                    logger.info(f"Found Article 9: {article['article_title']}")
                    logger.info(f"Article 9 has {len(article.get('clauses', []))} clauses")
                    
                    # Check all clauses
                    for clause in article.get("clauses", []):
                        logger.info(f"Checking clause {clause['clause_number']}: {clause['content']}")
                        
                        if "national flag" in clause["content"].lower():
                            logger.info(f"FOUND 'national flag' in clause {clause['clause_number']}")
                        
                        # Check sub-clauses
                        for sub_clause in clause.get("sub_clauses", []):
                            sub_id = sub_clause.get("sub_clause_id", sub_clause.get("sub_clause_letter", ""))
                            logger.info(f"Checking sub-clause {sub_id}: {sub_clause['content']}")
                            
                            if "national flag" in sub_clause["content"].lower():
                                logger.info(f"FOUND 'national flag' in sub-clause {sub_id}")
    
    if not found_article_9:
        logger.info("Article 9 NOT FOUND!")

if __name__ == "__main__":
    asyncio.run(test_search())
