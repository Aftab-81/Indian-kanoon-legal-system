import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import hashlib

class SummaryDatabase:
    """SQLite database for storing case summaries with efficient retrieval."""
    
    def __init__(self, db_path: str = "case_summaries.db"):
        """Initialize database connection and create tables if needed."""
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        self._create_indexes()
    
    def _create_tables(self):
        """Create database tables with optimized schema."""
        cursor = self.conn.cursor()
        
        # Main summaries table with compressed JSON storage
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pdf_hash TEXT UNIQUE NOT NULL,
                case_title TEXT NOT NULL,
                court_name TEXT,
                case_number TEXT,
                judgement_date TEXT,
                summary_type TEXT NOT NULL,
                output_language TEXT DEFAULT 'english',
                summary_data TEXT NOT NULL,
                confidence_score REAL,
                confidence_level TEXT,
                created_at TEXT NOT NULL,
                last_accessed TEXT,
                access_count INTEGER DEFAULT 0,
                file_name TEXT,
                file_size INTEGER
            )
        """)
        
        # Metadata search table for quick filtering
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS summary_metadata (
                summary_id INTEGER PRIMARY KEY,
                judges TEXT,
                sections_invoked TEXT,
                extracted_entities TEXT,
                tags TEXT,
                FOREIGN KEY (summary_id) REFERENCES summaries(id) ON DELETE CASCADE
            )
        """)
        
        # User preferences and settings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        self.conn.commit()
    
    def _create_indexes(self):
        """Create indexes for faster queries."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_summaries_created 
            ON summaries(created_at DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_summaries_confidence 
            ON summaries(confidence_score DESC)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_summaries_type 
            ON summaries(summary_type)
        """)
        
        self.conn.commit()
    
    def _calculate_pdf_hash(self, pdf_content: bytes) -> str:
        """Calculate unique hash for PDF content."""
        return hashlib.sha256(pdf_content).hexdigest()
    
    def save_summary(
        self,
        pdf_content: bytes,
        summary_data: Dict[str, Any],
        summary_type: str,
        output_language: str,
        file_name: str,
        file_size: int
    ) -> int:
        """Save summary to database with deduplication."""
        pdf_hash = self._calculate_pdf_hash(pdf_content)
        
        # Extract metadata for quick search
        metadata = summary_data.get('metadata', {})
        case_title = metadata.get('case_title', 'Unknown Case')
        court_name = metadata.get('court_name', '')
        case_number = metadata.get('case_number', '')
        judgement_date = metadata.get('date_of_judgement', '')
        
        confidence = summary_data.get('confidence_score', {})
        confidence_score = confidence.get('overall_confidence', 0.0)
        confidence_level = confidence.get('confidence_level', 'unknown')
        
        # Check if summary already exists
        existing = self._get_by_hash(pdf_hash, summary_type, output_language)
        if existing:
            # Update access info and return existing ID
            self._update_access(existing['id'])
            return existing['id']
        
        # Insert new summary
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO summaries (
                pdf_hash, case_title, court_name, case_number, judgement_date,
                summary_type, output_language, summary_data,
                confidence_score, confidence_level,
                created_at, last_accessed, access_count,
                file_name, file_size
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pdf_hash, case_title, court_name, case_number, judgement_date,
            summary_type, output_language, json.dumps(summary_data, ensure_ascii=False),
            confidence_score, confidence_level,
            datetime.now().isoformat(), datetime.now().isoformat(), 1,
            file_name, file_size
        ))
        
        summary_id = cursor.lastrowid
        
        # Save metadata for search
        self._save_metadata(summary_id, summary_data)
        
        self.conn.commit()
        return summary_id
    
    def _save_metadata(self, summary_id: int, summary_data: Dict[str, Any]):
        """Save searchable metadata."""
        metadata = summary_data.get('metadata', {})
        
        judges = json.dumps(metadata.get('judge_names', []), ensure_ascii=False)
        sections = json.dumps(metadata.get('sections_invoked', []), ensure_ascii=False)
        
        # Extract entities from detailed summary if available
        entities = summary_data.get('extracted_entities', {})
        entities_json = json.dumps(entities, ensure_ascii=False) if entities else '{}'
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO summary_metadata (
                summary_id, judges, sections_invoked, extracted_entities, tags
            ) VALUES (?, ?, ?, ?, ?)
        """, (summary_id, judges, sections, entities_json, '[]'))
        
        self.conn.commit()
    
    def _get_by_hash(self, pdf_hash: str, summary_type: str, output_language: str) -> Optional[Dict]:
        """Get existing summary by PDF hash."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM summaries 
            WHERE pdf_hash = ? AND summary_type = ? AND output_language = ?
            LIMIT 1
        """, (pdf_hash, summary_type, output_language))
        
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def _update_access(self, summary_id: int):
        """Update last accessed time and increment access count."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE summaries 
            SET last_accessed = ?, access_count = access_count + 1
            WHERE id = ?
        """, (datetime.now().isoformat(), summary_id))
        self.conn.commit()
    
    def get_summary_by_id(self, summary_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve summary by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM summaries WHERE id = ?", (summary_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        self._update_access(summary_id)
        
        return self._row_to_dict(row)
    
    def get_recent_summaries(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """Get recent summaries with pagination."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM summaries 
            ORDER BY created_at DESC 
            LIMIT ? OFFSET ?
        """, (limit, offset))
        
        return [self._row_to_dict(row) for row in cursor.fetchall()]
    
    def search_summaries(
        self,
        query: Optional[str] = None,
        court: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        confidence_min: Optional[float] = None,
        summary_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search summaries with multiple filters."""
        cursor = self.conn.cursor()
        
        sql = "SELECT * FROM summaries WHERE 1=1"
        params = []
        
        if query:
            sql += " AND (case_title LIKE ? OR case_number LIKE ? OR court_name LIKE ?)"
            search_term = f"%{query}%"
            params.extend([search_term, search_term, search_term])
        
        if court:
            sql += " AND court_name LIKE ?"
            params.append(f"%{court}%")
        
        if date_from:
            sql += " AND created_at >= ?"
            params.append(date_from)
        
        if date_to:
            sql += " AND created_at <= ?"
            params.append(date_to)
        
        if confidence_min:
            sql += " AND confidence_score >= ?"
            params.append(confidence_min)
        
        if summary_type:
            sql += " AND summary_type = ?"
            params.append(summary_type)
        
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(sql, params)
        return [self._row_to_dict(row) for row in cursor.fetchall()]
    
    def delete_summary(self, summary_id: int) -> bool:
        """Delete a summary by ID."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM summaries WHERE id = ?", (summary_id,))
        self.conn.commit()
        return cursor.rowcount > 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as total FROM summaries")
        total = cursor.fetchone()['total']
        
        cursor.execute("SELECT summary_type, COUNT(*) as count FROM summaries GROUP BY summary_type")
        by_type = {row['summary_type']: row['count'] for row in cursor.fetchall()}
        
        cursor.execute("SELECT AVG(confidence_score) as avg_confidence FROM summaries")
        avg_confidence = cursor.fetchone()['avg_confidence'] or 0.0
        
        cursor.execute("SELECT SUM(file_size) as total_size FROM summaries")
        total_size = cursor.fetchone()['total_size'] or 0
        
        return {
            "total_summaries": total,
            "by_type": by_type,
            "avg_confidence_score": round(avg_confidence, 2),
            "total_storage_mb": round(total_size / (1024 * 1024), 2),
            "db_file_size_mb": round(self.db_path.stat().st_size / (1024 * 1024), 2)
        }
    
    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert database row to dictionary with parsed JSON."""
        result = dict(row)
        result['summary_data'] = json.loads(result['summary_data'])
        return result
    
    def close(self):
        """Close database connection."""
        self.conn.close()

# Global database instance
_db_instance = None

def get_db() -> SummaryDatabase:
    """Get or create database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = SummaryDatabase()
    return _db_instance
