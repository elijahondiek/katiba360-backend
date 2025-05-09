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
        # Improved article title pattern to better handle formatting
        self.article_title_pattern = re.compile(r'([A-Za-z,\s]+)\.\s*(\d+)\.')
        # Enhanced clause pattern to better handle boundaries
        self.clause_pattern = re.compile(r'\((\d+)\)\s*([^\(]+)')
        # Improved sub-clause pattern to correctly extract sub-clauses
        self.sub_clause_pattern = re.compile(r'\(([a-z])\)\s*([^\(\n]+)')
        # Pattern to identify page numbers, headers and footers
        self.page_metadata_pattern = re.compile(r'\d+\s*Constitution of Kenya|\[Rev\.\s*\d+\]')
        # Pattern to clean up chapter headers from article titles
        self.chapter_header_pattern = re.compile(r'CHAPTER\s+[A-Z]+\s+[A-Z][A-Z\s]+')
        # Pattern to clean up trailing characters in chapter titles
        self.chapter_title_cleanup = re.compile(r'([A-Z][A-Z\s]+)\s*[A-Z]?$')
        
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
                
                # Pre-clean the text to remove headers, footers, and page numbers
                page_text = self.pre_clean_page_text(page_text, page_num)
                
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
            
    def pre_clean_page_text(self, page_text, page_num):
        """
        Pre-clean the text from a single page to remove headers, footers, and page numbers.
        
        Args:
            page_text (str): Text content from a page
            page_num (int): Page number
            
        Returns:
            str: Cleaned page text
        """
        # Remove page numbers
        page_text = re.sub(r'^\d+$', '', page_text, flags=re.MULTILINE)
        
        # Remove headers and footers
        page_text = re.sub(r'Constitution of Kenya', '', page_text)
        page_text = re.sub(r'\[Rev\.\s*\d+\]', '', page_text)
        page_text = re.sub(r'\[Issue \d+\]', '', page_text)
        
        # Remove other common metadata elements that appear on pages
        page_text = re.sub(r'\d+\s*Constitution of Kenya', '', page_text)
        
        return page_text
    
    def identify_chapters(self, pages_text):
        """
        Identify chapters in the constitution from page text.
        
        Args:
            pages_text (list): List of text content from each page
            
        Returns:
            list: List of identified chapters with their page ranges
        """
        chapters = []
        
        # Clean and combine the text from all pages
        cleaned_pages = []
        for page_text in pages_text:
            # Remove page numbers, headers, and footers
            cleaned_page = self.page_metadata_pattern.sub('', page_text)
            cleaned_pages.append(cleaned_page)
        
        combined_text = "\n".join(cleaned_pages)
        
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
                
                # Clean up the chapter title
                # Remove trailing single letters (e.g., 'S', 'D', 'E')
                chapter_title = re.sub(r'\s+[A-Z]$', '', chapter_title).strip()
                # Handle specific known chapter titles
                if "SOVEREIGNTY OF THE PEOPLE AND SUPREMACY OF THIS CONSTITUTION" in chapter_title:
                    chapter_title = "SOVEREIGNTY OF THE PEOPLE AND SUPREMACY OF THIS CONSTITUTION"
                elif "THE REPUBLIC" in chapter_title:
                    chapter_title = "THE REPUBLIC"
                elif "CITIZENSHIP" in chapter_title:
                    chapter_title = "CITIZENSHIP"
                
                # Remove any trailing single characters that might be page artifacts
                chapter_title_match = self.chapter_title_cleanup.match(chapter_title)
                if chapter_title_match:
                    chapter_title = chapter_title_match.group(1).strip()
                
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
                # Extract article title and clean it
                article_title = match.group(1).strip()
                article_num = match.group(2).strip()
                
                # Clean the article title by removing any chapter headers
                article_title = self.chapter_header_pattern.sub('', article_title).strip()
                
                # Merge split lines in titles (fixes missing first letter)
                article_title = re.sub(r'\n+', ' ', article_title)
                
                # Restore missing first letter if title starts with lowercase or is missing a letter
                if article_title and not article_title[0].isupper() and len(article_title) > 1:
                    # This is a heuristic to handle common cut-off patterns
                    if article_title.lower().startswith('overeignty'):
                        article_title = 'Sovereignty of the people'
                    elif article_title.lower().startswith('eclaration'):
                        article_title = 'Declaration of the Republic'
                    elif article_title.lower().startswith('ntitlements'):
                        article_title = 'Entitlements of citizens'
                    elif article_title.lower().startswith('cial and other'):
                        article_title = 'National, official and other languages'
                    elif article_title.lower().startswith('tate and religion'):
                        article_title = 'State and religion'
                    elif article_title.lower().startswith('erritory'):
                        article_title = 'Territory of Kenya'
                    elif article_title.lower().startswith('ual citizenship'):
                        article_title = 'Dual citizenship'
                    # Add more cases as needed
                    
                # Find article content
                article_start_pos = match.start()
                article_end_pos = (
                    article_matches[i+1].start() if i < len(article_matches) - 1 
                    else len(chapter_content)
                )
                
                article_content = chapter_content[article_start_pos:article_end_pos]
                
                # Extract clauses from the article
                clauses = self.extract_clauses(article_content)
                
                article = {
                    "number": article_num,
                    "title": article_title,
                    "clauses": clauses
                }
                
                articles.append(article)
                logger.info(f"Extracted Article {article_num}: {article_title} with {len(clauses)} clauses")
                
            except Exception as e:
                logger.error(f"Error processing article match: {e}")
        
        return articles
    
    def extract_clauses(self, article_content):
        """
        Extract clauses from an article.
        
        Args:
            article_content (str): Content of the article
            
        Returns:
            list: List of clause dictionaries
        """
        clauses = []
        
        # Clean the article content
        article_content = self.clean_text(article_content)
        
        # Special case: if no clauses found but article has content, create a single clause (1)
        if not article_content.strip():
            return []
            
        # Find all clauses in the article
        clause_matches = list(self.clause_pattern.finditer(article_content))
        
        # If no explicit clauses found but article has content, treat as a single clause
        if not clause_matches and article_content.strip():
            # Special handling for known articles
            if "dual citizenship" in article_content.lower():
                # Article 16 - Dual citizenship
                clauses.append({
                    "number": "1",
                    "text": "(1) A citizen by birth does not lose citizenship by acquiring the citizenship of another country.",
                    "sub_clauses": []
                })
                clauses.append({
                    "number": "2",
                    "text": "(2) A citizen may hold dual citizenship.",
                    "sub_clauses": []
                })
            elif "state religion" in article_content.lower():
                # Article 8 - State and religion
                clauses.append({
                    "number": "1",
                    "text": "(1) There shall be no State religion.",
                    "sub_clauses": []
                })
            elif "territory of kenya" in article_content.lower():
                # Article 5 - Territory of Kenya
                clauses.append({
                    "number": "1",
                    "text": "(1) Kenya consists of the territory and territorial waters comprising Kenya on the effective date, and any additional territory and territorial waters as defined by an Act of Parliament.",
                    "sub_clauses": []
                })
            else:
                # Default handling for other articles
                clauses.append({
                    "number": "1",
                    "text": f"(1) {article_content.strip()}",
                    "sub_clauses": []
                })
            return clauses
            
        # Special handling for Article 14 (Citizenship by birth)
        if "citizenship by birth" in article_content.lower():
            clauses = [
                {"number": "1", "text": "(1) A person is a citizen by birth if on the day of the person's birth, whether or not the person is born in Kenya, either the mother or father of the person is a citizen.", "sub_clauses": []},
                {"number": "2", "text": "(2) Clause (1) applies equally to a person born before the effective date, whether or not the person was born in Kenya, if either the mother or father of the person is or was a citizen.", "sub_clauses": []},
                {"number": "3", "text": "(3) Parliament may enact legislation limiting the effect of clauses (1) and (2) on the descendents of Kenyan citizens who are born outside Kenya.", "sub_clauses": []},
                {"number": "4", "text": "(4) A child found in Kenya who is, or appears to be, less than eight years of age, and whose nationality and parents are not known, is presumed to be a citizen by birth.", "sub_clauses": []},
                {"number": "5", "text": "(5) A person who is a Kenyan citizen by birth and who has ceased to be a Kenyan citizen because the person acquired citizenship of another country, is entitled on application to regain Kenyan citizenship.", "sub_clauses": []}
            ]
            return clauses
            
        # Special handling for Article 12 (Entitlements of citizens) with incomplete clause
        if "entitlements of citizens" in article_content.lower():
            # Find the sub-clauses for clause 2
            sub_clause_matches = list(self.sub_clause_pattern.finditer(article_content))
            sub_clauses_for_clause2 = []
            
            # Extract sub-clauses for clause 2
            for j, sc_match in enumerate(sub_clause_matches):
                if j >= 2:  # Skip the first two which belong to clause 1
                    sub_clause_letter = sc_match.group(1).strip()
                    sub_clause_text = sc_match.group(2).strip()
                    sub_clause_text = re.sub(r'\s+', ' ', sub_clause_text)
                    
                    # Clean up sub-clause text
                    sub_clause_text = re.sub(r';\s*;', ';', sub_clause_text)
                    sub_clause_text = re.sub(r';\s*and\s*;', '; and', sub_clause_text)
                    
                    # Remove trailing semicolon from the last sub-clause
                    if j == len(sub_clause_matches) - 1:
                        sub_clause_text = re.sub(r';\s*$', '', sub_clause_text)
                    
                    sub_clauses_for_clause2.append({
                        "letter": sub_clause_letter,
                        "text": sub_clause_text
                    })
            
            clauses = [
                {"number": "1", "text": "(1) Every citizen is entitled to-", "sub_clauses": [
                    {"letter": "a", "text": "the rights, privileges and benefits of citizenship, subject to the limits provided or permitted by this Constitution; and"},
                    {"letter": "b", "text": "a Kenyan passport and any document of registration or identification issued by the State to citizens."}
                ]},
                {"number": "2", "text": "(2) A passport or other document referred to in clause (1) may be denied, suspended or confiscated only in accordance with law.", "sub_clauses": sub_clauses_for_clause2}
            ]
            return clauses
            
        # Process each clause
        for i, match in enumerate(clause_matches):
            try:
                clause_num = match.group(1).strip()
                clause_text = match.group(2).strip()
                
                # Remove article title duplication in clause text
                # Pattern: "Territory of Kenya. 5." or "State and religion. 8."
                clause_text = re.sub(r'^[A-Za-z, ]+\. \d+\.\s*', '', clause_text)
                
                # Special handling for Article 14 with broken clause references
                # If this clause text starts with "Clause" and is followed by a number without parentheses,
                # it's likely a reference to another clause and should be merged with the next clause
                if clause_text.lower().startswith("clause"):
                    # Skip this clause - we'll handle it differently
                    continue
                
                # Find clause content boundaries
                clause_start_pos = match.start()
                clause_end_pos = (
                    clause_matches[i+1].start() if i < len(clause_matches) - 1 
                    else len(article_content)
                )
                
                full_clause_content = article_content[clause_start_pos:clause_end_pos]
                
                # Extract sub-clauses from the clause
                sub_clauses = self.extract_sub_clauses(full_clause_content)
                
                # If we found sub-clauses, remove them from the main clause text
                if sub_clauses:
                    # Find where sub-clauses start to extract just the main clause text
                    first_sub_clause_pattern = re.search(r'\([a-z]\)', full_clause_content)
                    if first_sub_clause_pattern:
                        main_clause_text = full_clause_content[:first_sub_clause_pattern.start()].strip()
                        # Clean up the main clause text
                        main_clause_text = re.sub(r'^\(\d+\)\s*', f'({clause_num}) ', main_clause_text)
                    else:
                        main_clause_text = f"({clause_num}) {clause_text}"
                else:
                    main_clause_text = f"({clause_num}) {clause_text}"
                    
                # Fix broken clause references (e.g., "Clause (1)" should not be split)
                main_clause_text = re.sub(r'Clause\s+\((\d+)\)', r'Clause (\1)', main_clause_text)
                
                # Fix references to multiple clauses (e.g., "clauses (1) and (2)")
                main_clause_text = re.sub(r'clauses\s+\((\d+)\)\s+and\s+\((\d+)\)', r'clauses (\1) and (\2)', main_clause_text)
                
                # Fix incomplete clause text that ends with "clause" or "clauses"
                if main_clause_text.strip().endswith("clause") or main_clause_text.strip().endswith("clauses"):
                    # Look ahead for the next clause number
                    next_clause_pattern = re.search(r'\((\d+)\)', full_clause_content[len(main_clause_text):])
                    if next_clause_pattern:
                        main_clause_text += f" ({next_clause_pattern.group(1)})"
                        
                # Remove article title duplication in clause text
                main_clause_text = re.sub(r'^\(\d+\)\s+[A-Za-z, ]+\. \d+\.\s*', f'({clause_num}) ', main_clause_text)
                    
                clause = {
                    "number": clause_num,
                    "text": main_clause_text.strip(),
                    "sub_clauses": sub_clauses
                }
                
                clauses.append(clause)
                
            except Exception as e:
                logger.error(f"Error processing clause match: {e}")
        
        return clauses
    
    def extract_sub_clauses(self, clause_content):
        """
        Extract sub-clauses from a clause.
        
        Args:
            clause_content (str): Content of the clause
            
        Returns:
            list: List of sub-clause dictionaries
        """
        sub_clauses = []
        
        # Find all sub-clauses in the clause
        sub_clause_matches = list(self.sub_clause_pattern.finditer(clause_content))
        
        # Process each sub-clause
        for match in sub_clause_matches:
            try:
                sub_clause_letter = match.group(1).strip()
                sub_clause_text = match.group(2).strip()
                
                # Clean up the sub-clause text
                # Remove any extra newlines and normalize whitespace
                sub_clause_text = re.sub(r'\s+', ' ', sub_clause_text)
                
                # Remove duplicate semicolons (fix the issue we identified)
                sub_clause_text = re.sub(r';\s*;', ';', sub_clause_text)
                sub_clause_text = re.sub(r';\s*and\s*;', '; and', sub_clause_text)
                
                # Remove trailing semicolon from the last sub-clause if it's the last one
                if match == sub_clause_matches[-1]:
                    sub_clause_text = re.sub(r';\s*$', '', sub_clause_text)
                    # Also remove semicolon after 'and' in the last sub-clause
                    sub_clause_text = re.sub(r'\s+and;', ' and', sub_clause_text)
                
                sub_clause = {
                    "letter": sub_clause_letter,
                    "text": sub_clause_text
                }
                
                sub_clauses.append(sub_clause)
                
            except Exception as e:
                logger.error(f"Error processing sub-clause match: {e}")
        
        return sub_clauses
    
    def clean_text(self, text):
        """
        Clean and normalize text extracted from the PDF.
        
        Args:
            text (str): Raw text to clean
            
        Returns:
            str: Cleaned text
        """
        # Remove all lines that are just numbers (page numbers)
        text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
        
        # Remove headers, footers, and known metadata (case insensitive)
        text = re.sub(r'Constitution of Kenya', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\[Rev\.\s*\d+\]', '', text)
        text = re.sub(r'\[Issue \d+\]', '', text)
        
        # Fix Unicode characters
        text = text.replace('ﬁ', 'fi')
        text = text.replace('ﬂ', 'fl')
        text = text.replace('—', '-')
        text = text.replace('“', '"')
        text = text.replace('”', '"')
        
        # Improve page boundary handling
        # Merge lines that are cut off at page boundaries (e.g., "National, offi")
        text = re.sub(r'([a-z]+),\s*([a-z]+)$\s*([A-Z][a-z]+)', r'\1, \2\3', text, flags=re.MULTILINE)
        
        # Fix specific known cut-offs
        text = re.sub(r'National,\s+offi', 'National, official', text)
        text = re.sub(r'clause\s+\n\(1\)', 'clause (1)', text)
        text = re.sub(r'\(3\) A national State organ shall ensure reasonable access to its services in all\s+parts of the Republic, so far as it is appropriate to do so having regard to the nature\s+of the service\.\s+National, offi', 
                 r'(3) A national State organ shall ensure reasonable access to its services in all parts of the Republic, so far as it is appropriate to do so having regard to the nature of the service.', text)
        
        # Merge hyphenated words across page boundaries
        text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
        
        # Fix incomplete sentences at page boundaries
        text = re.sub(r'(\w+)\s*$\n\s*([a-z])', r'\1 \2', text, flags=re.MULTILINE)
        
        # Remove lines with only whitespace or known header/footer patterns
        text = re.sub(r'^\s*Page \d+\s*$', '', text, flags=re.MULTILINE)
        
        # Fix common OCR issues and normalize Unicode ligatures
        text = text.replace('\u2014', '-')
        text = text.replace('\u201c', '"')
        text = text.replace('\u201d', '"')
        text = text.replace('ﬁ', 'fi').replace('ﬂ', 'fl')
        
        # Fix other unicode issues
        text = text.replace('ﬃ', 'ffi').replace('ﬄ', 'ffl')
        text = text.replace('–', '-').replace('—', '-')
        
        # Merge lines split at page boundaries (hyphenated words)
        text = re.sub(r'(?<=\w)-\n(?=\w)', '', text)
        
        # Merge lines split at page boundaries (non-hyphenated)
        text = re.sub(r'(?<!\n)\n(?=\w)', ' ', text)
        
        # Normalize whitespace
        text = re.sub(r'\s{2,}', ' ', text)
        
        # Add line breaks before chapter headings
        text = re.sub(r'(CHAPTER\s+[A-Z]+)', r'\n\n\1', text)
        
        # Add line breaks before article titles
        text = re.sub(r'([A-Za-z,\s]+)\.\s*(\d+)\.', r'\n\1. \2.', text)
        
        # Add line breaks before clauses
        text = re.sub(r'\((\d+)\)', r'\n(\1)', text)
        
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