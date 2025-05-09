#!/usr/bin/env python3
"""
Constitution Extractor

This script extracts text from the Kenyan Constitution PDF and structures it into
a hierarchical JSON format with chapters, articles, clauses, and sub-clauses.
"""

import fitz  # PyMuPDF
import re
import json
import os
from pathlib import Path
import logging
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConstitutionExtractor:
    """Class to extract and structure content from the Kenyan Constitution PDF."""
    
    def __init__(self, pdf_path):
        """
        Initialize the extractor with the path to the PDF.
        
        Args:
            pdf_path (str): Path to the Constitution PDF file
        """
        self.pdf_path = pdf_path
        self.constitution = {
            "constitution": {
                "title": "The Constitution of Kenya",
                "chapters": []
            }
        }
        
        # Define regex patterns for identifying constitutional elements
        self.chapter_pattern = re.compile(r'CHAPTER\s+([A-Z]+)\s+([A-Z][A-Z\s]+)')
        self.article_title_pattern = re.compile(r'([A-Za-z,\s]+)\.\s*(\d+)\.')
        self.clause_pattern = re.compile(r'\((\d+)\)\s*([^\(]+)')
        self.sub_clause_pattern = re.compile(r'\(([a-z])\)\s*([^\(]+)')
        
    def extract_text_from_pdf(self):
        """
        Extract text from the PDF document page by page for better handling of structure.
        
        Returns:
            list: A list of text content from each page
        """
        try:
            doc = fitz.open(self.pdf_path)
            pages_text = []
            
            logger.info(f"Total pages in PDF: {doc.page_count}")
            
            # Extract text from each page and store separately
            for page_num in range(doc.page_count):
                page = doc[page_num]
                # Use a structured text extraction to preserve layout better
                page_text = page.get_text("text")
                pages_text.append(page_text)
                
                # Log the first few pages for debugging
                if page_num < 2:
                    logger.info(f"Sample from page {page_num+1} (first 100 chars):\n{page_text[:100]}...")
            
            doc.close()
            
            # Combine all pages into a single text for debugging
            full_text = "\n\n".join(pages_text)
            with open("raw_constitution.txt", "w", encoding="utf-8") as f:
                f.write(full_text)
            
            return pages_text
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise
    
    def identify_chapters(self, pages_text):
        """
        Identify chapters in the constitution from page text.
        
        Args:
            pages_text (list): List of text content from each page
            
        Returns:
            list: List of identified chapters with their page ranges
        """
        chapters = []
        combined_text = "\n".join(pages_text)
        
        # Look for chapter headings
        chapter_matches = list(self.chapter_pattern.finditer(combined_text))
        
        logger.info(f"Found {len(chapter_matches)} chapters")
        
        # If no chapters found, try a more relaxed pattern
        if len(chapter_matches) == 0:
            logger.info("No chapters found with standard pattern, trying alternative pattern")
            alt_chapter_pattern = re.compile(r'CHAPTER\s+([A-Z]+)\s+([A-Z][A-Z\s]+)')
            chapter_matches = list(alt_chapter_pattern.finditer(combined_text))
            logger.info(f"Found {len(chapter_matches)} chapters with alternative pattern")
        
        # Process each chapter match
        for i, match in enumerate(chapter_matches):
            try:
                chapter_num = match.group(1).strip()
                chapter_title = match.group(2).strip()
                
                # Create chapter entry
                chapter = {
                    "number": chapter_num,
                    "title": chapter_title,
                    "start_pos": match.start(),
                    "end_pos": len(combined_text) if i == len(chapter_matches) - 1 else chapter_matches[i+1].start(),
                    "articles": []
                }
                
                chapters.append(chapter)
                logger.info(f"Identified Chapter {chapter_num}: {chapter_title}")
                
            except Exception as e:
                logger.error(f"Error processing chapter match: {e}")
        
        return chapters, combined_text
    
    def extract_articles(self, chapter, combined_text):
        """
        Extract articles from a chapter.
        
        Args:
            chapter (dict): Chapter dictionary with start_pos and end_pos
            combined_text (str): Combined text of all pages
            
        Returns:
            list: List of article dictionaries
        """
        articles = []
        
        # Extract chapter content
        chapter_content = combined_text[chapter["start_pos"]:chapter["end_pos"]]
        
        # Find all article titles in this chapter
        article_matches = list(self.article_title_pattern.finditer(chapter_content))
        
        logger.info(f"Found {len(article_matches)} articles in Chapter {chapter['number']}")
        
        # Process each article
        for i, match in enumerate(article_matches):
            try:
                article_title = match.group(1).strip()
                article_num = match.group(2).strip()
                
                # Determine article content boundaries
                start_pos = match.end()
                end_pos = len(chapter_content) if i == len(article_matches) - 1 else article_matches[i+1].start()
                article_content = chapter_content[start_pos:end_pos]
                
                # Create article object
                article = {
                    "number": article_num,
                    "title": article_title,
                    "clauses": self.extract_clauses(article_content)
                }
                
                articles.append(article)
                
            except Exception as e:
                logger.error(f"Error processing article: {e}")
        
        return articles
    
    def extract_clauses(self, article_content):
        """
        Extract clauses from article content.
        
        Args:
            article_content (str): Content of an article
            
        Returns:
            list: List of clause dictionaries
        """
        clauses = []
        
        # Find all clauses in this article
        clause_matches = list(self.clause_pattern.finditer(article_content))
        
        # If no clauses found, treat the entire article content as a single clause
        if not clause_matches and article_content.strip():
            clauses.append({
                "number": "1",
                "text": article_content.strip(),
                "sub_clauses": []
            })
            return clauses
        
        # Process each clause
        for i, match in enumerate(clause_matches):
            try:
                clause_num = match.group(1).strip()
                clause_text = match.group(2).strip()
                
                # Create clause object
                clause = {
                    "number": clause_num,
                    "text": clause_text,
                    "sub_clauses": self.extract_sub_clauses(clause_text)
                }
                
                clauses.append(clause)
                
            except Exception as e:
                logger.error(f"Error processing clause: {e}")
        
        return clauses
    
    def extract_sub_clauses(self, clause_text):
        """
        Extract sub-clauses from clause text.
        
        Args:
            clause_text (str): Content of a clause
            
        Returns:
            list: List of sub-clause dictionaries
        """
        sub_clauses = []
        
        # Find all sub-clauses in this clause
        sub_clause_matches = list(self.sub_clause_pattern.finditer(clause_text))
        
        # Process each sub-clause
        for match in sub_clause_matches:
            try:
                sub_letter = match.group(1).strip()
                sub_text = match.group(2).strip()
                
                # Create sub-clause object
                sub_clause = {
                    "letter": sub_letter,
                    "text": sub_text
                }
                
                sub_clauses.append(sub_clause)
                
            except Exception as e:
                logger.error(f"Error processing sub-clause: {e}")
        
        return sub_clauses
    
    def clean_text(self, text):
        """
        Clean the extracted text to make it easier to process.
        
        Args:
            text (str): Raw text from PDF
            
        Returns:
            str: Cleaned text
        """
        # Remove page numbers
        text = re.sub(r'\n\d+\n', '\n', text)
        
        # Remove headers and footers
        text = text.replace('Constitution of Kenya', '')
        text = re.sub(r'\[Rev\.\s*\d+\]', '', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Add line breaks before chapter headings for better parsing
        text = text.replace('CHAPTER', '\n\nCHAPTER')
        
        # Write cleaned text to file for debugging
        with open("cleaned_constitution.txt", "w", encoding="utf-8") as f:
            f.write(text)
            
        return text
    
    def process(self):
        """
        Process the PDF and extract the structured constitution.
        
        Returns:
            dict: The structured constitution data
        """
        try:
            logger.info(f"Processing PDF: {self.pdf_path}")
            
            # Extract text from PDF page by page
            pages_text = self.extract_text_from_pdf()
            logger.info(f"Extracted text from {len(pages_text)} pages")
            
            # Identify chapters and get combined text
            chapters, combined_text = self.identify_chapters(pages_text)
            logger.info(f"Identified {len(chapters)} chapters")
            
            # Process each chapter to extract articles, clauses, and sub-clauses
            processed_chapters = []
            for chapter in chapters:
                # Extract articles for this chapter
                articles = self.extract_articles(chapter, combined_text)
                
                # Create the final chapter structure
                processed_chapter = {
                    "number": chapter["number"],
                    "title": chapter["title"],
                    "articles": articles
                }
                
                processed_chapters.append(processed_chapter)
                logger.info(f"Chapter {chapter['number']} processed with {len(articles)} articles")
            
            # Set the chapters in the constitution structure
            self.constitution["constitution"]["chapters"] = processed_chapters
            
            return self.constitution
        except Exception as e:
            logger.error(f"Error processing constitution: {e}")
            raise
    
    def save_to_json(self, output_path):
        """
        Save the structured constitution to a JSON file.
        
        Args:
            output_path (str): Path to save the JSON file
        """
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.constitution, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Constitution saved to {output_path}")
        except Exception as e:
            logger.error(f"Error saving to JSON: {e}")
            raise
    
def main():
    """
    Main function to extract and save the constitution.
    """
    # Get the absolute path to the PDF
    base_dir = Path(__file__).resolve().parent.parent.parent
    pdf_path = base_dir / "src" / "data" / "source" / "TheConstitutionOfKenya.pdf"
    
    # Define output path
    output_path = base_dir / "src" / "data" / "processed" / "constitution.json"
    
    # Create the extractor and process the PDF
    extractor = ConstitutionExtractor(str(pdf_path))
    extractor.process()
    extractor.save_to_json(str(output_path))
    
    logger.info("Constitution extraction complete")


if __name__ == "__main__":
    main()
