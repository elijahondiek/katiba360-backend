#!/usr/bin/env python3
"""
Schedule Extractor for the Constitution of Kenya

This script extracts the six schedules from the Constitution of Kenya HTML file
and outputs them in a structured JSON format.
"""

import json
import re
import argparse
import os
import logging
from bs4 import BeautifulSoup
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ArticleReference:
    """Represents a reference to an article in the Constitution"""
    article_number: str
    clause_number: Optional[str] = None


@dataclass
class ScheduleItem:
    """Represents an item in a schedule"""
    item_number: str
    content: str
    sub_items: List[Dict] = field(default_factory=list)


@dataclass
class Schedule:
    """Represents a schedule in the Constitution"""
    schedule_number: str  # e.g., "FIRST", "SECOND", etc.
    title: str
    article_references: List[ArticleReference] = field(default_factory=list)
    items: List[ScheduleItem] = field(default_factory=list)
    content: str = ""


@dataclass
class ConstitutionSchedules:
    """Represents all schedules in the Constitution"""
    schedules: List[Schedule] = field(default_factory=list)


class ScheduleExtractor:
    """Extract schedules from the Constitution HTML"""
    
    def __init__(self, html_path, output_path):
        """Initialize the extractor"""
        self.html_path = html_path
        self.output_path = output_path
        self.soup = None
        self.constitution_schedules = ConstitutionSchedules(schedules=[])
        
        # Schedule number words to ordinals
        self.schedule_ordinals = {
            "FIRST": 1,
            "SECOND": 2,
            "THIRD": 3,
            "FOURTH": 4,
            "FIFTH": 5,
            "SIXTH": 6
        }
    
    def extract(self):
        """Extract schedules from HTML"""
        try:
            # Read and parse HTML
            with open(self.html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            self.soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find all schedule attachments
            self._extract_schedules()
            
            # Convert to dictionary
            schedules_dict = asdict(self.constitution_schedules)
            
            # Write to JSON file
            with open(self.output_path, 'w', encoding='utf-8') as f:
                json.dump(schedules_dict, f, indent=2, ensure_ascii=False)
            
            # Log detailed statistics
            self._log_detailed_statistics()
            
        except Exception as e:
            logger.error(f"Error extracting schedules: {e}")
            raise
    
    def _log_detailed_statistics(self):
        """Log detailed statistics about the extracted schedules"""
        total_items = 0
        total_article_refs = 0
        total_sub_items = 0
        
        logger.info("\n===== SCHEDULES EXTRACTION SUMMARY =====")
        logger.info(f"Total schedules extracted: {len(self.constitution_schedules.schedules)}")
        logger.info("\nSchedule statistics:")
        
        for schedule in self.constitution_schedules.schedules:
            # Count items and sub-items
            schedule_items = len(schedule.items)
            schedule_article_refs = len(schedule.article_references)
            schedule_sub_items = sum(len(item.sub_items) for item in schedule.items)
            
            total_items += schedule_items
            total_article_refs += schedule_article_refs
            total_sub_items += schedule_sub_items
            
            # Log schedule statistics
            logger.info(f"Schedule {schedule.schedule_number} ({schedule.title}):")
            logger.info(f"  - Items: {schedule_items}")
            logger.info(f"  - Sub-items: {schedule_sub_items}")
            logger.info(f"  - Article references: {schedule_article_refs}")
            
            # Log article references
            if schedule_article_refs > 0:
                ref_str = ", ".join([f"Article {ref.article_number}" + 
                                    (f"({ref.clause_number})" if ref.clause_number else "") 
                                    for ref in schedule.article_references])
                logger.info(f"  - Referenced articles: {ref_str}")
            
            logger.info("")
        
        # Log overall statistics
        logger.info("Overall statistics:")
        logger.info(f"Total schedules: {len(self.constitution_schedules.schedules)}")
        logger.info(f"Total items: {total_items}")
        logger.info(f"Total sub-items: {total_sub_items}")
        logger.info(f"Total article references: {total_article_refs}")
        logger.info("=========================================")
    
    def _extract_schedules(self):
        """Extract all schedules from the HTML"""
        # Find all schedule attachments (they are in div elements with class akn-attachment)
        attachments = self.soup.find_all('div', class_='akn-attachment')
        
        for attachment in attachments:
            # Check if this is a schedule
            heading = attachment.find('h2', class_='akn-heading')
            if not heading or 'SCHEDULE' not in heading.text:
                continue
            
            # Extract schedule number and title
            schedule_number = heading.text.strip()
            subheading = attachment.find('h2', class_='akn-subheading')
            title = subheading.text.strip() if subheading else ""
            
            # Create a new schedule
            schedule = Schedule(
                schedule_number=schedule_number,
                title=title
            )
            
            # Extract article references
            self._extract_article_references(attachment, schedule)
            
            # Extract schedule items
            self._extract_schedule_items(attachment, schedule)
            
            # For schedules with tables (like Third and Fifth schedules)
            if len(schedule.items) == 0:
                self._extract_table_content(attachment, schedule)
            
            # Add schedule to the list
            self.constitution_schedules.schedules.append(schedule)
    
    def _extract_article_references(self, attachment, schedule):
        """Extract article references from a schedule"""
        # Find the container with article references
        container = attachment.find('span', class_='akn-hcontainer')
        if not container:
            return
        
        # Find the cross heading with article references
        cross_heading = container.find('h3', class_='akn-crossHeading')
        if not cross_heading:
            return
        
        # Extract article references using regex
        article_refs = cross_heading.text.strip()
        
        # Pattern for article references like "Article 6(1)" or "Article 74"
        pattern = r'Article\s+(\d+)(?:\((\d+)\))?'
        matches = re.findall(pattern, article_refs)
        
        for match in matches:
            article_num = match[0]
            clause_num = match[1] if match[1] else None
            
            article_ref = ArticleReference(
                article_number=article_num,
                clause_number=clause_num
            )
            
            schedule.article_references.append(article_ref)
    
    def _extract_schedule_items(self, attachment, schedule):
        """Extract items from a schedule"""
        # Find all paragraphs in the schedule
        paragraphs = attachment.find_all('section', class_='akn-paragraph')
        
        for paragraph in paragraphs:
            # Extract item number
            num_elem = paragraph.find('span', class_='akn-num')
            if not num_elem:
                continue
                
            item_number = num_elem.text.strip().rstrip('.')
            
            # Extract content
            content_elem = paragraph.find('span', class_='akn-content')
            if not content_elem:
                continue
                
            # Get all paragraph text
            p_elements = content_elem.find_all('span', class_='akn-p')
            content = "\n".join([p.text.strip() for p in p_elements])
            
            # Create schedule item
            item = ScheduleItem(
                item_number=item_number,
                content=content
            )
            
            # Extract sub-items if any
            self._extract_sub_items(paragraph, item)
            
            # Add item to schedule
            schedule.items.append(item)
    
    def _extract_sub_items(self, paragraph, item):
        """Extract sub-items from a schedule item"""
        # Find all sub-paragraphs
        sub_paragraphs = paragraph.find_all('section', class_='akn-subparagraph')
        
        for sub_para in sub_paragraphs:
            # Extract sub-item number
            num_elem = sub_para.find('span', class_='akn-num')
            if not num_elem:
                continue
                
            sub_item_number = num_elem.text.strip().rstrip('.')
            
            # Extract content
            content_elem = sub_para.find('span', class_='akn-content')
            if not content_elem:
                continue
                
            # Get all paragraph text
            p_elements = content_elem.find_all('span', class_='akn-p')
            content = "\n".join([p.text.strip() for p in p_elements])
            
            # Create sub-item
            sub_item = {
                "item_number": sub_item_number,
                "content": content
            }
            
            # Add sub-item to item
            item.sub_items.append(sub_item)
    
    def _extract_table_content(self, attachment, schedule):
        """Extract content from tables in the schedule"""
        # Find all tables in the attachment
        tables = attachment.find_all('table', class_='akn-table')
        
        if tables:
            self._process_tables(tables, schedule)
        
        # If no tables were found or no content was extracted, try to get all text content
        if len(schedule.items) == 0:
            self._extract_all_text_content(attachment, schedule)
    
    def _process_tables(self, tables, schedule):
        """Process tables and extract their content"""
        for table_idx, table in enumerate(tables):
            table_title = self._get_table_title(table)
            item_number = str(table_idx + 1)
            table_content = self._extract_table_text(table)
            
            if table_content:
                self._create_table_item(table_content, table_title, item_number, schedule)
    
    def _get_table_title(self, table):
        """Get the title of a table from its previous sibling"""
        table_title = ""
        prev_elem = table.find_previous_sibling()
        if prev_elem and prev_elem.name == 'h3':
            table_title = prev_elem.text.strip()
        return table_title
    
    def _extract_table_text(self, table):
        """Extract text content from a table"""
        table_content = []
        
        # Extract headers if present
        self._extract_table_headers(table, table_content)
        
        # Extract rows
        self._extract_table_rows(table, table_content)
        
        return table_content
    
    def _extract_table_headers(self, table, table_content):
        """Extract headers from a table"""
        headers = table.find_all('th')
        if headers:
            header_text = [h.text.strip() for h in headers if h.text.strip()]
            if header_text:
                table_content.append(" | ".join(header_text))
    
    def _extract_table_rows(self, table, table_content):
        """Extract rows from a table"""
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all(['td', 'th'])
            cell_text = [c.text.strip() for c in cells if c.text.strip()]
            if cell_text:
                table_content.append(" | ".join(cell_text))
    
    def _create_table_item(self, table_content, table_title, item_number, schedule):
        """Create a schedule item from table content"""
        content = "\n".join(table_content)
        if table_title:
            content = f"{table_title}\n\n{content}"
        
        item = ScheduleItem(
            item_number=item_number,
            content=content
        )
        
        schedule.items.append(item)
    
    def _extract_all_text_content(self, attachment, schedule):
        """Extract all text content from the schedule"""
        all_text = []
        for p in attachment.find_all('span', class_='akn-p'):
            text = p.text.strip()
            if text:
                all_text.append(text)
        
        if all_text:
            content = "\n".join(all_text)
            item = ScheduleItem(
                item_number="1",
                content=content
            )
            schedule.items.append(item)


def main():
    """Main function to run the extractor"""
    parser = argparse.ArgumentParser(description='Extract Schedules from the Constitution of Kenya HTML')
    parser.add_argument('--input', '-i', type=str, default='test.html',
                        help='Path to input HTML file')
    parser.add_argument('--output', '-o', type=str, default='src/data/processed/schedules.json',
                        help='Path to output JSON file')
    
    args = parser.parse_args()
    
    # Ensure the output directory exists
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    # Extract and save
    extractor = ScheduleExtractor(args.input, args.output)
    extractor.extract()


if __name__ == "__main__":
    main()
