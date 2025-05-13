import json
import re
from bs4 import BeautifulSoup
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
import logging
import os

# Define regex patterns as constants to avoid duplication
ARTICLE_PATTERN = re.compile(r'^\d+\.')
CLAUSE_PATTERN = re.compile(r'^\((\d+)\)\s*(.+)$')
SUB_CLAUSE_PATTERN = re.compile(r'^\(([a-z]|i{1,3}|iv|ix|v{1,3})\)\s*(.+)$')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SubClause:
    sub_clause_id: str
    content: str

@dataclass
class Clause:
    clause_number: str
    content: str
    sub_clauses: List[SubClause] = field(default_factory=list)

@dataclass
class Article:
    article_number: int
    article_title: str
    clauses: List[Clause] = field(default_factory=list)

@dataclass
class Part:
    part_number: int
    part_title: str
    articles: List[Article] = field(default_factory=list)

@dataclass
class Chapter:
    chapter_number: int
    chapter_title: str
    articles: List[Article] = field(default_factory=list)
    parts: List[Part] = field(default_factory=list)

@dataclass
class Schedule:
    schedule_number: int
    schedule_title: str
    content: List[str] = field(default_factory=list)

@dataclass
class Constitution:
    title: str
    preamble: str = ""
    chapters: List[Chapter] = field(default_factory=list)
    schedules: List[Schedule] = field(default_factory=list)


