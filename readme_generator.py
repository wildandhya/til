"""
README Generator for TIL (Today I Learned) Database
------------------------------------------------
This script generates a formatted README.md file from a SQLite database of TIL entries.
It updates index sections, category listings, and entry counts in the README.
If the database or table doesn't exist, it will create them automatically.

Prerequisites:
    - Required packages: sqlite_utils, pathlib
    
Usage:
    python update_readme.py [--rewrite]
    --rewrite: Updates README.md file directly instead of printing to stdout
"""

import pathlib
import sqlite_utils
import sys
import re
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Constants
README_FILENAME = "README.md"
DATABASE_FILENAME = "tils.db"
TABLE_NAME = "til"

# Database schema definition
TABLE_SCHEMA = {
    "title": str,
    "url": str,
    "topic": str,
    "created": str,
    "created_utc": float
}

# Regular expressions for section markers
PATTERNS = {
    'index': re.compile(r"<!\-\- index starts \-\->.*<!\-\- index ends \-\->", re.DOTALL),
    'count': re.compile(r"<!\-\- count starts \-\->.*<!\-\- count ends \-\->", re.DOTALL),
    'category': re.compile(r"<!\-\- category starts \-\->.*<!\-\- category ends \-\->", re.DOTALL)
}

TEMPLATES = {
    'count': "<!-- count starts -->{}<!-- count ends -->",
    'index_start': "<!-- index starts -->",
    'index_end': "<!-- index ends -->",
    'category_start': "<!-- category starts -->",
    'category_end': "<!-- category ends -->"
}

@dataclass
class TILEntry:
    """Represents a single TIL entry."""
    title: str
    url: str
    topic: str
    created: str
    created_utc: float

class ReadmeGenerator:
    def __init__(self, root_path: pathlib.Path):
        self.root = root_path
        self.db_path = root_path / DATABASE_FILENAME
        self.readme_path = root_path / README_FILENAME
        self.db = None

    def connect_db(self) -> None:
        """Establishes database connection and ensures table exists."""
        try:
            self.db = sqlite_utils.Database(self.db_path)
            self._ensure_table_exists()
        except Exception as e:
            logging.error(f"Database connection failed: {e}")
            raise

    def _ensure_table_exists(self) -> None:
        """Creates the TIL table if it doesn't exist."""
        if TABLE_NAME not in self.db.table_names():
            logging.info(f"Creating table '{TABLE_NAME}'")
            self.db.create_table(
                TABLE_NAME,
                TABLE_SCHEMA,
                pk="url",
                not_null={"title", "url", "topic", "created", "created_utc"}
            )
            # Create indexes for better performance
            self.db[TABLE_NAME].create_index(["topic"])
            self.db[TABLE_NAME].create_index(["created_utc"])
            logging.info(f"Table '{TABLE_NAME}' created successfully")

    def get_entries_by_topic(self) -> Dict[str, List[TILEntry]]:
        """Retrieves all TIL entries grouped by topic."""
        by_topic = {}
        try:
            for row in self.db[TABLE_NAME].rows_where(order_by="created_utc"):
                entry = TILEntry(
                    title=row["title"],
                    url=row["url"],
                    topic=row["topic"],
                    created=row["created"],
                    created_utc=row["created_utc"]
                )
                by_topic.setdefault(entry.topic, []).append(entry)
        except Exception as e:
            logging.error(f"Error retrieving entries: {e}")
            raise
        return by_topic

    def generate_index(self, by_topic: Dict[str, List[TILEntry]]) -> str:
        """Generates the index section of the README."""
        index = [TEMPLATES['index_start']]
        
        for topic, entries in sorted(by_topic.items()):
            index.append(f"## {topic}\n")
            for entry in entries:
                date = entry.created.split("T")[0]
                index.append(
                    f"* [{entry.title}]({entry.url}) - {date}"
                )
            index.append("")
        
        if index[-1] == "":
            index.pop()
        index.append(TEMPLATES['index_end'])
        return "\n".join(index).strip()

    def generate_category(self, by_topic: Dict[str, List[TILEntry]]) -> str:
        """Generates the category section of the README."""
        category = [TEMPLATES['category_start']]
        
        for topic in sorted(by_topic.keys()):
            category.append(
                f"* [{topic}](#{topic.lower().replace(' ', '-')})"
            )
        
        category.append(TEMPLATES['category_end'])
        return "\n".join(category).strip()

    def update_readme(self, rewrite: bool = False) -> None:
        """Updates README content either by printing or rewriting the file."""
        try:
            self.connect_db()
            by_topic = self.get_entries_by_topic()
            
            index_content = self.generate_index(by_topic)
            category_content = self.generate_category(by_topic)
            count = self.db[TABLE_NAME].count
            
            if rewrite:
                self._rewrite_readme(index_content, category_content, count)
                logging.info(f"Successfully updated {README_FILENAME}")
            else:
                print(index_content)
                
        except Exception as e:
            logging.error(f"Failed to update README: {e}")
            sys.exit(1)

    def _rewrite_readme(self, index_content: str, category_content: str, count: int) -> None:
        """Rewrites the README file with new content."""
        try:
            with open(self.readme_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Update all sections
            for pattern, replacement in [
                (PATTERNS['category'], category_content),
                (PATTERNS['index'], index_content),
                (PATTERNS['count'], TEMPLATES['count'].format(count))
            ]:
                content = pattern.sub(replacement, content)

            with open(self.readme_path, 'w', encoding='utf-8') as f:
                f.write(content)

        except Exception as e:
            logging.error(f"Failed to rewrite README file: {e}")
            raise

def main():
    root = pathlib.Path(__file__).parent.resolve()
    generator = ReadmeGenerator(root)
    generator.update_readme(rewrite="--rewrite" in sys.argv)

if __name__ == "__main__":
    main()