#!/usr/bin/env python3
"""
DOCX Constitution Extractor

This script extracts text from the Kenyan Constitution DOCX file and structures it into
a hierarchical JSON format with chapters, articles, clauses, and sub-clauses.
"""

from docx import Document
import re
import json
import os
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConstitutionDocxExtractor:
    """Class to extract and structure content from the Kenyan Constitution DOCX file."""
    
    def __init__(self, docx_path):
        """
        Initialize the extractor with the path to the DOCX file.
        
        Args:
            docx_path (str): Path to the Constitution DOCX file
        """
        self.docx_path = docx_path
        self.constitution = {
            "constitution": {
                "title": "The Constitution of Kenya",
                "preamble": "",
                "chapters": []
            }
        }
        
        # Define regex patterns for identifying constitutional elements based on DOCX structure
        self.chapter_pattern = re.compile(r'^CHAPTER\s+([A-Z]+)')
        self.chapter_title_pattern = re.compile(r'^([A-Z][A-Z\s]+[A-Z])$')
        # Improved article title pattern to better match the format in the DOCX
        self.article_title_pattern = re.compile(r'^([A-Za-z][^.]+)\.$')
        # Pattern to extract article numbers (e.g., "1." or "Article 1.")
        self.article_number_pattern = re.compile(r'^(?:Article\s+)?(\d+)\.\s*')
        # Pattern for clauses with numbers in parentheses
        self.clause_pattern = re.compile(r'^\(?(\d+)\)?\s+(.*)')
        # Pattern for sub-clauses with letters
        self.sub_clause_pattern = re.compile(r'^\(?([a-z])\)?\s+(.*)')
        # Pattern for numbered sub-items (roman numerals)
        self.numbered_sub_clause_pattern = re.compile(r'^\(?(i{1,3})\)?\s+(.*)')
        
    def to_title_case(self, text):
        """
        Custom title case: handle ALL CAPS, remove trailing punctuation/dashes
        """
        text = text.strip().rstrip('.-–—').replace('  ', ' ')
        if text.isupper():
            return text.title()
        # Handle mixed case
        return text[:1].upper() + text[1:]

    def extract_text_from_docx(self):
        """Extract all paragraphs from the DOCX file."""
        try:
            logger.info(f"Opening DOCX file: {self.docx_path}")
            doc = Document(self.docx_path)
            paragraphs = []
            
            for paragraph in doc.paragraphs:
                # Get text and style information
                text = paragraph.text.strip()
                if text:  # Only add non-empty paragraphs
                    style_name = paragraph.style.name if paragraph.style else None
                    paragraphs.append({
                        'text': text,
                        'style': style_name
                    })
            
            logger.info(f"Extracted {len(paragraphs)} paragraphs from DOCX")
            # Print the first 5 paragraphs for debugging
            for i, para in enumerate(paragraphs[:5]):
                logger.info(f"Paragraph {i}: {para['text'][:50]}...")
            return paragraphs
            
        except Exception as e:
            logger.error(f"Error extracting text from DOCX: {e}")
            raise
            
    def extract_preamble(self, paragraphs):
        """Extract the preamble from the beginning of the document."""
        preamble_lines = []
        for para in paragraphs:
            text = para['text']
            if self.chapter_pattern.match(text):
                break
            if text:
                preamble_lines.append(text)
        return ' '.join(preamble_lines)
        
    def process_paragraphs(self, paragraphs):
        """Process paragraphs to extract constitutional structure."""
        current_chapter = None
        current_part = None
        current_article = None
        current_clause = None
        global_article_counter = 1
        
        # Extract preamble
        preamble = self.extract_preamble(paragraphs)
        self.constitution["constitution"]["preamble"] = preamble
        # Skip preamble paragraphs
        i = 0
        while i < len(paragraphs) and not self.chapter_pattern.match(paragraphs[i]['text']):
            i += 1
        
        # Log the regex patterns being used
        logger.info(f"Chapter pattern: {self.chapter_pattern.pattern}")
        logger.info(f"Article title pattern: {self.article_title_pattern.pattern}")
        logger.info(f"Clause pattern: {self.clause_pattern.pattern}")
        
        while i < len(paragraphs):
            para = paragraphs[i]
            text = para['text']
            style = para.get('style', '')
            
            # Check for chapter start based on style and content
            chapter_match = self.chapter_pattern.match(text)
            part_match = re.match(r'^PART\s+(\d+)\s*[–-]*\s*(.+)?$', text, re.IGNORECASE)
            if chapter_match or style == 'Heading 1':
                # Save current chapter if exists
                if current_chapter:
                    self.constitution["constitution"]["chapters"].append(current_chapter)
                
                # Extract chapter number
                if chapter_match:
                    chapter_number = chapter_match.group(1)
                else:
                    # Extract from text like "CHAPTER ONE"
                    chapter_parts = text.split()
                    if len(chapter_parts) >= 2:
                        chapter_number = chapter_parts[1]
                    else:
                        chapter_number = "UNKNOWN"
                
                # Get chapter title from next paragraph
                if i + 1 < len(paragraphs):
                    title_text = paragraphs[i + 1]['text']
                    title_match = self.chapter_title_pattern.match(title_text)
                    if title_match or paragraphs[i + 1].get('style', '') == 'Normal':
                        chapter_title = title_text
                        i += 1  # Skip title paragraph
                    else:
                        # Try to find a known chapter title based on the chapter number
                        chapter_title = self.get_known_chapter_title(chapter_number)
                else:
                    # Try to find a known chapter title based on the chapter number
                    chapter_title = self.get_known_chapter_title(chapter_number)
                
                current_chapter = {
                    "number": chapter_number,
                    "title": self.to_title_case(chapter_title),
                    "articles": [],
                    "parts": [],
                    "preamble": ""
                }
                current_part = None
                current_article = None
                current_clause = None
                
                logger.info(f"Found Chapter {chapter_number}: {chapter_title}")
            # Check for PART heading (within chapter)
            elif part_match:
                part_number = part_match.group(1)
                part_title = part_match.group(2) if part_match.group(2) else ""
                current_part = {
                    "part": part_number,
                    "title": self.to_title_case(part_title),
                    "articles": []
                }
                if current_chapter is not None:
                    current_chapter["parts"].append(current_part)
                current_article = None
                current_clause = None
                logger.info(f"Found PART {part_number}: {part_title}")
                
            # Check for article title (Heading 2 style)
            elif self.article_title_pattern.match(text) or style == 'Heading 2':
                if current_chapter:
                    article_title = text.rstrip('.')
                    
                    # Skip titles that look like they might be sub-clauses or fragments
                    if article_title.lower().startswith('a ') or article_title.lower().startswith('the ') or len(article_title) < 5:
                        logger.info(f"Skipping likely fragment title: {article_title}")
                        i += 1
                        continue
                    
                    # Extract article number from the title if it starts with a number
                    article_number = ""
                    title_number_match = re.match(r'^(\d+)\s+', article_title)
                    if title_number_match:
                        article_number = title_number_match.group(1)
                        article_title = article_title[len(title_number_match.group(0)):].strip()
                    
                    # If no number in title, try to get it from the next paragraph
                    if not article_number and i + 1 < len(paragraphs):
                        next_text = paragraphs[i + 1]['text']
                        article_number_match = self.article_number_pattern.match(next_text)
                        
                        if article_number_match:
                            article_number = article_number_match.group(1)
                    
                    # If we couldn't extract the article number, try to get it from the title
                    if not article_number and article_title.split()[0].isdigit():
                        article_number = article_title.split()[0]
                        article_title = ' '.join(article_title.split()[1:])
                    
                    # If we still don't have an article number, try to determine it from context
                    if not article_number and current_chapter:
                        # Look at the previous article's number if available
                        if current_article and current_article.get('local_number'):
                            try:
                                prev_num = int(current_article['local_number'])
                                article_number = str(prev_num + 1)
                                logger.info(f"Inferred article number {article_number} from previous article")
                            except ValueError:
                                # If previous number isn't a valid integer, use position in chapter
                                article_number = str(len(current_chapter['articles']) + 1)
                        else:
                            # First article in chapter
                            article_number = "1"
                    
                    # Clean and standardize the title
                    article_title = self.to_title_case(article_title)
                    
                    # Save current article if exists
                    if current_article:
                        # Attach to part if inside a part, else to chapter
                        if current_part is not None:
                            current_part["articles"].append(current_article)
                        else:
                            current_chapter["articles"].append(current_article)
                    
                    # Create new article with both local and global numbering
                    current_article = {
                        "local_number": article_number,  # Number within chapter/part
                        "global_number": str(global_article_counter),  # Sequential number across entire constitution
                        "title": article_title,
                        "clauses": []
                    }
                    global_article_counter += 1  # Increment global counter
                    current_clause = None
                    
                    logger.info(f"Found Article {article_number} (global: {current_article['global_number']}): {article_title}")
                
            # Check for clause (List Paragraph style or starts with a number in parentheses)
            elif (style == 'List Paragraph' or self.clause_pattern.match(text)) and current_article:
                clause_match = self.clause_pattern.match(text)
                if clause_match:
                    clause_number = clause_match.group(1)
                    clause_text = f"({clause_number}) {clause_match.group(2)}"
                    
                    # Clean up the clause text
                    clause_text = clause_text.replace('\\(', '(').replace('\\)', ')')
                    
                    # Check if this is a continuation of a previous clause
                    if current_clause and current_clause["number"] == clause_number:
                        # Append to existing clause text with a space
                        current_clause["text"] += " " + clause_match.group(2)
                        logger.info(f"Appended to Clause {clause_number} in Article {current_article['local_number']}")
                    else:
                        # Create new clause
                        current_clause = {
                            "number": clause_number,
                            "text": clause_text,
                            "sub_clauses": []
                        }
                        current_article["clauses"].append(current_clause)
                        logger.info(f"Found Clause {clause_number} in Article {current_article['local_number']}")
                    
                    # Look ahead for continuation lines
                    j = i + 1
                    while j < len(paragraphs):
                        next_para = paragraphs[j]
                        next_text = next_para['text']
                        next_style = next_para.get('style', '')
                        
                        # If it's a new clause, article, chapter, or part, stop looking
                        if (self.clause_pattern.match(next_text) or 
                            self.article_title_pattern.match(next_text) or 
                            self.chapter_pattern.match(next_text) or 
                            re.match(r'^PART\s+\d+', next_text)):
                            break
                            
                        # If it's a sub-clause, stop looking
                        if (self.sub_clause_pattern.search(next_text) or
                            self.numbered_sub_clause_pattern.search(next_text) or
                            next_style in ['List Paragraph', 'List Bullet', 'List Number']):
                            break
                            
                        # It's a continuation - append and skip this paragraph in the main loop
                        if next_text:
                            current_clause["text"] += " " + next_text
                            logger.info(f"Added continuation line to Clause {clause_number}")
                            j += 1
                            i = j - 1  # Will be incremented at the end of the loop
                        else:
                            break
                    
            # Check for sub-clause (indented text with letter or roman numeral, or bullet/indented value under article)
            elif current_clause and (style == 'List Paragraph' or style == 'List Bullet' or style == 'List Number' or style.startswith('List') or (style == 'Normal' and current_article and current_article['title'].lower().startswith('national values and principles'))) and len(text) > 0:
                # First try to match explicit sub-clause patterns
                sub_clause_match = self.sub_clause_pattern.search(text)
                numbered_sub_clause_match = self.numbered_sub_clause_pattern.search(text)
                
                # Also check for sub-clauses that start with letters without parentheses
                if not sub_clause_match and len(text) > 2 and text[0].islower() and (text[1] == ' ' or text[1] == ')'):
                    sub_clause_match = re.match(r'^([a-z])\s+(.*)', text)
                
                # Track the current sub-clause for continuation lines
                current_sub_clause = None
                
                if sub_clause_match:
                    letter = sub_clause_match.group(1)
                    sub_text = sub_clause_match.group(2)
                    
                    # Clean up the sub-clause text
                    sub_text = sub_text.strip()
                    if sub_text.endswith(';'):
                        sub_text = sub_text[:-1].strip()
                    
                    # Check if this is a continuation of a previous sub-clause
                    existing_sub = None
                    for sub in current_clause["sub_clauses"]:
                        if sub.get("letter") == letter:
                            existing_sub = sub
                            break
                    
                    if existing_sub:
                        # Append to existing sub-clause
                        existing_sub["text"] += " " + sub_text
                        current_sub_clause = existing_sub
                        logger.info(f"Appended to Sub-clause {letter} in Clause {current_clause['number']}")
                    else:
                        # Create new sub-clause
                        new_sub = {
                            "letter": letter,
                            "text": sub_text
                        }
                        current_clause["sub_clauses"].append(new_sub)
                        current_sub_clause = new_sub
                        logger.info(f"Found Sub-clause {letter} in Clause {current_clause['number']}")
                    
                elif numbered_sub_clause_match:
                    # This could be a roman numeral sub-clause
                    numeral = numbered_sub_clause_match.group(1)
                    sub_text = numbered_sub_clause_match.group(2)
                    
                    # Clean up the sub-text
                    sub_text = sub_text.strip()
                    if sub_text.endswith(';'):
                        sub_text = sub_text[:-1].strip()
                    
                    # If we already have sub-clauses, this might be a sub-item
                    if current_clause["sub_clauses"]:
                        last_sub_clause = current_clause["sub_clauses"][-1]
                        if "sub_items" not in last_sub_clause:
                            last_sub_clause["sub_items"] = []
                        
                        # Check if this numeral already exists
                        existing_item = None
                        for item in last_sub_clause.get("sub_items", []):
                            if item.get("numeral") == numeral:
                                existing_item = item
                                break
                        
                        if existing_item:
                            # Append to existing sub-item
                            existing_item["text"] += " " + sub_text
                            logger.info(f"Appended to Sub-item {numeral} in Sub-clause {last_sub_clause['letter']}")
                        else:
                            # Add new sub-item
                            new_item = {
                                "numeral": numeral,
                                "text": sub_text
                            }
                            last_sub_clause["sub_items"].append(new_item)
                            logger.info(f"Found Sub-item {numeral} in Sub-clause {last_sub_clause['letter']}")
                    else:
                        # Treat it as a lettered sub-clause with a numeral instead
                        new_sub = {
                            "letter": numeral,
                            "text": sub_text
                        }
                        current_clause["sub_clauses"].append(new_sub)
                        current_sub_clause = new_sub
                        logger.info(f"Found Numbered Sub-clause {numeral} in Clause {current_clause['number']}")
                    
                # If no explicit pattern matches but it's a list style or a bullet/indented value, treat as an implicit sub-clause
                elif text[0].islower() or text.startswith('the ') or text.startswith('a '):
                    # This is likely a continuation or implicit sub-clause
                    # Generate a letter based on position
                    letter = chr(97 + len(current_clause["sub_clauses"]))  # 97 is ASCII for 'a'
                    
                    # Clean up the text
                    clean_text = text.strip()
                    if clean_text.endswith(';'):
                        clean_text = clean_text[:-1].strip()
                    
                    new_sub = {
                        "letter": letter,
                        "text": clean_text
                    }
                    current_clause["sub_clauses"].append(new_sub)
                    current_sub_clause = new_sub
                    logger.info(f"Found Implicit Sub-clause {letter} in Clause {current_clause['number']}")
                
                # Look ahead for continuation lines for the sub-clause
                if current_sub_clause:
                    j = i + 1
                    while j < len(paragraphs):
                        next_para = paragraphs[j]
                        next_text = next_para['text']
                        next_style = next_para.get('style', '')
                        
                        # If it's a new clause, article, chapter, part, or sub-clause, stop looking
                        if (self.clause_pattern.match(next_text) or 
                            self.article_title_pattern.match(next_text) or 
                            self.chapter_pattern.match(next_text) or 
                            re.match(r'^PART\s+\d+', next_text) or
                            self.sub_clause_pattern.search(next_text) or
                            self.numbered_sub_clause_pattern.search(next_text)):
                            break
                            
                        # It's a continuation if it's not a new structural element
                        if next_text and not next_text[0].isupper():
                            current_sub_clause["text"] += " " + next_text
                            logger.info(f"Added continuation line to Sub-clause {current_sub_clause.get('letter')}")
                            j += 1
                            i = j - 1  # Will be incremented at the end of the loop
                        else:
                            break
            
            i += 1
        
        # Save the last article and chapter
        if current_article:
            if current_part is not None:
                current_part["articles"].append(current_article)
            else:
                current_chapter["articles"].append(current_article)
        if current_chapter:
            self.constitution["constitution"]["chapters"].append(current_chapter)
            
        return self.constitution
    
    def get_known_chapter_title(self, chapter_number):
        """Return a known chapter title based on chapter number."""
        chapter_titles = {
            "ONE": "SOVEREIGNTY OF THE PEOPLE AND SUPREMACY OF THIS CONSTITUTION",
            "TWO": "THE REPUBLIC",
            "THREE": "CITIZENSHIP",
            "FOUR": "THE BILL OF RIGHTS",
            "FIVE": "LAND AND ENVIRONMENT",
            "SIX": "LEADERSHIP AND INTEGRITY",
            "SEVEN": "REPRESENTATION OF THE PEOPLE",
            "EIGHT": "THE LEGISLATURE",
            "NINE": "THE EXECUTIVE",
            "TEN": "JUDICIARY",
            "ELEVEN": "DEVOLVED GOVERNMENT",
            "TWELVE": "PUBLIC FINANCE",
            "THIRTEEN": "THE PUBLIC SERVICE",
            "FOURTEEN": "NATIONAL SECURITY",
            "FIFTEEN": "COMMISSIONS AND INDEPENDENT OFFICES",
            "SIXTEEN": "AMENDMENT OF THIS CONSTITUTION",
            "SEVENTEEN": "GENERAL PROVISIONS",
            "EIGHTEEN": "TRANSITIONAL AND CONSEQUENTIAL PROVISIONS"
        }
        return chapter_titles.get(chapter_number, "")
    
    def merge_fragmented_articles(self):
        """Merge articles that appear to be fragments of the same article."""
        for chapter in self.constitution["constitution"]["chapters"]:
            # Process articles in the chapter
            i = 0
            while i < len(chapter["articles"]) - 1:
                current = chapter["articles"][i]
                next_article = chapter["articles"][i + 1]
                
                # Get the article number (may be local_number or number)
                current_num = current.get("local_number", current.get("number", ""))
                next_num = next_article.get("local_number", next_article.get("number", ""))
                
                # Check if the next article is a fragment of the current one
                if (not next_num or next_num == current_num) and current_num:
                    # Merge titles if they are different
                    if current["title"] != next_article["title"]:
                        current["title"] += " " + next_article["title"]
                    
                    # Merge clauses
                    current["clauses"].extend(next_article["clauses"])
                    
                    # Remove the fragment
                    chapter["articles"].pop(i + 1)
                    logger.info(f"Merged fragmented article: {current_num} {current['title']}")
                else:
                    i += 1
            
            # Process articles in parts if they exist
            for part in chapter.get("parts", []):
                i = 0
                while i < len(part["articles"]) - 1:
                    current = part["articles"][i]
                    next_article = part["articles"][i + 1]
                    
                    # Get the article number (may be local_number or number)
                    current_num = current.get("local_number", current.get("number", ""))
                    next_num = next_article.get("local_number", next_article.get("number", ""))
                    
                    # Check if the next article is a fragment of the current one
                    if (not next_num or next_num == current_num) and current_num:
                        # Merge titles if they are different
                        if current["title"] != next_article["title"]:
                            current["title"] += " " + next_article["title"]
                        
                        # Merge clauses
                        current["clauses"].extend(next_article["clauses"])
                        
                        # Remove the fragment
                        part["articles"].pop(i + 1)
                        logger.info(f"Merged fragmented article in part: {current_num} {current['title']}")
                    else:
                        i += 1
    
    def fix_article_numbers(self):
        """Fix article numbers based on known article titles and sequence."""
        # This is a placeholder for more sophisticated article number fixing
        # For now, we'll just ensure all articles have both local_number and global_number
        global_counter = 1
        for chapter in self.constitution["constitution"]["chapters"]:
            for art in chapter.get("articles", []):
                # Ensure local_number exists
                if "number" in art and "local_number" not in art:
                    art["local_number"] = art.pop("number")
                # Ensure global_number exists
                if "global_number" not in art:
                    art["global_number"] = str(global_counter)
                    global_counter += 1
            
            # Process articles in parts
            for part in chapter.get("parts", []):
                for art in part.get("articles", []):
                    # Ensure local_number exists
                    if "number" in art and "local_number" not in art:
                        art["local_number"] = art.pop("number")
                    # Ensure global_number exists
                    if "global_number" not in art:
                        art["global_number"] = str(global_counter)
                        global_counter += 1
    
    def clean_output(self):
        """Clean and normalize the extracted data."""
        # Standardize all titles
        for chapter in self.constitution["constitution"]["chapters"]:
            # Clean chapter title
            chapter["title"] = self.to_title_case(chapter["title"])
            
            # Clean article titles
            for article in chapter.get("articles", []):
                article["title"] = self.to_title_case(article["title"])
            
            # Clean part titles
            for part in chapter.get("parts", []):
                if "title" in part:
                    part["title"] = self.to_title_case(part["title"])
                
                # Clean article titles in parts
                for article in part.get("articles", []):
                    article["title"] = self.to_title_case(article["title"])
    
    def save_to_json(self, output_path):
        """
        Save the structured constitution to a JSON file.
        
        Args:
            output_path (str): Path to save the JSON file
        """
        try:
            logger.info(f"Saving constitution to JSON: {output_path}")
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.constitution, f, ensure_ascii=False, indent=2)
            logger.info(f"Constitution saved to: {output_path}")
        except Exception as e:
            logger.error(f"Error saving to JSON: {e}")
            raise
    
    def post_process_structure(self):
        """
        Fix structural issues: merge spurious chapter 2 as PART 2 of Chapter FOUR, move misplaced sub-clauses, fix Article 10 sub-values,
        standardize title casing, ensure proper numbering, and fix any remaining structural issues.
        """
        chapters = self.constitution["constitution"]["chapters"]
        
        # 1. Standardize title casing for all elements
        for ch in chapters:
            # Standardize chapter title
            ch["title"] = self.to_title_case(ch["title"])
            
            # Process articles in chapters
            for art in ch.get("articles", []):
                art["title"] = self.to_title_case(art["title"])
                
                # Ensure both local_number and global_number exist
                if "number" in art and "local_number" not in art:
                    art["local_number"] = art.pop("number")
                if "global_number" not in art:
                    # If missing, assign a placeholder
                    art["global_number"] = art["local_number"]
            
            # Process parts
            for part in ch.get("parts", []):
                if "title" in part:
                    part["title"] = self.to_title_case(part["title"])
                
                # Process articles in parts
                for art in part.get("articles", []):
                    art["title"] = self.to_title_case(art["title"])
                    
                    # Ensure both local_number and global_number exist
                    if "number" in art and "local_number" not in art:
                        art["local_number"] = art.pop("number")
                    if "global_number" not in art:
                        # If missing, assign a placeholder
                        art["global_number"] = art["local_number"]
        
        # 2. Merge chapter '2' with empty title into Chapter FOUR as PART 2
        part2_chapter = None
        chapter_four = None
        for ch in chapters:
            if ch["number"] == "FOUR":
                chapter_four = ch
            if ch["number"] == "2" and not ch["title"]:
                part2_chapter = ch
        if part2_chapter and chapter_four:
            # Create PART 2 object
            part2 = {
                "part": "2",
                "title": "Part 2 – Specific Rights And Fundamental Freedoms",
                "articles": part2_chapter.get("articles", [])
            }
            # Add to chapter_four["parts"]
            if "parts" not in chapter_four:
                chapter_four["parts"] = []
            chapter_four["parts"].append(part2)
            # Remove the spurious chapter
            chapters.remove(part2_chapter)
        
        # 3. Move sub-clause (a) Privacy to Article 31 (robust, recursive)
        def collect_and_remove_privacy_subs(articles, skip_article_number="31"):
            found = []
            for art in articles:
                for clause in art.get("clauses", []):
                    for sub in list(clause.get("sub_clauses", [])):
                        if (
                            sub.get("letter", "").lower() == "a"
                            and "privacy" in sub.get("text", "").lower()
                            and art.get("local_number") != skip_article_number
                        ):
                            clause["sub_clauses"].remove(sub)
                            found.append(sub)
            return found

        privacy_subs = []
        # Check top-level articles and articles in parts
        for ch in chapters:
            privacy_subs += collect_and_remove_privacy_subs(ch.get("articles", []))
            for part in ch.get("parts", []):
                privacy_subs += collect_and_remove_privacy_subs(part.get("articles", []))

        # Ensure Article 31 exists (check both top-level and in parts)
        found_31 = False
        def add_privacy_to_31(articles):
            nonlocal found_31
            for art in articles:
                if art.get("local_number") == "31":
                    found_31 = True
                    if not art.get("clauses"):
                        art["clauses"] = [{"number": "1", "text": "", "sub_clauses": []}]
                    for sub in privacy_subs:
                        if not any("privacy" in s.get("text", "").lower() for s in art["clauses"][0]["sub_clauses"]):
                            art["clauses"][0]["sub_clauses"].append(sub)
        for ch in chapters:
            add_privacy_to_31(ch.get("articles", []))
            for part in ch.get("parts", []):
                add_privacy_to_31(part.get("articles", []))
        # If Article 31 does not exist, create it under the last chapter
        if not found_31 and privacy_subs:
            last_ch = chapters[-1]
            new_art = {"local_number": "31", "global_number": "31", "title": "Privacy", "clauses": [{"number": "1", "text": "", "sub_clauses": privacy_subs}]}
            last_ch["articles"].append(new_art)

        # 4. Add preamble to chapter if missing
        for ch in chapters:
            if "preamble" not in ch:
                ch["preamble"] = ""  # For future use
        
        # 5. Fix Article 10 sub-values (e.g., 'sustainable development')
        for ch in chapters:
            for art in ch.get("articles", []):
                if art["local_number"] == "10":
                    # Find all articles after 10 that are likely sub-values
                    idx = ch["articles"].index(art)
                    to_move = []
                    for art2 in ch["articles"][idx+1:]:
                        # Heuristic: short title, no clauses, or matches known value
                        if art2["title"].lower() in [
                            "sustainable development", "patriotism", "rule of law", "democracy and participation of the people", "human dignity", "equity", "social justice", "inclusiveness", "equality", "human rights", "non-discrimination", "protection of the marginalised", "good governance", "integrity", "transparency", "accountability" ] or (len(art2["title"]) < 30 and not art2["clauses"]):
                            to_move.append(art2)
                    # Move as sub-clauses of Article 10's first clause
                    if art["clauses"]:
                        for subart in to_move:
                            art["clauses"][0]["sub_clauses"].append({
                                "letter": "a", # Could improve with correct letter
                                "text": subart["title"]
                            })
                            ch["articles"].remove(subart)
    
    def process(self):
        """
        Main processing method to extract and structure the constitution.
        
        Returns:
            dict: The structured constitution data
        """
        try:
            logger.info(f"Processing DOCX: {self.docx_path}")
            
            # Extract paragraphs from DOCX
            paragraphs = self.extract_text_from_docx()
            
            # Process paragraphs to extract structure
            self.process_paragraphs(paragraphs)
            
            # Merge fragmented articles
            self.merge_fragmented_articles()
            
            # Fix article numbers
            self.fix_article_numbers()
            
            # Clean the output
            self.clean_output()
            
            # Perform a second merge to catch any remaining fragments
            self.merge_fragmented_articles()
            
            # Post-process for structural fixes
            self.post_process_structure()
            
            # Count items for summary
            total_articles = sum(len(chapter["articles"]) for chapter in self.constitution["constitution"]["chapters"])
            total_clauses = sum(len(article["clauses"]) for chapter in self.constitution["constitution"]["chapters"] for article in chapter["articles"])
            total_sub_clauses = sum(len(clause["sub_clauses"]) for chapter in self.constitution["constitution"]["chapters"] for article in chapter["articles"] for clause in article["clauses"])
            
            logger.info(f"Processed {len(self.constitution['constitution']['chapters'])} chapters")
            logger.info(f"Processed {total_articles} articles")
            logger.info(f"Processed {total_clauses} clauses")
            logger.info(f"Processed {total_sub_clauses} sub-clauses")
            
            return self.constitution
            
        except Exception as e:
            logger.error(f"Error processing constitution: {e}")
            raise


