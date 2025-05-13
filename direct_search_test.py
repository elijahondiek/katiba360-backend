import json
import sys
from pathlib import Path

def main():
    # Load the constitution data directly
    file_path = Path("src/data/processed/constitution_final.json")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            print("Constitution data loaded from file")
    except Exception as e:
        print(f"Error loading constitution data: {e}")
        return
    
    # Search for "the national flag" in Article 9
    print("Searching for 'the national flag' in Article 9")
    
    results = []
    found_article_9 = False
    
    for chapter in data.get("chapters", []):
        if chapter["chapter_number"] == 2:  # Chapter 2 contains Article 9
            print(f"Found Chapter 2: {chapter['chapter_title']}")
            for article in chapter.get("articles", []):
                if article["article_number"] == 9:
                    found_article_9 = True
                    print(f"Found Article 9: {article['article_title']}")
                    print(f"Article 9 has {len(article.get('clauses', []))} clauses")
                    
                    # Check all clauses
                    for clause in article.get("clauses", []):
                        print(f"Checking clause {clause['clause_number']}: {clause['content']}")
                        
                        if "national flag" in clause["content"].lower():
                            print(f"FOUND 'national flag' in clause {clause['clause_number']}")
                            results.append({
                                "type": "clause",
                                "chapter_number": chapter["chapter_number"],
                                "chapter_title": chapter["chapter_title"],
                                "article_number": article["article_number"],
                                "article_title": article["article_title"],
                                "clause_number": clause["clause_number"],
                                "content": clause["content"]
                            })
                        
                        # Check sub-clauses
                        for sub_clause in clause.get("sub_clauses", []):
                            sub_id = sub_clause.get("sub_clause_id", sub_clause.get("sub_clause_letter", ""))
                            print(f"Checking sub-clause {sub_id}: {sub_clause['content']}")
                            
                            if "national flag" in sub_clause["content"].lower():
                                print(f"FOUND 'national flag' in sub-clause {sub_id}")
                                results.append({
                                    "type": "sub_clause",
                                    "chapter_number": chapter["chapter_number"],
                                    "chapter_title": chapter["chapter_title"],
                                    "article_number": article["article_number"],
                                    "article_title": article["article_title"],
                                    "clause_number": clause["clause_number"],
                                    "sub_clause_letter": sub_id,
                                    "content": sub_clause["content"]
                                })
    
    if not found_article_9:
        print("Article 9 NOT FOUND!")
    
    # Also search in preamble
    preamble = data.get("preamble", "")
    if "national flag" in preamble.lower():
        print("FOUND 'national flag' in preamble")
        results.append({
            "type": "preamble",
            "content": preamble
        })
    
    # Print results
    print("\nSearch Results:")
    print(f"Found {len(results)} matches for 'the national flag'")
    for i, result in enumerate(results, 1):
        print(f"\nResult {i}:")
        print(f"Type: {result['type']}")
        if result['type'] == 'preamble':
            print("Location: Preamble")
        else:
            print(f"Location: Chapter {result['chapter_number']}, Article {result['article_number']}")
            if result['type'] == 'sub_clause':
                print(f"Clause {result['clause_number']}, Sub-clause {result['sub_clause_letter']}")
            elif result['type'] == 'clause':
                print(f"Clause {result['clause_number']}")
        
        # Print a snippet of the content
        content = result['content']
        if len(content) > 100:
            content = content[:100] + "..."
        print(f"Content: {content}")

if __name__ == "__main__":
    main()
