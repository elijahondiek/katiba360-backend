import json
import os
from bs4 import BeautifulSoup
import re
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_chapters_from_html(html_file_path):
    """Extract chapters 14, 16, 17, and 18 from the HTML source file."""
    logger.info(f"Reading HTML file from {html_file_path}")
    
    with open(html_file_path, 'r', encoding='utf-8') as file:
        html_content = file.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find chapters 14, 16, 17, and 18
    chapter_14 = soup.find('section', {'id': 'chp_Fourteen'})
    chapter_16 = soup.find('section', {'id': 'chp_Sixteen'})
    chapter_17 = soup.find('section', {'id': 'chp_Seventeen'})
    chapter_18 = soup.find('section', {'id': 'chp_Eighteen'})
    
    chapters_data = []
    
    # Process Chapter 14 (with parts)
    if chapter_14:
        logger.info("Processing Chapter 14")
        chapter_14_data = process_chapter_with_parts(chapter_14, 14, "National Security")
        chapters_data.append(chapter_14_data)
    else:
        logger.warning("Chapter 14 not found in HTML")
    
    # Process Chapter 16
    if chapter_16:
        logger.info("Processing Chapter 16")
        chapter_16_data = process_chapter(chapter_16, 16, "Amendment of this Constitution")
        chapters_data.append(chapter_16_data)
    else:
        logger.warning("Chapter 16 not found in HTML")
    
    # Process Chapter 17
    if chapter_17:
        logger.info("Processing Chapter 17")
        chapter_17_data = process_chapter(chapter_17, 17, "General Provisions")
        chapters_data.append(chapter_17_data)
    else:
        logger.warning("Chapter 17 not found in HTML")
    
    # Process Chapter 18
    if chapter_18:
        logger.info("Processing Chapter 18")
        chapter_18_data = process_chapter(chapter_18, 18, "Transitional and Consequential Provisions")
        chapters_data.append(chapter_18_data)
    else:
        logger.warning("Chapter 18 not found in HTML")
    
    return chapters_data

def process_chapter_with_parts(chapter_element, chapter_number, chapter_title):
    """Process a chapter element with parts and extract its articles."""
    chapter_data = {
        "chapter_number": chapter_number,
        "chapter_title": chapter_title,
        "articles": [],
        "parts": []
    }
    
    # Find all part sections within the chapter
    part_sections = chapter_element.find_all('section', {'class': 'akn-part'})
    
    for part_section in part_sections:
        part_data = process_part(part_section)
        if part_data:
            chapter_data["parts"].append(part_data)
    
    return chapter_data

def process_part(part_element):
    """Process a part element and extract its articles."""
    # Extract part number and title from the h2 tag
    h2_tag = part_element.find('h2')
    if not h2_tag:
        return None
    
    part_text = h2_tag.text.strip()
    match = re.match(r'Part\s+(\d+)\s+[–-]\s+(.*)', part_text)
    
    if not match:
        return None
    
    part_number = int(match.group(1))
    part_title = match.group(2).strip()
    
    part_data = {
        "part_number": part_number,
        "part_title": part_title,
        "articles": []
    }
    
    # Find all article sections within the part
    article_sections = part_element.find_all('section', {'class': 'akn-section'})
    
    for article_section in article_sections:
        article_data = process_article(article_section)
        if article_data:
            part_data["articles"].append(article_data)
    
    return part_data

def process_chapter(chapter_element, chapter_number, chapter_title):
    """Process a chapter element and extract its articles."""
    chapter_data = {
        "chapter_number": chapter_number,
        "chapter_title": chapter_title,
        "articles": [],
        "parts": []
    }
    
    # Find all article sections within the chapter
    article_sections = chapter_element.find_all('section', {'class': 'akn-section'})
    
    for article_section in article_sections:
        article_data = process_article(article_section)
        if article_data:
            chapter_data["articles"].append(article_data)
    
    return chapter_data

def process_article(article_element):
    """Process an article element and extract its clauses."""
    # Extract article number and title from the h3 tag
    h3_tag = article_element.find('h3')
    if not h3_tag:
        return None
    
    article_text = h3_tag.text.strip()
    match = re.match(r'(\d+)\.\s+(.*)', article_text)
    
    if not match:
        return None
    
    article_number = int(match.group(1))
    article_title = match.group(2).strip()
    
    article_data = {
        "article_number": article_number,
        "article_title": article_title,
        "clauses": []
    }
    
    # Find all subsections (clauses) within the article
    subsections = article_element.find_all('section', {'class': 'akn-subsection'})
    
    # If there are subsections, process them as clauses
    if subsections:
        for subsection in subsections:
            clause_data = process_clause(subsection)
            if clause_data:
                article_data["clauses"].append(clause_data)
    else:
        # Handle articles with direct content (no subsections)
        content_tag = article_element.find('span', {'class': 'akn-content'})
        if content_tag and content_tag.find('span', {'class': 'akn-p'}):
            content = content_tag.find('span', {'class': 'akn-p'}).text.strip()
            # Create a single clause with the content
            article_data["clauses"].append({
                "clause_number": 1,
                "content": content,
                "sub_clauses": []
            })
        # Handle articles with intro and paragraphs but no subsections
        elif article_element.find('span', {'class': 'akn-intro'}):
            intro_tag = article_element.find('span', {'class': 'akn-intro'})
            if intro_tag and intro_tag.find('span', {'class': 'akn-p'}):
                content = intro_tag.find('span', {'class': 'akn-p'}).text.strip()
                # Create a single clause with the intro content
                article_data["clauses"].append({
                    "clause_number": 1,
                    "content": content,
                    "sub_clauses": []
                })
            
            # Process paragraphs as sub-clauses
            paragraphs = article_element.find_all('section', {'class': 'akn-paragraph'})
            if paragraphs:
                for paragraph in paragraphs:
                    sub_clause_data = process_sub_clause(paragraph)
                    if sub_clause_data and len(article_data["clauses"]) > 0:
                        article_data["clauses"][0]["sub_clauses"].append(sub_clause_data)
    
    return article_data

