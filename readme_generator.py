"""
README Generator for TIL (Today I Learned) Database
------------------------------------------------
This script generates a formatted README.md file from a SQLite database of TIL entries.
It updates index sections, category listings, and entry counts in the README.
The database should be built first using build_database.py.

Prerequisites:
    - Required packages: sqlite_utils, pathlib, git
    
Usage:
    python update_readme.py [--rewrite]
    --rewrite: Updates README.md file directly instead of printing to stdout
"""

import pathlib
import sqlite_utils
import sys
import re
import logging
import git
from datetime import timezone
from typing import Dict, List
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

# Updated Database schema definition to match build_database.py
TABLE_SCHEMA = {
    "path": str,
    "topic": str,
    "title": str,
    "url": str,
    "body": str,
    "created": str,
    "created_utc": str,
    "updated": str,
    "updated_utc": str
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
    path: str
    topic: str
    title: str
    url: str
    body: str
    created: str
    created_utc: str
    updated: str
    updated_utc: str

def created_changed_times(repo_path, ref="main"):
    """Get creation and update times for all files in the repository."""
    created_changed_times = {}
    repo = git.Repo(repo_path, odbt=git.GitDB)
    commits = reversed(list(repo.iter_commits(ref)))
    for commit in commits:
        dt = commit.committed_datetime
        affected_files = list(commit.stats.files.keys())
        for filepath in affected_files:
            if filepath not in created_changed_times:
                created_changed_times[filepath] = {
                    "created": dt.isoformat(),
                    "created_utc": dt.astimezone(timezone.utc).isoformat(),
                }
            created_changed_times[filepath].update(
                {
                    "updated": dt.isoformat(),
                    "updated_utc": dt.astimezone(timezone.utc).isoformat(),
                }
            )
    return created_changed_times

def build_database(repo_path):
    """Build/update the database from markdown files."""
    all_times = created_changed_times(repo_path)
    db = sqlite_utils.Database(repo_path / DATABASE_FILENAME)
    table = db.table(TABLE_NAME, pk="path")
    
    records = []
    for filepath in repo_path.glob("*/*.md"):
        with filepath.open() as fp:
            title = fp.readline().lstrip("#").strip()
            body = fp.read().strip()
            
        path = str(filepath.relative_to(repo_path))
        url = f"https://github.com/wildandhya/til/blob/main/{path}"
        record = {
            "path": path.replace("/", "_"),
            "topic": path.split("/")[0],
            "title": title,
            "url": url,
            "body": body,
        }
        
        # Only update if the file exists in git history
        if path in all_times:
            record.update(all_times[path])
            records.append(record)
        else:
            logging.warning(f"File {path} not found in git history")

    table.upsert_all(records, pk="path")
    
    # full-text search
    if "til_fts" not in db.table_names():
        table.enable_fts(["title", "body"])

class ReadmeGenerator:
    def __init__(self, root_path: pathlib.Path):
        self.root = root_path
        self.db_path = root_path / DATABASE_FILENAME
        self.readme_path = root_path / README_FILENAME
        self.db = None

    def connect_db(self) -> None:
        """Establishes database connection."""
        try:
            self.db = sqlite_utils.Database(self.db_path)
        except Exception as e:
            logging.error(f"Database connection failed: {e}")
            raise

    def get_entries_by_topic(self) -> Dict[str, List[TILEntry]]:
        """Retrieves all TIL entries grouped by topic."""
        by_topic = {}
        try:
            for row in self.db[TABLE_NAME].rows_where(order_by="created_utc"):
                entry = TILEntry(**row)
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
            for entry in sorted(entries, key=lambda x: x.created_utc, reverse=True):
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
            entry_count = len(by_topic[topic])
            category.append(
                f"* [{topic}](#{topic.lower()}) ({entry_count} TILs)"
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

            # Update each section individually to preserve formatting
            content = PATTERNS['category'].sub(category_content, content)
            content = PATTERNS['index'].sub(index_content, content)
            content = PATTERNS['count'].sub(TEMPLATES['count'].format(count), content)

            # Write the updated content back to the file
            with open(self.readme_path, 'w', encoding='utf-8') as f:
                f.write(content)

        except Exception as e:
            logging.error(f"Failed to rewrite README file: {e}")
            raise

def main():
    root = pathlib.Path(__file__).parent.resolve()
    
    # First build/update the database
    build_database(root)
    
    # Then generate the README
    generator = ReadmeGenerator(root)
    generator.update_readme(rewrite="--rewrite" in sys.argv)

if __name__ == "__main__":
    main()