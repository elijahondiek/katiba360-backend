#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Constitution Extractor - Version 8
---------------------------------
This script extracts the structure and content of a constitution from a DOCX file
and converts it into a structured JSON format.

This version addresses critical issues:
1. Fixes chapter titles to use proper names instead of article titles
2. Corrects nesting of articles inside chapters
3. Properly handles clause and sub-clause relationships
4. Fixes clause numbering
5. Prevents clause text from including future article content
6. Implements consistent global article numbering
"""

import os
import re
import json
import logging
from docx import Document

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConstitutionDocxExtractor:
    """Extract constitution structure from DOCX file."""
    
    def __init__(self, docx_path):
        """Initialize with path to DOCX file."""
        self.docx_path = docx_path
        self.constitution = {
            "constitution": {
                "title": "The Constitution of Kenya",
                "preamble": "",
                "chapters": []
            }
        }
        
        # Compile regex patterns for structure recognition
        self.chapter_pattern = re.compile(r'^CHAPTER\s+([A-Z]+)')
        self.article_pattern = re.compile(r'^Article\s+([0-9]+)[\s:—–-]+(.+)$', re.IGNORECASE)
        self.clause_pattern = re.compile(r'^\(([0-9]+)\)')
        self.sub_clause_pattern = re.compile(r'^\(([a-z])\)')
        self.bullet_pattern = re.compile(r'^[•\-*]\s+(.+)$')
        
        # Known chapter titles (from the actual Constitution of Kenya)
        self.chapter_titles = {
            "ONE": "Sovereignty of the People and Supremacy of this Constitution",
            "TWO": "The Republic",
            "THREE": "Citizenship",
            "FOUR": "The Bill of Rights",
            "FIVE": "Land and Environment",
            "SIX": "Leadership and Integrity",
            "SEVEN": "Representation of the People",
            "EIGHT": "The Legislature",
            "NINE": "The Executive",
            "TEN": "Judiciary",
            "ELEVEN": "Devolved Government",
            "TWELVE": "Public Finance",
            "THIRTEEN": "The Public Service",
            "FOURTEEN": "National Security",
            "FIFTEEN": "Commissions and Independent Offices",
            "SIXTEEN": "Amendment of this Constitution",
            "SEVENTEEN": "General Provisions",
            "EIGHTEEN": "Transitional and Consequential Provisions"
        }
        
        # Known part titles within chapters
        self.part_titles = {
            "FOUR": {
                "1": "General Provisions Relating to the Bill of Rights",
                "2": "Rights and Fundamental Freedoms",
                "3": "Specific Application of Rights",
                "4": "State of Emergency",
                "5": "Kenya National Human Rights and Equality Commission"
            }
        }
        
        # Track current context
        self.current_chapter = None
        self.current_part = None
        self.current_article = None
        self.current_clause = None
        self.global_article_count = 0
        
    def extract(self):
        """Extract constitution structure from DOCX file."""
        # Extract text from DOCX
        paragraphs = self.extract_text_from_docx()
        
        # Process paragraphs to build structure
        self.process_paragraphs(paragraphs)
        
        # Post-process the structure
        self.post_process_structure()
        
        return self.constitution
    
    def extract_text_from_docx(self):
        """Extract text and paragraph styles from DOCX file."""
        doc = Document(self.docx_path)
        paragraphs = []
        
        for paragraph in doc.paragraphs:
            text = paragraph.text.strip()
            if text:
                style = paragraph.style.name if paragraph.style else ""
                paragraphs.append((text, style))
        
        logger.info(f"Extracted {len(paragraphs)} paragraphs from DOCX")
        return paragraphs
    
    def is_article_title(self, text, style):
        """Determine if text is an article title."""
        # Check if it matches Article X pattern
        if self.article_pattern.match(text):
            return True
        
        # Check if it's a heading style
        if style in ['Heading 2', 'Heading 3']:
            return True
        
        # Check for common article title patterns
        if (len(text.split()) <= 6 and 
            (text.startswith('Right to') or 
             text.startswith('Freedom of') or 
             'rights' in text.lower() or 
             'freedom' in text.lower()) and
            not text.startswith('(') and
            not self.clause_pattern.match(text)):
            return True
        
        return False
    
    def is_new_content_marker(self, text):
        """Check if text indicates the start of new content (article or chapter)."""
        return (self.chapter_pattern.match(text) or 
                self.article_pattern.match(text) or 
                text.startswith('Article') or
                (len(text.split()) <= 6 and 
                 (text.startswith('Right to') or 
                  text.startswith('Freedom of'))))
    
    def process_paragraphs(self, paragraphs):
        """Process paragraphs to build constitution structure."""
        i = 0
        while i < len(paragraphs):
            text, style = paragraphs[i]
            
            # Process chapter
            chapter_match = self.chapter_pattern.match(text)
            if chapter_match:
                chapter_number = chapter_match.group(1)
                
                # Get the proper chapter title from our mapping
                chapter_title = self.chapter_titles.get(chapter_number, "")
                
                # If we don't have a predefined title, try to extract it from the next paragraph
                if not chapter_title and i + 1 < len(paragraphs):
                    next_text, next_style = paragraphs[i + 1]
                    if next_style in ['Normal', 'Heading 1'] and not self.chapter_pattern.match(next_text):
                        chapter_title = next_text
                        i += 1  # Skip the title paragraph since we've processed it
                
                self.current_chapter = {
                    "number": chapter_number,
                    "title": chapter_title,
                    "articles": [],
                    "parts": [],
                    "preamble": ""
                }
                self.constitution["constitution"]["chapters"].append(self.current_chapter)
                self.current_part = None
                self.current_article = None
                self.current_clause = None
                
                logger.info(f"Found Chapter {chapter_number}: {chapter_title}")
                i += 1
                continue
            
            # If we don't have a chapter yet, skip
            if not self.current_chapter:
                i += 1
                continue
            
            # Process part (if text starts with "PART")
            if text.startswith('PART '):
                part_number = text.split()[1].strip()
                
                # Get the proper part title from our mapping
                part_title = ""
                if self.current_chapter["number"] in self.part_titles:
                    part_title = self.part_titles[self.current_chapter["number"]].get(part_number, "")
                
                # If we don't have a predefined title, try to extract it from the text
                if not part_title:
                    parts = text.split('—', 1)
                    if len(parts) > 1:
                        part_title = parts[1].strip()
                    elif i + 1 < len(paragraphs):
                        next_text, next_style = paragraphs[i + 1]
                        if next_style in ['Normal', 'Heading 2'] and not self.is_article_title(next_text, next_style):
                            part_title = next_text
                            i += 1  # Skip the title paragraph since we've processed it
                
                self.current_part = {
                    "number": part_number,
                    "title": part_title,
                    "articles": []
                }
                self.current_chapter["parts"].append(self.current_part)
                self.current_article = None
                self.current_clause = None
                
                logger.info(f"Found Part {part_number}: {part_title}")
                i += 1
                continue
            
            # Process article
            if self.is_article_title(text, style):
                self.global_article_count += 1
                
                # Extract article number and title
                article_match = self.article_pattern.match(text)
                if article_match:
                    article_number = article_match.group(1)
                    article_title = article_match.group(2).strip()
                else:
                    # If no explicit number, use sequential numbering
                    if self.current_article:
                        try:
                            article_number = str(int(self.current_article["local_number"]) + 1)
                        except ValueError:
                            article_number = "1"
                    else:
                        article_number = "1"
                    
                    article_title = text
                
                logger.info(f"Found Article {article_number} (global: {self.global_article_count}): {article_title[:50]}")
                
                self.current_article = {
                    "local_number": article_number,
                    "global_number": str(self.global_article_count),
                    "title": article_title,
                    "clauses": []
                }
                
                if self.current_part:
                    self.current_part["articles"].append(self.current_article)
                else:
                    self.current_chapter["articles"].append(self.current_article)
                
                self.current_clause = None
                i += 1
                continue
            
            # If we don't have an article yet, skip
            if not self.current_article:
                i += 1
                continue
            
            # Process clause
            clause_match = self.clause_pattern.match(text)
            if clause_match:
                clause_number = clause_match.group(1)
                
                # Create a new clause
                self.current_clause = {
                    "number": clause_number,
                    "text": text,
                    "sub_clauses": []
                }
                self.current_article["clauses"].append(self.current_clause)
                
                logger.info(f"Found Clause {clause_number} in Article {self.current_article['local_number']}")
                i += 1
                continue
            
            # Process sub-clause
            sub_clause_match = self.sub_clause_pattern.match(text)
            if sub_clause_match and self.current_clause:
                sub_clause_letter = sub_clause_match.group(1)
                
                sub_clause = {
                    "letter": sub_clause_letter,
                    "text": text
                }
                self.current_clause["sub_clauses"].append(sub_clause)
                
                logger.info(f"Found Sub-clause {sub_clause_letter} in Clause {self.current_clause['number']}")
                i += 1
                continue
            
            # Process bullet points as sub-clauses
            bullet_match = self.bullet_pattern.match(text)
            if bullet_match and self.current_clause:
                bullet_text = bullet_match.group(1)
                
                # Use a number if we don't have any sub-clauses yet, otherwise use the next letter
                if not self.current_clause["sub_clauses"]:
                    sub_clause = {
                        "letter": "a",
                        "text": text
                    }
                else:
                    # Get the last sub-clause letter and increment it
                    last_letter = self.current_clause["sub_clauses"][-1]["letter"]
                    next_letter = chr(ord(last_letter) + 1)
                    
                    sub_clause = {
                        "letter": next_letter,
                        "text": text
                    }
                
                self.current_clause["sub_clauses"].append(sub_clause)
                
                logger.info(f"Found bullet point as sub-clause in Clause {self.current_clause['number']}")
                i += 1
                continue
            
            # Check if this is a list item that should be a sub-clause
            if style == 'List Paragraph' and self.current_clause and not text.startswith('('):
                # This is likely a sub-clause without explicit marking
                if not self.current_clause["sub_clauses"]:
                    sub_clause = {
                        "letter": "a",
                        "text": text
                    }
                else:
                    # Get the last sub-clause letter and increment it
                    last_letter = self.current_clause["sub_clauses"][-1]["letter"]
                    next_letter = chr(ord(last_letter) + 1)
                    
                    sub_clause = {
                        "letter": next_letter,
                        "text": text
                    }
                
                self.current_clause["sub_clauses"].append(sub_clause)
                
                logger.info(f"Found list item as sub-clause in Clause {self.current_clause['number']}")
                i += 1
                continue
            
            # If we have a current clause, append text to it (but only if it's not a new article/chapter)
            if self.current_clause and text and not self.is_new_content_marker(text):
                # Check if this is a continuation of clause text
                self.current_clause["text"] += " " + text
                logger.info(f"Appended to existing clause: {text[:20]}...")
            elif self.current_article and text and not self.is_new_content_marker(text):
                # This might be implicit clause content
                if not self.current_article["clauses"]:
                    # Create an implicit clause
                    self.current_clause = {
                        "number": "1",
                        "text": text,
                        "sub_clauses": []
                    }
                    self.current_article["clauses"].append(self.current_clause)
                    logger.info(f"Created implicit clause for article content: {text[:20]}...")
            
            i += 1
    
    def standardize_title_casing(self, title):
        """Standardize title casing to Title Case with exceptions."""
        # Words that should remain lowercase
        lowercase_words = {'a', 'an', 'the', 'and', 'but', 'or', 'for', 'nor', 'on', 'at', 
                          'to', 'from', 'by', 'of', 'in', 'with', 'under', 'over'}
        
        # Don't modify if it's a full sentence or clause content
        if len(title.split()) > 10 or title.endswith('.'):
            return title
        
        words = title.split()
        result = []
        
        for i, word in enumerate(words):
            # Always capitalize first and last word
            if i == 0 or i == len(words) - 1:
                result.append(word.capitalize())
            # Keep lowercase for specific words
            elif word.lower() in lowercase_words:
                result.append(word.lower())
            # Capitalize other words
            else:
                result.append(word.capitalize())
        
        return ' '.join(result)
    
    def fix_clause_numbering(self):
        """Ensure clause numbers are sequential and match their content."""
        chapters = self.constitution["constitution"]["chapters"]
        
        for chapter in chapters:
            # Process articles in the chapter
            for article in chapter.get("articles", []):
                for i, clause in enumerate(article.get("clauses", []), 1):
                    # Extract the actual clause number from the text if available
                    clause_match = self.clause_pattern.match(clause.get("text", ""))
                    if clause_match:
                        actual_number = clause_match.group(1)
                        clause["number"] = actual_number
                    else:
                        # Otherwise use sequential numbering
                        clause["number"] = str(i)
            
            # Process articles in parts
            for part in chapter.get("parts", []):
                for article in part.get("articles", []):
                    for i, clause in enumerate(article.get("clauses", []), 1):
                        # Extract the actual clause number from the text if available
                        clause_match = self.clause_pattern.match(clause.get("text", ""))
                        if clause_match:
                            actual_number = clause_match.group(1)
                            clause["number"] = actual_number
                        else:
                            # Otherwise use sequential numbering
                            clause["number"] = str(i)
    
    def fix_article_titles(self):
        """Fix article titles to ensure they don't contain clause content."""
        chapters = self.constitution["constitution"]["chapters"]
        
        for chapter in chapters:
            # Process articles in the chapter
            for article in chapter.get("articles", []):
                title = article.get("title", "")
                
                # If title is too long, it might be clause content
                if len(title.split()) > 10:
                    # Create a new clause with this content if none exists
                    if not article["clauses"]:
                        article["clauses"].append({
                            "number": "1",
                            "text": title,
                            "sub_clauses": []
                        })
                    
                    # Set a more appropriate title
                    article["title"] = f"Article {article.get('local_number', '')}"
                    logger.info(f"Fixed article title: {title[:30]}...")
            
            # Process articles in parts
            for part in chapter.get("parts", []):
                for article in part.get("articles", []):
                    title = article.get("title", "")
                    
                    # If title is too long, it might be clause content
                    if len(title.split()) > 10:
                        # Create a new clause with this content if none exists
                        if not article["clauses"]:
                            article["clauses"].append({
                                "number": "1",
                                "text": title,
                                "sub_clauses": []
                            })
                        
                        # Set a more appropriate title
                        article["title"] = f"Article {article.get('local_number', '')}"
                        logger.info(f"Fixed article title: {title[:30]}...")
    
    def ensure_global_numbering(self):
        """Ensure global article numbering is consistent."""
        global_count = 1
        chapters = self.constitution["constitution"]["chapters"]
        
        for chapter in chapters:
            # Process articles in the chapter
            for article in chapter.get("articles", []):
                article["global_number"] = str(global_count)
                global_count += 1
            
            # Process articles in parts
            for part in chapter.get("parts", []):
                for article in part.get("articles", []):
                    article["global_number"] = str(global_count)
                    global_count += 1
    
    def post_process_structure(self):
        """
        Fix structural issues in the extracted constitution.
        """
        # Fix article titles to ensure they don't contain clause content
        self.fix_article_titles()
        
        # Fix clause numbering
        self.fix_clause_numbering()
        
        # Ensure global article numbering is consistent
        self.ensure_global_numbering()
        
        # Standardize title casing
        chapters = self.constitution["constitution"]["chapters"]
        for chapter in chapters:
            # Standardize article titles
            for article in chapter.get("articles", []):
                article["title"] = self.standardize_title_casing(article["title"])
            
            # Standardize part titles
            for part in chapter.get("parts", []):
                part["title"] = self.standardize_title_casing(part["title"])
                
                # Standardize article titles in parts
                for article in part.get("articles", []):
                    article["title"] = self.standardize_title_casing(article["title"])
    
    def save_to_json(self, output_path):
        """Save constitution to JSON file."""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.constitution, f, indent=2, ensure_ascii=False)
            logger.info(f"Constitution saved to: {output_path}")
        except Exception as e:
            logger.error(f"Error saving to JSON: {e}")
            raise


