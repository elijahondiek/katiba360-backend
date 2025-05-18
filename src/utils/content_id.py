"""
Utility functions for handling standardized content IDs in the Katiba360 application.

Content IDs are hierarchical path-based identifiers that represent constitution elements
such as chapters, articles, clauses, and subclauses in a consistent, human-readable format.

Format: "chapter:{chapter}[:article:{article}[:clause:{clause}[:subclause:{subclause}]]]"
Examples:
- "chapter:1"
- "chapter:1:article:2"
- "chapter:1:article:2:clause:3"
- "chapter:1:article:2:clause:3:subclause:a"
"""

from typing import Dict, Any, Optional, Tuple, List, Union


def create_content_id(content_type: str, chapter: int, article: Optional[int] = None, 
                     clause: Optional[int] = None, subclause: Optional[str] = None) -> str:
    """
    Generate standardized content ID for constitution elements.
    
    Args:
        content_type: Type of content (chapter, article, clause, subclause)
        chapter: Chapter number
        article: Optional article number
        clause: Optional clause number
        subclause: Optional subclause identifier
        
    Returns:
        Standardized content ID string
    """
    parts = [f"chapter:{chapter}"]
    
    if article is not None:
        parts.append(f"article:{article}")
    
    if clause is not None:
        parts.append(f"clause:{clause}")
        
    if subclause is not None:
        parts.append(f"subclause:{subclause}")
    
    # Add content type as metadata
    # This helps with filtering and querying
    parts.append(f"type:{content_type}")
        
    return ":".join(parts)


def parse_content_id(content_id: str) -> Dict[str, Any]:
    """
    Parse content ID into its components.
    
    Args:
        content_id: Standardized content ID string
        
    Returns:
        Dictionary of content ID components
        
    Example:
        parse_content_id("chapter:1:article:2:type:article")
        Returns: {"chapter": 1, "article": 2, "type": "article"}
    """
    parts = content_id.split(":")
    result = {}
    
    for i in range(0, len(parts), 2):
        if i+1 < len(parts):
            key = parts[i]
            try:
                # Try to convert to int if possible
                value = int(parts[i+1])
            except ValueError:
                value = parts[i+1]
            result[key] = value
            
    return result


def is_valid_content_id(content_id: str) -> bool:
    """
    Validate if a string is a properly formatted content ID.
    
    Args:
        content_id: String to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        parts = content_id.split(":")
        
        # Must have at least chapter and type
        if len(parts) < 4:
            return False
            
        # Must have even number of parts (key:value pairs)
        if len(parts) % 2 != 0:
            return False
            
        # First part must be "chapter"
        if parts[0] != "chapter":
            return False
            
        # Must have a type
        if "type" not in parts:
            return False
            
        # Check for valid hierarchy
        components = ["chapter", "article", "clause", "subclause"]
        last_found_idx = -1
        
        for i in range(0, len(parts), 2):
            if i+1 >= len(parts):
                break
                
            key = parts[i]
            if key in components:
                current_idx = components.index(key)
                if current_idx <= last_found_idx and last_found_idx != -1:
                    # Components must be in order and not repeated
                    return False
                last_found_idx = current_idx
                
        return True
        
    except Exception:
        return False


def get_content_type(content_id: str) -> Optional[str]:
    """
    Extract the content type from a content ID.
    
    Args:
        content_id: Standardized content ID string
        
    Returns:
        Content type or None if not found
    """
    parts = content_id.split(":")
    for i in range(0, len(parts), 2):
        if i+1 < len(parts) and parts[i] == "type":
            return parts[i+1]
    return None


def get_parent_content_id(content_id: str) -> Optional[str]:
    """
    Get the parent content ID by removing the last component.
    
    Args:
        content_id: Standardized content ID string
        
    Returns:
        Parent content ID or None if at top level
    """
    if not is_valid_content_id(content_id):
        return None
        
    parsed = parse_content_id(content_id)
    
    if "subclause" in parsed:
        # Remove subclause
        new_type = "clause"
        return create_content_id(
            new_type, 
            parsed["chapter"], 
            parsed.get("article"), 
            parsed.get("clause")
        )
    elif "clause" in parsed:
        # Remove clause
        new_type = "article"
        return create_content_id(
            new_type, 
            parsed["chapter"], 
            parsed.get("article")
        )
    elif "article" in parsed:
        # Remove article
        new_type = "chapter"
        return create_content_id(
            new_type, 
            parsed["chapter"]
        )
    else:
        # Already at top level
        return None


def content_id_to_display(content_id: str) -> str:
    """
    Convert a content ID to a human-readable display string.
    
    Args:
        content_id: Standardized content ID string
        
    Returns:
        Human-readable display string
        
    Example:
        content_id_to_display("chapter:1:article:2:type:article")
        Returns: "Chapter 1, Article 2"
    """
    if not is_valid_content_id(content_id):
        return content_id
        
    parsed = parse_content_id(content_id)
    parts = []
    
    if "chapter" in parsed:
        parts.append(f"Chapter {parsed['chapter']}")
        
    if "article" in parsed:
        parts.append(f"Article {parsed['article']}")
        
    if "clause" in parsed:
        parts.append(f"Clause {parsed['clause']}")
        
    if "subclause" in parsed:
        parts.append(f"Subclause {parsed['subclause']}")
        
    return ", ".join(parts)