def main():
    """Main function to extract and save the constitution."""
    # Get the absolute path to the DOCX file
    base_dir = Path(__file__).resolve().parent.parent.parent
    docx_path = base_dir / "src" / "data" / "source" / "TheConstitutionOfKenya.docx"
    
    # Check if the file exists
    if not docx_path.exists():
        logger.error(f"DOCX file not found at: {docx_path}")
        logger.info(f"Current directory: {os.getcwd()}")
        logger.info(f"Base directory: {base_dir}")
        return
    else:
        logger.info(f"DOCX file found at: {docx_path}")
        logger.info(f"File size: {docx_path.stat().st_size} bytes")
    
    # Define output path
    output_path = base_dir / "src" / "data" / "processed" / "constitution.json"
    
    # Create the extractor and process the DOCX
    extractor = ConstitutionDocxExtractor(str(docx_path))
    constitution_data = extractor.process()
    extractor.save_to_json(str(output_path))
    
    # Print summary
    chapters = constitution_data["constitution"]["chapters"]
    total_articles = sum(len(chapter["articles"]) for chapter in chapters)
    total_clauses = sum(len(article["clauses"]) for chapter in chapters for article in chapter["articles"])
    
    logger.info(f"Constitution extraction complete:")
    logger.info(f"  - {len(chapters)} chapters")
    logger.info(f"  - {total_articles} articles")
    logger.info(f"  - {total_clauses} clauses")


if __name__ == "__main__":
    main()