class HtmlConstitutionExtractor:
    """Extract constitution from HTML"""
    
    def __init__(self, html_path, output_path):
        """Initialize the extractor"""
        self.html_path = html_path
        self.output_path = output_path
        self.soup = None
        
        # Official chapter titles
        self.official_chapter_titles = {
            1: "Sovereignty of the People and Supremacy of this Constitution",
            2: "The Republic",
            3: "Citizenship",
            4: "The Bill of Rights",
            5: "Land and Environment",
            6: "Leadership and Integrity",
            7: "Representation of the People",
            8: "The Legislature",
            9: "The Executive",
            10: "Judiciary",
            11: "Devolved Government",
            12: "Public Finance",
            13: "The Public Service",
            14: "National Security",
            15: "Commissions and Independent Offices",
            16: "Amendment of this Constitution",
            17: "General Provisions",
            18: "Transitional and Consequential Provisions"
        }
        
        # Initialize with empty chapters list, we'll populate it in _initialize_chapters
        self.constitution = Constitution(
            title="The Constitution of Kenya, 2010",
            preamble="",
            chapters=[]
        )
        
        # Initialize chapters
        self._initialize_chapters()
    
    def _initialize_chapters(self):
        """Initialize all 18 chapters with official titles"""
        # Create chapters with official titles
        for chapter_num in range(1, 19):
            chapter = Chapter(
                chapter_number=chapter_num,
                chapter_title=self.official_chapter_titles[chapter_num],
                articles=[],
                parts=[]
            )
            self.constitution.chapters.append(chapter)

    def _extract_preamble(self):
        """Extract the preamble from the HTML"""
        preamble_text = ""
        preamble_section = self.soup.find(string=re.compile("PREAMBLE", re.IGNORECASE))
        
        if preamble_section:
            # Find the parent element containing the preamble
            preamble_parent = preamble_section.find_parent()
            
            # Collect all text until we hit a chapter heading
            current = preamble_parent.next_sibling
            preamble_parts = []
            
            while current and not (hasattr(current, 'text') and re.search(r'Chapter\s+(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|ELEVEN|TWELVE|THIRTEEN|FOURTEEN|FIFTEEN|SIXTEEN|SEVENTEEN|EIGHTEEN)', current.text, re.IGNORECASE)):
                if hasattr(current, 'text') and current.text.strip():
                    preamble_parts.append(current.text.strip())
                current = current.next_sibling
            
            preamble_text = " ".join(preamble_parts)
        
        self.constitution.preamble = preamble_text
    
    def _extract_chapters(self):
        """Extract chapters and their content"""
        # Find all article elements (they start with a number followed by a period)
        article_elements = self.soup.find_all(string=lambda text: text and ARTICLE_PATTERN.match(text.strip()))
        
        # Process each article element
        self._process_article_elements(article_elements)    
    
    def _process_article_elements(self, article_elements):
        """Process article elements to extract articles and assign them to chapters"""
        article_pattern = re.compile(r'^(\d+)\.\s+(.+)$')
        
        for article_elem in article_elements:
            # Extract article number and title
            article_match = article_pattern.match(article_elem.strip())
            if not article_match:
                continue
                
            article_num = int(article_match.group(1))
            article_title = article_match.group(2).strip()
            
            # Create new article
            article = Article(
                article_number=article_num,
                article_title=article_title,
                clauses=[]
            )
            
            # Determine which chapter this article belongs to
            chapter_num = self._determine_chapter_for_article(article_num)
            
            # Add article to the appropriate chapter
            self._add_article_to_chapter(article_elem, article, chapter_num)
    
    def _add_article_to_chapter(self, article_elem, article, chapter_num):
        """Add an article to its appropriate chapter"""
        if chapter_num <= 0 or chapter_num > 18:
            return
            
        # Find the corresponding chapter
        for chapter in self.constitution.chapters:
            if chapter.chapter_number == chapter_num:
                # Extract clauses for this article
                self._extract_clauses_for_article(article_elem, article)
                
                # Add article to chapter
                chapter.articles.append(article)
                break
    
    def _determine_chapter_for_article(self, article_num):
        """Determine which chapter an article belongs to based on its number"""
        # Article ranges for each chapter in the Constitution of Kenya
        chapter_ranges = {
            1: (1, 3),      # Chapter 1: Articles 1-3
            2: (4, 11),     # Chapter 2: Articles 4-11
            3: (12, 18),    # Chapter 3: Articles 12-18
            4: (19, 59),    # Chapter 4: Articles 19-59
            5: (60, 72),    # Chapter 5: Articles 60-72
            6: (73, 80),    # Chapter 6: Articles 73-80
            7: (81, 92),    # Chapter 7: Articles 81-92
            8: (93, 128),   # Chapter 8: Articles 93-128
            9: (129, 155),  # Chapter 9: Articles 129-155
            10: (156, 173), # Chapter 10: Articles 156-173
            11: (174, 200), # Chapter 11: Articles 174-200
            12: (201, 231), # Chapter 12: Articles 201-231
            13: (232, 236), # Chapter 13: Articles 232-236
            14: (237, 247), # Chapter 14: Articles 237-247
            15: (248, 254), # Chapter 15: Articles 248-254
            16: (255, 257), # Chapter 16: Articles 255-257
            17: (258, 260), # Chapter 17: Articles 258-260
            18: (261, 264)  # Chapter 18: Articles 261-264
        }
        
        for chapter_num, (start, end) in chapter_ranges.items():
            if start <= article_num <= end:
                return chapter_num
        
        # If we can't determine the chapter, return 0
        return 0
    
    def _extract_articles_for_chapter(self, chapter_heading, next_chapter_heading, chapter):
        """Extract articles for a specific chapter"""
        # Find the parent element of the chapter heading
        chapter_parent = chapter_heading.find_parent()
        
        # Find all article elements within this chapter
        current = chapter_parent.next_sibling
        article_elements = []
        
        while current and (not next_chapter_heading or not (hasattr(current, 'text') and next_chapter_heading in current.text)):
            if hasattr(current, 'text') and re.match(r'^\d+\.', current.text.strip()):
                article_elements.append(current)
            current = current.next_sibling
        
        # Process each article
        for article_elem in article_elements:
            article_match = re.match(r'^(\d+)\.\s*(.*?)$', article_elem.text.strip())
            if article_match:
                article_num = int(article_match.group(1))
                article_title = article_match.group(2).strip()
                
                # Create new article
                article = Article(
                    article_number=article_num,
                    article_title=article_title,
                    clauses=[]
                )
                
                # Extract clauses for this article
                self._extract_clauses_for_article(article_elem, article)
                
                # Add article to chapter
                chapter.articles.append(article)
    
    def _extract_clauses_for_article(self, article_elem, article):
        """Extract clauses for a specific article"""
        # Find the parent element that contains the article
        parent = article_elem.find_parent()
        if not parent:
            return
        
        # Find and process potential clauses
        potential_clauses = self._find_potential_clauses(parent)
        self._process_clauses(potential_clauses, article)
    
    def _find_potential_clauses(self, parent):
        """Find elements that might contain clauses"""
        potential_clauses = []
        
        # Look at all siblings after the parent element until we find another article
        next_elem = parent.next_sibling
        while next_elem:
            if self._is_article_element(next_elem):
                # We've reached the next article, stop searching
                break
                
            if self._is_clause_element(next_elem):
                potential_clauses.append(next_elem)
                    
            next_elem = next_elem.next_sibling
            
        return potential_clauses
    
    def _is_article_element(self, elem):
        """Check if an element is an article"""
        return hasattr(elem, 'text') and ARTICLE_PATTERN.match(elem.text.strip())
    
    def _is_clause_element(self, elem):
        """Check if an element is a clause"""
        if not (hasattr(elem, 'text') and elem.text.strip()):
            return False
            
        clause_text = elem.text.strip()
        return clause_text.startswith('(') and CLAUSE_PATTERN.match(clause_text)
    
    def _process_clauses(self, clause_elements, article):
        """Process clause elements and add them to the article"""
        for clause_elem in clause_elements:
            clause_text = clause_elem.text.strip()
            clause_match = CLAUSE_PATTERN.match(clause_text)
            
            if not clause_match:
                continue
                
            clause_num = clause_match.group(1)
            clause_content = clause_match.group(2).strip()
            
            # Create new clause
            clause = Clause(
                clause_number=clause_num,
                content=clause_content,
                sub_clauses=[]
            )
            
            # Extract sub-clauses for this clause
            self._extract_sub_clauses_for_clause(clause_elem, clause)
            
            # Add clause to article
            article.clauses.append(clause)
    
    def _extract_sub_clauses_for_clause(self, clause_elem, clause):
        """Extract sub-clauses for a specific clause"""
        # Find the parent element that contains the clause
        parent = clause_elem.find_parent()
        if not parent:
            return
        
        # Find potential sub-clauses
        potential_sub_clauses = self._find_potential_sub_clauses(parent)
        
        # Process the sub-clauses
        self._process_sub_clauses(potential_sub_clauses, clause)
    
    def _find_potential_sub_clauses(self, parent):
        """Find elements that might contain sub-clauses"""
        potential_sub_clauses = []
        next_elem = parent.next_sibling
        
        while next_elem:
            if self._is_article_or_clause_element(next_elem):
                break
                
            if self._is_sub_clause_element(next_elem):
                potential_sub_clauses.append(next_elem)
                
            next_elem = next_elem.next_sibling
            
        return potential_sub_clauses
    
    def _is_article_or_clause_element(self, elem):
        """Check if an element is an article or clause"""
        if not hasattr(elem, 'text') or not elem.text.strip():
            return False
            
        text = elem.text.strip()
        return ARTICLE_PATTERN.match(text) or text.startswith('(') and CLAUSE_PATTERN.match(text)
    
    def _is_sub_clause_element(self, elem):
        """Check if an element is a sub-clause"""
        if not hasattr(elem, 'text') or not elem.text.strip():
            return False
            
        text = elem.text.strip()
        return text.startswith('(') and SUB_CLAUSE_PATTERN.match(text)
    
    def _process_sub_clauses(self, sub_clause_elements, clause):
        """Process sub-clause elements and add them to the clause"""
        for sub_clause_elem in sub_clause_elements:
            sub_clause_text = sub_clause_elem.text.strip()
            sub_clause_match = SUB_CLAUSE_PATTERN.match(sub_clause_text)
            
            if not sub_clause_match:
                continue
                
            sub_clause_id = sub_clause_match.group(1)
            sub_clause_content = sub_clause_match.group(2).strip()
            
            # Create new sub-clause
            sub_clause = SubClause(
                sub_clause_id=sub_clause_id,
                content=sub_clause_content
            )
            
            # Add sub-clause to clause
            clause.sub_clauses.append(sub_clause)
    
    def _word_to_number(self, word):
        """Convert word representation of number to integer"""
        word_to_num = {
            'ONE': 1, 'TWO': 2, 'THREE': 3, 'FOUR': 4, 'FIVE': 5, 
            'SIX': 6, 'SEVEN': 7, 'EIGHT': 8, 'NINE': 9, 'TEN': 10,
            'ELEVEN': 11, 'TWELVE': 12, 'THIRTEEN': 13, 'FOURTEEN': 14, 
            'FIFTEEN': 15, 'SIXTEEN': 16, 'SEVENTEEN': 17, 'EIGHTEEN': 18
        }
        return word_to_num.get(word, 0)
    
    def extract(self):
        """Extract the constitution structure from HTML"""
        try:
            # Read and parse HTML
            with open(self.html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            self.soup = BeautifulSoup(html_content, 'html.parser')
            
            # Set the title (hardcoded for now)
            self.constitution.title = "The Constitution of Kenya, 2010"
            
            # Extract preamble
            self._extract_preamble()
            
            # Extract chapters and their content
            self._extract_chapters()
            
            # Convert to dictionary
            constitution_dict = asdict(self.constitution)
            
            # Write to JSON file
            with open(self.output_path, 'w', encoding='utf-8') as f:
                json.dump(constitution_dict, f, indent=2, ensure_ascii=False)
            
            # Log extraction statistics
            self._log_detailed_statistics()
            
        except Exception as e:
            logging.error(f"Error extracting constitution: {e}")
            raise
    
    def _log_detailed_statistics(self):
        """Log detailed statistics about the extracted constitution"""
        total_articles = 0
        total_clauses = 0
        total_sub_clauses = 0
        
        # Print chapter-by-chapter statistics
        logging.info("\n===== CONSTITUTION EXTRACTION SUMMARY =====")
        logging.info(f"Title: {self.constitution.title}")
        logging.info(f"Preamble extracted: {'Yes' if self.constitution.preamble else 'No'}")
        logging.info(f"Total chapters: {len(self.constitution.chapters)}")
        logging.info("\nChapter statistics:")
        
        for chapter in self.constitution.chapters:
            chapter_articles = len(chapter.articles)
            total_articles += chapter_articles
            
            # Count clauses in this chapter
            chapter_clauses = 0
            chapter_sub_clauses = 0
            
            for article in chapter.articles:
                article_clauses = len(article.clauses)
                chapter_clauses += article_clauses
                
                # Count sub-clauses
                for clause in article.clauses:
                    chapter_sub_clauses += len(clause.sub_clauses)
            
            total_clauses += chapter_clauses
            total_sub_clauses += chapter_sub_clauses
            
            logging.info(f"Chapter {chapter.chapter_number} ({chapter.chapter_title}): {chapter_articles} articles, {chapter_clauses} clauses, {chapter_sub_clauses} sub-clauses")
        
        # Print overall statistics
        logging.info("\nOverall statistics:")
        logging.info(f"Total chapters: {len(self.constitution.chapters)}")
        logging.info(f"Total articles: {total_articles}")
        logging.info(f"Total clauses: {total_clauses}")
        logging.info(f"Total sub-clauses: {total_sub_clauses}")
        logging.info("=========================================")
        
    def _extract_preamble(self):
        """Extract the preamble from the HTML"""
        # Look for preamble content in the HTML
        preamble_paragraphs = []
        
        # Find all span elements with class 'akn-p' that contain preamble content
        preamble_spans = self.soup.find_all('span', class_='akn-p')
        
        for span in preamble_spans:
            # Check if this is a preamble paragraph
            if span.find('b', class_='akn-b'):
                # Get the full text including the bold part
                full_text = span.get_text().strip()
                preamble_paragraphs.append(full_text)
        
        # Combine paragraphs into a single preamble text
        if preamble_paragraphs:
            self.constitution.preamble = "\n\n".join(preamble_paragraphs)
    
    def _log_statistics(self):
        """Log statistics about the extracted constitution"""
        total_articles = 0
        total_clauses = 0
        total_sub_clauses = 0
        
        for chapter in self.constitution.chapters:
            chapter_articles = len(chapter.articles)
            chapter_parts = len(chapter.parts)
            
            part_articles = sum(len(part.articles) for part in chapter.parts)
            total_articles += chapter_articles + part_articles
            
            # Count clauses and sub-clauses in chapter articles
            for article in chapter.articles:
                total_clauses += len(article.clauses)
                total_sub_clauses += sum(len(clause.sub_clauses) for clause in article.clauses)
            
            # Count clauses and sub-clauses in part articles
            for part in chapter.parts:
                for article in part.articles:
                    total_clauses += len(article.clauses)
                    total_sub_clauses += sum(len(clause.sub_clauses) for clause in article.clauses)
            
            logger.info(f"Chapter {chapter.chapter_number}: {chapter_articles} articles, {chapter_parts} parts, {part_articles} articles in parts")
        
        logger.info(f"Total chapters: {len(self.constitution.chapters)}")
        logger.info(f"Total articles: {total_articles}")
        logger.info(f"Total clauses: {total_clauses}")
        logger.info(f"Total sub-clauses: {total_sub_clauses}")
    
    def save_to_json(self, output_path):
        """Save the constitution to a JSON file"""
        constitution_dict = asdict(self.constitution)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(constitution_dict, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Constitution saved to {output_path}")


def main():
    """Main function to run the extractor"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract Constitution of Kenya from HTML')
    parser.add_argument('--input', '-i', type=str, default='test.html',
                        help='Path to input HTML file')
    parser.add_argument('--output', '-o', type=str, default='src/data/processed/constitution_final.json',
                        help='Path to output JSON file')
    
    args = parser.parse_args()
    
    # Ensure the output directory exists
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    # Extract and save
    extractor = HtmlConstitutionExtractor(args.input, args.output)
    extractor.extract()


if __name__ == "__main__":
    main()
