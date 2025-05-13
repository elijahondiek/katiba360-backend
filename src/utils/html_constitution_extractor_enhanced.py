import json
import re
from bs4 import BeautifulSoup, Tag
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
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


class EnhancedHtmlConstitutionExtractor:
    """Enhanced extractor for constitution from HTML with better handling of nested elements"""
    
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
        """Extract the preamble from the HTML including national symbols"""
        preamble_section = self.soup.find(string=re.compile("PREAMBLE", re.IGNORECASE))
        
        if not preamble_section:
            logger.warning("Preamble section not found")
            return
            
        # Find the parent element containing the preamble
        preamble_parent = preamble_section.find_parent()
        
        # Collect all text until we hit a chapter heading
        current = preamble_parent
        preamble_parts = []
        
        # Process the preamble and national symbols section
        while current and not (hasattr(current, 'name') and current.name == 'section' and 'akn-chapter' in current.get('class', [])):
            if isinstance(current, Tag):
                # Extract text content
                if current.text.strip():
                    preamble_parts.append(current.text.strip())
            
            # Move to next sibling
            current = current.next_sibling
        
        # Clean up and join the preamble parts
        preamble_text = "\n".join(preamble_parts)
        self.constitution.preamble = preamble_text
    
    def _extract_chapters(self):
        """Extract chapters and their content using structured HTML parsing"""
        # Find all chapter sections
        chapter_sections = self.soup.find_all('section', class_='akn-chapter')
        
        for chapter_section in chapter_sections:
            # Extract chapter number and title
            chapter_heading = chapter_section.find('h2')
            if not chapter_heading:
                continue
                
            # Parse chapter number and title
            chapter_text = chapter_heading.text.strip()
            chapter_match = re.search(r'Chapter\s+(One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten|Eleven|Twelve|Thirteen|Fourteen|Fifteen|Sixteen|Seventeen|Eighteen)', chapter_text, re.IGNORECASE)
            
            if not chapter_match:
                continue
                
            # Convert word to number
            chapter_word = chapter_match.group(1).upper()
            chapter_num = self._word_to_number(chapter_word)
            
            if chapter_num <= 0 or chapter_num > 18:
                continue
            
            # Find the corresponding chapter in our data structure
            chapter = next((c for c in self.constitution.chapters if c.chapter_number == chapter_num), None)
            if not chapter:
                continue
            
            # Extract articles for this chapter
            self._extract_articles_for_chapter(chapter_section, chapter)
    
    def _extract_articles_for_chapter(self, chapter_section, chapter):
        """Extract articles for a specific chapter using structured HTML parsing"""
        # Find all article sections within this chapter
        article_sections = chapter_section.find_all('section', class_='akn-section')
        
        for article_section in article_sections:
            # Extract article number and title
            article_heading = article_section.find('h3')
            if not article_heading:
                continue
                
            # Parse article number and title
            article_text = article_heading.text.strip()
            article_match = re.match(r'(\d+)\.\s*(.*?)$', article_text)
            
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
            
            # Extract clauses for this article
            self._extract_clauses_for_article(article_section, article)
            
            # Add article to chapter
            chapter.articles.append(article)
    
    def _extract_clauses_for_article(self, article_section, article):
        """Extract clauses for a specific article using structured HTML parsing"""
        # Find all subsection elements (clauses)
        subsections = article_section.find_all('section', class_='akn-subsection')
        
        for subsection in subsections:
            # Extract clause number
            num_elem = subsection.find('span', class_='akn-num')
            if not num_elem:
                continue
                
            clause_num_text = num_elem.text.strip()
            clause_match = re.match(r'\((\d+)\)', clause_num_text)
            
            if not clause_match:
                continue
                
            clause_num = clause_match.group(1)
            
            # Extract clause content
            content_elem = subsection.find('span', class_='akn-content')
            if not content_elem:
                continue
                
            # Get the text from the paragraph element
            p_elem = content_elem.find('span', class_='akn-p')
            if not p_elem:
                continue
                
            clause_content = p_elem.text.strip()
            
            # Create new clause
            clause = Clause(
                clause_number=clause_num,
                content=clause_content,
                sub_clauses=[]
            )
            
            # Check if this clause has an intro and paragraphs (sub-clauses)
            intro_elem = subsection.find('span', class_='akn-intro')
            if intro_elem:
                # This clause has sub-clauses
                self._extract_sub_clauses_for_clause(subsection, clause)
            
            # Add clause to article
            article.clauses.append(clause)
    
    def _extract_sub_clauses_for_clause(self, subsection, clause):
        """Extract sub-clauses for a specific clause using structured HTML parsing"""
        # Find all paragraph elements (sub-clauses)
        paragraphs = subsection.find_all('section', class_='akn-paragraph')
        
        for paragraph in paragraphs:
            # Extract sub-clause ID
            num_elem = paragraph.find('span', class_='akn-num')
            if not num_elem:
                continue
                
            sub_clause_id_text = num_elem.text.strip()
            sub_clause_match = re.match(r'\(([a-z]|i{1,3}|iv|ix|v{1,3})\)', sub_clause_id_text)
            
            if not sub_clause_match:
                continue
                
            sub_clause_id = sub_clause_match.group(1)
            
            # Extract sub-clause content
            content_elem = paragraph.find('span', class_='akn-content')
            if not content_elem:
                continue
                
            # Get the text from the paragraph element
            p_elem = content_elem.find('span', class_='akn-p')
            if not p_elem:
                continue
                
            sub_clause_content = p_elem.text.strip()
            
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
            
            # Post-process to fix missing content
            self._post_process_special_cases()
            
            # Convert to dictionary
            constitution_dict = asdict(self.constitution)
            
            # Write to JSON file
            with open(self.output_path, 'w', encoding='utf-8') as f:
                json.dump(constitution_dict, f, indent=2, ensure_ascii=False)
            
            # Log extraction statistics
            self._log_detailed_statistics()
            
            return constitution_dict
            
        except Exception as e:
            logging.error(f"Error extracting constitution: {e}")
            raise
    
    def _post_process_special_cases(self):
        """Fix special cases that the parser might miss"""
        # Fix Article 9 (National symbols and national days)
        self._fix_article_9()
        
        # Fix Article 10 (National values and principles of governance)
        self._fix_article_10()
        
        # Add other special case fixes as needed
    
    def _fix_article_9(self):
        """Fix Article 9 (National symbols and national days) which has a complex structure"""
        # Find Chapter 2
        chapter = next((c for c in self.constitution.chapters if c.chapter_number == 2), None)
        if not chapter:
            return
            
        # Find Article 9
        article = next((a for a in chapter.articles if a.article_number == 9), None)
        if not article:
            # If Article 9 doesn't exist, create it
            article = Article(
                article_number=9,
                article_title="National symbols and national days",
                clauses=[]
            )
            chapter.articles.append(article)
        
        # Ensure all clauses are present
        # Clause 1: The national symbols of the Republic are...
        if not any(c.clause_number == "1" for c in article.clauses):
            clause_1 = Clause(
                clause_number="1",
                content="The national symbols of the Republic are—",
                sub_clauses=[
                    SubClause(sub_clause_id="a", content="the national flag;"),
                    SubClause(sub_clause_id="b", content="the national anthem;"),
                    SubClause(sub_clause_id="c", content="the coat of arms; and"),
                    SubClause(sub_clause_id="d", content="the public seal.")
                ]
            )
            article.clauses.append(clause_1)
        
        # Clause 3: The national days are...
        if not any(c.clause_number == "3" for c in article.clauses):
            clause_3 = Clause(
                clause_number="3",
                content="The national days are—",
                sub_clauses=[
                    SubClause(sub_clause_id="a", content="Madaraka Day, to be observed on 1st June;"),
                    SubClause(sub_clause_id="b", content="Mashujaa Day, to be observed on 20th October; and"),
                    SubClause(sub_clause_id="c", content="Jamhuri Day, to be observed on 12th December.")
                ]
            )
            article.clauses.append(clause_3)
    
    def _fix_article_10(self):
        """Fix Article 10 (National values and principles of governance) which has a complex structure"""
        # Find Chapter 2
        chapter = next((c for c in self.constitution.chapters if c.chapter_number == 2), None)
        if not chapter:
            return
            
        # Find Article 10
        article = next((a for a in chapter.articles if a.article_number == 10), None)
        if not article:
            # If Article 10 doesn't exist, create it
            article = Article(
                article_number=10,
                article_title="National values and principles of governance",
                clauses=[]
            )
            chapter.articles.append(article)
        
        # Ensure all clauses are present
        # Clause 1: The national values and principles of governance...
        if not any(c.clause_number == "1" for c in article.clauses):
            clause_1 = Clause(
                clause_number="1",
                content="The national values and principles of governance in this Article bind all State organs, State officers, public officers and all persons whenever any of them—",
                sub_clauses=[
                    SubClause(sub_clause_id="a", content="applies or interprets this Constitution;"),
                    SubClause(sub_clause_id="b", content="enacts, applies or interprets any law; or"),
                    SubClause(sub_clause_id="c", content="makes or implements public policy decisions.")
                ]
            )
            article.clauses.append(clause_1)
        
        # Clause 2: The national values and principles of governance include...
        if not any(c.clause_number == "2" for c in article.clauses):
            clause_2 = Clause(
                clause_number="2",
                content="The national values and principles of governance include—",
                sub_clauses=[
                    SubClause(sub_clause_id="a", content="patriotism, national unity, sharing and devolution of power, the rule of law, democracy and participation of the people;"),
                    SubClause(sub_clause_id="b", content="human dignity, equity, social justice, inclusiveness, equality, human rights, non-discrimination and protection of the marginalised;"),
                    SubClause(sub_clause_id="c", content="good governance, integrity, transparency and accountability; and"),
                    SubClause(sub_clause_id="d", content="sustainable development.")
                ]
            )
            article.clauses.append(clause_2)
    
    def _log_detailed_statistics(self):
        """Log detailed statistics about the extracted constitution"""
        total_articles = 0
        total_clauses = 0
        total_sub_clauses = 0
        
        # Print chapter-by-chapter statistics
        logging.info("\n===== ENHANCED CONSTITUTION EXTRACTION SUMMARY =====")
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


# Example usage
if __name__ == "__main__":
    # Set paths
    html_path = "path/to/constitution.html"
    output_path = "path/to/output/constitution_enhanced.json"
    
    # Create extractor
    extractor = EnhancedHtmlConstitutionExtractor(html_path, output_path)
    
    # Extract constitution
    extractor.extract()
