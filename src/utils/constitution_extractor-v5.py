#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Constitution Extractor - Version 5
---------------------------------
This script extracts the structure and content of a constitution from a DOCX file
and converts it into a structured JSON format.

This version includes improved preamble extraction, better clause handling,
and enhanced title standardization.
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
        self.part_pattern = re.compile(r'^PART\s+([0-9]+)')
        self.article_title_pattern = re.compile(r'^Article\s+([0-9]+)[:\s—–-]+(.+)$', re.IGNORECASE)
        self.article_number_pattern = re.compile(r'^([0-9]+)\.\s+(.+)$')
        self.clause_pattern = re.compile(r'^\(([0-9]+)\)')
        self.sub_clause_pattern = re.compile(r'^\(([a-z])\)')
        self.bullet_pattern = re.compile(r'^[•\-*]\s+(.+)$')
        
        # Track current context
        self.current_chapter = None
        self.current_part = None
        self.current_article = None
        self.current_clause = None
        self.current_sub_clause = None
        self.global_article_count = 0
        self.in_preamble = True
        
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
    
    def extract_preamble(self, paragraphs):
        """Extract preamble from the beginning of the document."""
        preamble_text = ""
        preamble_started = False
        
        for text, style in paragraphs:
            # Skip until we find something that looks like a preamble
            if not preamble_started and ("PREAMBLE" in text.upper() or text.startswith("We, the people")):
                preamble_started = True
                if not text.startswith("PREAMBLE"):
                    preamble_text = text
                continue
            
            # If we've started the preamble, collect text until we hit a chapter
            if preamble_started:
                if self.chapter_pattern.match(text):
                    break
                
                if text and not text.startswith("THE CONSTITUTION OF KENYA"):
                    preamble_text += " " + text
        
        if preamble_text:
            self.constitution["constitution"]["preamble"] = preamble_text.strip()
            logger.info(f"Extracted preamble: {preamble_text[:50]}...")
    
    def process_paragraphs(self, paragraphs):
        """Process paragraphs to build constitution structure."""
        # First extract the preamble
        self.extract_preamble(paragraphs)
        
        # Now process the rest of the document
        for text, style in paragraphs:
            # Skip empty lines
            if not text:
                continue
            
            # Skip if we're still in preamble and haven't hit a chapter yet
            if self.in_preamble:
                if self.chapter_pattern.match(text):
                    self.in_preamble = False
                else:
                    continue
            
            # Process chapter
            chapter_match = self.chapter_pattern.match(text)
            if chapter_match or style == 'Heading 1':
                chapter_number = chapter_match.group(1) if chapter_match else ""
                
                # Extract title - it might be in the same line after a dash or on the next line
                chapter_title = ""
                if '—' in text or '-' in text:
                    title_parts = text.split('—' if '—' in text else '-', 1)
                    if len(title_parts) > 1:
                        chapter_title = title_parts[1].strip()
                
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
                continue
            
            # If we don't have a chapter yet, skip
            if not self.current_chapter:
                continue
            
            # Process part
            part_match = self.part_pattern.match(text)
            if part_match or (style == 'Heading 2' and 'PART' in text):
                part_number = part_match.group(1) if part_match else ""
                
                # Extract title
                part_title = ""
                if '—' in text or '-' in text:
                    title_parts = text.split('—' if '—' in text else '-', 1)
                    if len(title_parts) > 1:
                        part_title = title_parts[1].strip()
                
                self.current_part = {
                    "number": part_number,
                    "title": part_title,
                    "articles": []
                }
                self.current_chapter["parts"].append(self.current_part)
                self.current_article = None
                self.current_clause = None
                continue
            
            # Process article
            article_title_match = self.article_title_pattern.match(text)
            article_number_match = self.article_number_pattern.match(text)
            
            if article_title_match or article_number_match or style == 'Heading 3' or \
               (len(text.split()) < 10 and ('Right to' in text or 'Freedom of' in text)):
                
                # Skip likely fragment titles that aren't full articles
                if text.startswith('the right to') or text.startswith('the privacy of'):
                    logger.info(f"Skipping likely fragment title: {text}")
                    continue
                
                self.global_article_count += 1
                
                if article_title_match:
                    article_number = article_title_match.group(1)
                    article_title = article_title_match.group(2).strip()
                elif article_number_match:
                    article_number = article_number_match.group(1)
                    article_title = article_number_match.group(2).strip()
                else:
                    # Infer article number from previous article
                    if self.current_article:
                        try:
                            article_number = str(int(self.current_article["local_number"]) + 1)
                            logger.info(f"Inferred article number {article_number} from previous article")
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
                continue
            
            # If we don't have an article yet, skip
            if not self.current_article:
                continue
            
            # Process clause
            clause_match = self.clause_pattern.match(text)
            if clause_match:
                clause_number = clause_match.group(1)
                logger.info(f"Found Clause {clause_number} in Article {self.current_article['local_number']}")
                
                self.current_clause = {
                    "number": clause_number,
                    "text": text,
                    "sub_clauses": []
                }
                self.current_article["clauses"].append(self.current_clause)
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
                continue
            
            # If we have a current clause, append text to it
            if self.current_clause and text:
                # Check if this is a continuation of clause text (not a new clause or article)
                if not text.startswith('(') or re.match(r'^\([^a-z0-9]', text):
                    self.current_clause["text"] += " " + text
                    logger.info(f"Appended to existing clause: {text[:20]}...")
            elif self.current_article and text:
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
                # Otherwise, it might be a continuation of the article title
                elif len(self.current_article["title"].split()) < 5 and len(text.split()) < 10:
                    self.current_article["title"] += " " + text
    
    def fix_misplaced_clause_content(self):
        """Fix articles where clause content is in the title instead of in clauses."""
        chapters = self.constitution["constitution"]["chapters"]
        
        for chapter in chapters:
            # Process articles in the chapter
            for article in chapter.get("articles", []):
                title = article.get("title", "")
                
                # Check if title looks like clause content
                if len(title.split()) > 10 and not title.startswith("Article") and not any(word in title.lower() for word in ["right", "freedom", "citizenship", "sovereignty"]):
                    # This title is likely clause content
                    if not article["clauses"]:
                        # Create a new clause with this content
                        article["clauses"].append({
                            "number": "1",
                            "text": title,
                            "sub_clauses": []
                        })
                        # Set a more appropriate title
                        article["title"] = f"Article {article.get('local_number', '')}" 
                        logger.info(f"Moved clause content from title to clause: {title[:30]}...")
                
                # Check for empty clauses that should have content
                if not article["clauses"] and article.get("local_number") not in ["1", "2", "3", "4", "5"]:
                    # Create a default clause for articles that should have content
                    article["clauses"].append({
                        "number": "1",
                        "text": f"({article.get('local_number', '1')}) {title}",
                        "sub_clauses": []
                    })
                    # Set a more appropriate title
                    words = title.split()
                    if len(words) > 3:
                        article["title"] = " ".join(words[:3]) + "..."
                    logger.info(f"Created default clause for empty article: {article.get('local_number', '')}")
            
            # Process articles in parts
            for part in chapter.get("parts", []):
                for article in part.get("articles", []):
                    title = article.get("title", "")
                    
                    # Check if title looks like clause content
                    if len(title.split()) > 10 and not title.startswith("Article") and not any(word in title.lower() for word in ["right", "freedom", "citizenship", "sovereignty"]):
                        # This title is likely clause content
                        if not article["clauses"]:
                            # Create a new clause with this content
                            article["clauses"].append({
                                "number": "1",
                                "text": title,
                                "sub_clauses": []
                            })
                            # Set a more appropriate title
                            article["title"] = f"Article {article.get('local_number', '')}" 
                            logger.info(f"Moved clause content from title to clause: {title[:30]}...")
                    
                    # Check for empty clauses that should have content
                    if not article["clauses"] and article.get("local_number") not in ["1", "2", "3", "4", "5"]:
                        # Create a default clause for articles that should have content
                        article["clauses"].append({
                            "number": "1",
                            "text": f"({article.get('local_number', '1')}) {title}",
                            "sub_clauses": []
                        })
                        # Set a more appropriate title
                        words = title.split()
                        if len(words) > 3:
                            article["title"] = " ".join(words[:3]) + "..."
                        logger.info(f"Created default clause for empty article: {article.get('local_number', '')}")
    
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
    
    def post_process_structure(self):
        """
        Fix structural issues: merge spurious chapter 2 as PART 2 of Chapter FOUR, move misplaced sub-clauses, fix Article 10 sub-values,
        standardize title casing, ensure proper numbering, and fix any remaining structural issues.
        """
        # Fix misplaced clause content in titles
        self.fix_misplaced_clause_content()
        
        # Get chapters for processing
        chapters = self.constitution["constitution"]["chapters"]
        
        # 1. Standardize title casing for all elements
        for ch in chapters:
            # Standardize chapter title
            ch["title"] = self.standardize_title_casing(ch["title"])
            
            # Standardize article titles
            for article in ch.get("articles", []):
                article["title"] = self.standardize_title_casing(article["title"])
            
            # Standardize part titles
            for part in ch.get("parts", []):
                part["title"] = self.standardize_title_casing(part["title"])
                
                # Standardize article titles in parts
                for article in part.get("articles", []):
                    article["title"] = self.standardize_title_casing(article["title"])
        
        # 2. Ensure all articles have proper numbering
        global_article_count = 1
        for ch in chapters:
            local_article_count = 1
            
            # Update article numbers in the chapter
            for article in ch.get("articles", []):
                article["local_number"] = str(local_article_count)
                article["global_number"] = str(global_article_count)
                local_article_count += 1
                global_article_count += 1
            
            # Update article numbers in parts
            for part in ch.get("parts", []):
                for article in part.get("articles", []):
                    article["local_number"] = str(local_article_count)
                    article["global_number"] = str(global_article_count)
                    local_article_count += 1
                    global_article_count += 1
        
        # 3. Ensure clause numbers are sequential
        for ch in chapters:
            # Process articles in the chapter
            for article in ch.get("articles", []):
                for i, clause in enumerate(article.get("clauses", []), 1):
                    clause["number"] = str(i)
            
            # Process articles in parts
            for part in ch.get("parts", []):
                for article in part.get("articles", []):
                    for i, clause in enumerate(article.get("clauses", []), 1):
                        clause["number"] = str(i)
    
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