def process_clause(clause_element):
    """Process a clause element and extract its content and sub-clauses."""
    # Extract clause number
    num_tag = clause_element.find('span', {'class': 'akn-num'})
    if not num_tag:
        return None
    
    clause_number_text = num_tag.text.strip()
    match = re.match(r'\((\d+)\)', clause_number_text)
    
    if not match:
        return None
    
    clause_number = int(match.group(1))
    
    # Extract clause content
    content_tag = clause_element.find('span', {'class': 'akn-content'})
    intro_tag = clause_element.find('span', {'class': 'akn-intro'})
    
    content = ""
    if content_tag and content_tag.find('span', {'class': 'akn-p'}):
        content = content_tag.find('span', {'class': 'akn-p'}).text.strip()
    elif intro_tag and intro_tag.find('span', {'class': 'akn-p'}):
        content = intro_tag.find('span', {'class': 'akn-p'}).text.strip()
    
    clause_data = {
        "clause_number": clause_number,
        "content": content,
        "sub_clauses": []
    }
    
    # Find all paragraphs (sub-clauses) within the clause
    paragraphs = clause_element.find_all('section', {'class': 'akn-paragraph'})
    
    for paragraph in paragraphs:
        sub_clause_data = process_sub_clause(paragraph)
        if sub_clause_data:
            clause_data["sub_clauses"].append(sub_clause_data)
    
    return clause_data

def process_sub_clause(sub_clause_element):
    """Process a sub-clause element and extract its content."""
    # Extract sub-clause letter
    num_tag = sub_clause_element.find('span', {'class': 'akn-num'})
    if not num_tag:
        return None
    
    sub_clause_letter_text = num_tag.text.strip()
    match = re.match(r'\(([a-z])\)', sub_clause_letter_text)
    
    if not match:
        return None
    
    sub_clause_letter = match.group(1)
    
    # Extract sub-clause content
    content_tag = sub_clause_element.find('span', {'class': 'akn-content'})
    if not content_tag or not content_tag.find('span', {'class': 'akn-p'}):
        return None
    
    content = content_tag.find('span', {'class': 'akn-p'}).text.strip()
    
    sub_clause_data = {
        "sub_clause_letter": sub_clause_letter,
        "content": content
    }
    
    # Check for sub-paragraphs (nested sub-clauses)
    sub_paragraphs = sub_clause_element.find_all('section', {'class': 'akn-subparagraph'})
    if sub_paragraphs:
        sub_clause_data["nested_sub_clauses"] = []
        for sub_paragraph in sub_paragraphs:
            nested_sub_clause = process_nested_sub_clause(sub_paragraph)
            if nested_sub_clause:
                sub_clause_data["nested_sub_clauses"].append(nested_sub_clause)
    
    return sub_clause_data

def process_nested_sub_clause(nested_sub_clause_element):
    """Process a nested sub-clause element and extract its content."""
    # Extract nested sub-clause number
    num_tag = nested_sub_clause_element.find('span', {'class': 'akn-num'})
    if not num_tag:
        return None
    
    nested_sub_clause_number_text = num_tag.text.strip()
    match = re.match(r'\(([ivx]+)\)', nested_sub_clause_number_text)
    
    if not match:
        return None
    
    nested_sub_clause_number = match.group(1)
    
    # Extract nested sub-clause content
    content_tag = nested_sub_clause_element.find('span', {'class': 'akn-content'})
    if not content_tag or not content_tag.find('span', {'class': 'akn-p'}):
        return None
    
    content = content_tag.find('span', {'class': 'akn-p'}).text.strip()
    
    nested_sub_clause_data = {
        "nested_sub_clause_number": nested_sub_clause_number,
        "content": content
    }
    
    return nested_sub_clause_data

def update_json_file(json_file_path, new_chapters):
    """Update the JSON file with the extracted chapters."""
    logger.info(f"Updating JSON file at {json_file_path}")
    
    with open(json_file_path, 'r', encoding='utf-8') as file:
        constitution_data = json.load(file)
    
    # Find the chapters that need to be updated
    for new_chapter in new_chapters:
        chapter_number = new_chapter["chapter_number"]
        
        # Check if the chapter already exists
        chapter_exists = False
        for i, chapter in enumerate(constitution_data["chapters"]):
            if chapter["chapter_number"] == chapter_number:
                # Update the existing chapter
                constitution_data["chapters"][i] = new_chapter
                chapter_exists = True
                logger.info(f"Updated Chapter {chapter_number}")
                break
        
        if not chapter_exists:
            # Add the new chapter
            constitution_data["chapters"].append(new_chapter)
            logger.info(f"Added Chapter {chapter_number}")
    
    # Save the updated data
    with open(json_file_path, 'w', encoding='utf-8') as file:
        json.dump(constitution_data, file, indent=2, ensure_ascii=False)
    
    logger.info("JSON file updated successfully")

def main():
    # File paths
    html_file_path = "src/data/source/TheConstitutionOfKenya.html"
    json_file_path = "src/data/processed/constitution_final.json"
    
    # Get the absolute paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    html_file_path = os.path.join(base_dir, html_file_path)
    json_file_path = os.path.join(base_dir, json_file_path)
    
    # Extract chapters from HTML
    new_chapters = extract_chapters_from_html(html_file_path)
    
    # Update the JSON file
    update_json_file(json_file_path, new_chapters)

if __name__ == "__main__":
    main()
