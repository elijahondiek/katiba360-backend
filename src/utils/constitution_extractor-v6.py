#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Constitution Extractor - Version 6
---------------------------------
This script extracts the structure and content of a constitution from a DOCX file
and converts it into a structured JSON format.

This version includes improved preamble extraction, better chapter title handling,
enhanced clause detection, and fixes for article placement.
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
        self.chapter_title_pattern = re.compile(r'^CHAPTER\s+[A-Z]+\s*[—–-]\s*(.+)$')
        self.part_pattern = re.compile(r'^PART\s+([0-9]+)')
        self.part_title_pattern = re.compile(r'^PART\s+[0-9]+\s*[—–-]\s*(.+)$')
        self.article_title_pattern = re.compile(r'^Article\s+([0-9]+)[:\s—–-]+(.+)$', re.IGNORECASE)
        self.article_number_pattern = re.compile(r'^([0-9]+)\.\s+(.+)$')
        self.clause_pattern = re.compile(r'^\(([0-9]+)\)')
        self.sub_clause_pattern = re.compile(r'^\(([a-z])\)')
        self.bullet_pattern = re.compile(r'^[•\-*]\s+(.+)$')
        self.preamble_pattern = re.compile(r'^(We,\s+the\s+people|PREAMBLE)', re.IGNORECASE)
        
        # Track current context
        self.current_chapter = None
        self.current_part = None
        self.current_article = None
        self.current_clause = None
        self.current_sub_clause = None
        self.global_article_count = 0
        self.in_preamble = False
        self.preamble_text = []
        
    def extract(self):
        """Extract constitution structure from DOCX file."""
        # Extract text from DOCX
        paragraphs = self.extract_text_from_docx()
        
        # First pass: identify preamble
        self.identify_preamble(paragraphs)
        
        # Second pass: process paragraphs to build structure
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
    
    def identify_preamble(self, paragraphs):
        """Identify and extract preamble from the document."""
        in_preamble = False
        preamble_text = []
        
        for text, style in paragraphs:
            # Check if this is the start of the preamble
            if not in_preamble and self.preamble_pattern.match(text):
                in_preamble = True
                # Add this line if it's not just "PREAMBLE"
                if not text.upper() == "PREAMBLE":
                    preamble_text.append(text)
                continue
            
            # If we're in the preamble, collect text until we hit a chapter
            if in_preamble:
                if self.chapter_pattern.match(text):
                    in_preamble = False
                    continue
                
                # Add text to preamble
                preamble_text.append(text)
        
        # Join preamble text
        if preamble_text:
            self.constitution["constitution"]["preamble"] = " ".join(preamble_text)
            logger.info(f"Extracted preamble: {self.constitution['constitution']['preamble'][:50]}...")
    
    def process_paragraphs(self, paragraphs):
        """Process paragraphs to build constitution structure."""
        for text, style in paragraphs:
            # Skip empty lines
            if not text:
                continue
            
            # Skip if we're still in preamble
            if self.in_preamble:
                if self.chapter_pattern.match(text):
                    self.in_preamble = False
                else:
                    continue
            
            # Process chapter
            chapter_match = self.chapter_pattern.match(text)
            if chapter_match:
                chapter_number = chapter_match.group(1)
                
                # Extract title from the same line if it contains a dash
                chapter_title = ""
                title_match = self.chapter_title_pattern.match(text)
                if title_match:
                    chapter_title = title_match.group(1).strip()
                
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
                continue
            
            # If we don't have a chapter yet, create a default one
            if not self.current_chapter:
                self.current_chapter = {
                    "number": "",
                    "title": "",
                    "articles": [],
                    "parts": [],
                    "preamble": ""
                }
                self.constitution["constitution"]["chapters"].append(self.current_chapter)
                logger.info("Created default chapter")
            
            # Process chapter title (if it's on the next line)
            if self.current_chapter and not self.current_chapter["title"] and not self.part_pattern.match(text) and not self.article_title_pattern.match(text):
                # If this looks like a chapter title (not too long, not a clause)
                if len(text.split()) < 10 and not text.startswith('(') and style in ['Heading 1', 'Heading 2', '']:
                    self.current_chapter["title"] = text
                    logger.info(f"Set chapter title: {text}")
                    continue
            
            # Process part
            part_match = self.part_pattern.match(text)
            if part_match:
                part_number = part_match.group(1)
                
                # Extract title from the same line if it contains a dash
                part_title = ""
                title_match = self.part_title_pattern.match(text)
                if title_match:
                    part_title = title_match.group(1).strip()
                
                self.current_part = {
                    "number": part_number,
                    "title": part_title,
                    "articles": []
                }
                self.current_chapter["parts"].append(self.current_part)
                self.current_article = None
                self.current_clause = None
                
                logger.info(f"Found Part {part_number}: {part_title}")
                continue
            
            # Process part title (if it's on the next line)
            if self.current_part and not self.current_part["title"] and not self.article_title_pattern.match(text):
                # If this looks like a part title (not too long, not a clause)
                if len(text.split()) < 10 and not text.startswith('(') and style in ['Heading 2', 'Heading 3', '']:
                    self.current_part["title"] = text
                    logger.info(f"Set part title: {text}")
                    continue
            
            # Process article
            article_title_match = self.article_title_pattern.match(text)
            article_number_match = self.article_number_pattern.match(text)
            
            if article_title_match or article_number_match or (style in ['Heading 3', 'Heading 4'] and len(text.split()) < 10):
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
                logger.info(f"Found Sub-clause {sub_clause_letter} in Clause {self.current_clause['number']}")
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
                    logger.info(f"Appended to article title: {text}")
    
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
    
    def fix_article_placement(self):
        """Fix articles that are in the wrong chapter or part."""
        # Identify chapters with no number or title
        empty_chapters = []
        for i, chapter in enumerate(self.constitution["constitution"]["chapters"]):
            if not chapter["number"] and not chapter["title"]:
                empty_chapters.append(i)
        
        # Move articles from empty chapters to appropriate chapters
        for i in reversed(empty_chapters):
            empty_chapter = self.constitution["constitution"]["chapters"][i]
            
            # Move articles to appropriate chapters based on content
            for article in empty_chapter.get("articles", []):
                # Try to determine which chapter this article belongs to
                title = article.get("title", "").lower()
                
                # Default to chapter 4 (Bill of Rights) if we can't determine
                target_chapter_index = 3  # 0-indexed, so chapter 4
                
                # Look for keywords to determine chapter
                if "sovereignty" in title or "supremacy" in title:
                    target_chapter_index = 0  # Chapter 1
                elif "republic" in title or "state" in title or "territory" in title:
                    target_chapter_index = 1  # Chapter 2
                elif "citizenship" in title or "registration" in title:
                    target_chapter_index = 2  # Chapter 3
                
                # Ensure target chapter exists
                while len(self.constitution["constitution"]["chapters"]) <= target_chapter_index:
                    self.constitution["constitution"]["chapters"].append({
                        "number": str(len(self.constitution["constitution"]["chapters"]) + 1),
                        "title": "",
                        "articles": [],
                        "parts": [],
                        "preamble": ""
                    })
                
                # Add article to target chapter
                self.constitution["constitution"]["chapters"][target_chapter_index]["articles"].append(article)
                logger.info(f"Moved article '{article['title']}' to chapter {target_chapter_index + 1}")
            
            # Remove the empty chapter
            del self.constitution["constitution"]["chapters"][i]
            logger.info(f"Removed empty chapter at index {i}")
    
    def fix_clause_separation(self):
        """Fix clauses that contain multiple clauses merged together."""
        chapters = self.constitution["constitution"]["chapters"]
        
        for chapter in chapters:
            # Process articles in the chapter
            for article in chapter.get("articles", []):
                # Check each clause
                new_clauses = []
                for clause in article.get("clauses", []):
                    text = clause.get("text", "")
                    
                    # Look for patterns like "(2) Some text" within the clause text
                    clause_splits = re.split(r'\s+\(([0-9]+)\)\s+', text)
                    
                    if len(clause_splits) > 2:  # We have multiple clauses
                        # First part is the original clause text up to the first split
                        new_clauses.append({
                            "number": clause["number"],
                            "text": clause_splits[0],
                            "sub_clauses": clause.get("sub_clauses", [])[:]  # Copy sub-clauses
                        })
                        
                        # Process remaining splits (alternating between clause numbers and text)
                        for i in range(1, len(clause_splits), 2):
                            if i + 1 < len(clause_splits):
                                new_clauses.append({
                                    "number": clause_splits[i],
                                    "text": f"({clause_splits[i]}) {clause_splits[i+1]}",
                                    "sub_clauses": []
                                })
                    else:
                        # No splits needed, keep the original clause
                        new_clauses.append(clause)
                
                # Replace with new clauses
                if len(new_clauses) > len(article["clauses"]):
                    logger.info(f"Split {len(article['clauses'])} clauses into {len(new_clauses)} clauses for article {article['title']}")
                    article["clauses"] = new_clauses
            
            # Process articles in parts
            for part in chapter.get("parts", []):
                for article in part.get("articles", []):
                    # Check each clause
                    new_clauses = []
                    for clause in article.get("clauses", []):
                        text = clause.get("text", "")
                        
                        # Look for patterns like "(2) Some text" within the clause text
                        clause_splits = re.split(r'\s+\(([0-9]+)\)\s+', text)
                        
                        if len(clause_splits) > 2:  # We have multiple clauses
                            # First part is the original clause text up to the first split
                            new_clauses.append({
                                "number": clause["number"],
                                "text": clause_splits[0],
                                "sub_clauses": clause.get("sub_clauses", [])[:]  # Copy sub-clauses
                            })
                            
                            # Process remaining splits (alternating between clause numbers and text)
                            for i in range(1, len(clause_splits), 2):
                                if i + 1 < len(clause_splits):
                                    new_clauses.append({
                                        "number": clause_splits[i],
                                        "text": f"({clause_splits[i]}) {clause_splits[i+1]}",
                                        "sub_clauses": []
                                    })
                        else:
                            # No splits needed, keep the original clause
                            new_clauses.append(clause)
                    
                    # Replace with new clauses
                    if len(new_clauses) > len(article["clauses"]):
                        logger.info(f"Split {len(article['clauses'])} clauses into {len(new_clauses)} clauses for article {article['title']}")
                        article["clauses"] = new_clauses
    
    def post_process_structure(self):
        """
        Fix structural issues: merge spurious chapters, move misplaced articles, fix clause content,
        standardize title casing, ensure proper numbering, and fix any remaining structural issues.
        """
        # Fix misplaced clause content in titles
        self.fix_misplaced_clause_content()
        
        # Fix articles that are in the wrong chapter
        self.fix_article_placement()
        
        # Fix clauses that contain multiple clauses merged together
        self.fix_clause_separation()
        
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