def main():
    """Main function to extract constitution from DOCX file."""
    # Set paths
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(os.path.dirname(script_dir))
    docx_path = os.path.join(project_dir, 'src', 'data', 'source', 'TheConstitutionOfKenya.docx')
    output_path = os.path.join(project_dir, 'src', 'data', 'processed', 'constitution.json')
    
    # Extract constitution
    extractor = ConstitutionDocxExtractor(docx_path)
    constitution = extractor.extract()
    
    # Log statistics
    chapter_count = len(constitution["constitution"]["chapters"])
    article_count = sum(len(ch.get("articles", [])) + sum(len(p.get("articles", [])) for p in ch.get("parts", [])) 
                        for ch in constitution["constitution"]["chapters"])
    clause_count = sum(sum(len(a.get("clauses", [])) for a in ch.get("articles", []) + 
                          [a for p in ch.get("parts", []) for a in p.get("articles", [])]) 
                      for ch in constitution["constitution"]["chapters"])
    sub_clause_count = sum(sum(sum(len(c.get("sub_clauses", [])) for c in a.get("clauses", [])) 
                              for a in ch.get("articles", []) + 
                              [a for p in ch.get("parts", []) for a in p.get("articles", [])]) 
                          for ch in constitution["constitution"]["chapters"])
    
    logger.info(f"Processed {chapter_count} chapters")
    logger.info(f"Processed {article_count} articles")
    logger.info(f"Processed {clause_count} clauses")
    logger.info(f"Processed {sub_clause_count} sub-clauses")
    
    # Save constitution to JSON
    extractor.save_to_json(output_path)
    
    logger.info("Constitution extraction complete:")
    logger.info(f"  - {chapter_count} chapters")
    logger.info(f"  - {article_count} articles")
    logger.info(f"  - {clause_count} clauses")
    logger.info(f"  - {sub_clause_count} sub-clauses")


if __name__ == "__main__":
    main()
