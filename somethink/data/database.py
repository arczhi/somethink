"""
数据库操作模块
负责文件索引的持久化存储
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
import json


class Database:
    """数据库操作类"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        self._init_database()
    
    def _init_database(self):
        """初始化数据库连接和表结构"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # 使结果可以通过列名访问
        
        self._create_tables()
    
    def _create_tables(self):
        """创建数据库表"""
        cursor = self.conn.cursor()
        
        # 文件表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                filename TEXT NOT NULL,
                extension TEXT,
                file_type TEXT,
                size INTEGER,
                modified_time TIMESTAMP,
                created_time TIMESTAMP,
                content_text TEXT,
                topic_id INTEGER,
                embedding_vector TEXT,
                indexed_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (topic_id) REFERENCES topics(id)
            )
        ''')
        
        # 为path和topic_id创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_path ON files(path)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_topic ON files(topic_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_type ON files(file_type)')
        
        # 主题表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY,
                name TEXT,
                keywords TEXT,
                representative_docs TEXT,
                created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 元数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER NOT NULL,
                key TEXT NOT NULL,
                value TEXT,
                FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_metadata_file ON metadata(file_id)')
        
        # 配置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # 全文搜索虚拟表（用于快速文本搜索）
        cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS files_fts 
            USING fts5(filename, content_text, content='files', content_rowid='id')
        ''')
        
        self.conn.commit()
    
    def insert_file(self, file_info: Dict[str, Any]) -> int:
        """
        插入文件记录
        
        Args:
            file_info: 文件信息字典
            
        Returns:
            插入记录的ID
        """
        cursor = self.conn.cursor()
        
        # 检查文件是否已存在
        cursor.execute('SELECT id FROM files WHERE path = ?', (file_info.get('path'),))
        existing = cursor.fetchone()
        
        if existing:
            # 更新现有记录
            file_id = existing['id']
            cursor.execute('''
                UPDATE files 
                SET filename = ?, extension = ?, file_type = ?, 
                    size = ?, modified_time = ?, created_time = ?, content_text = ?
                WHERE id = ?
            ''', (
                file_info.get('filename'),
                file_info.get('extension'),
                file_info.get('file_type'),
                file_info.get('size'),
                file_info.get('modified_time'),
                file_info.get('created_time'),
                file_info.get('content_text', ''),
                file_id
            ))
            
            # 删除旧的FTS记录
            cursor.execute('DELETE FROM files_fts WHERE rowid = ?', (file_id,))
        else:
            # 插入新记录
            cursor.execute('''
                INSERT INTO files 
                (path, filename, extension, file_type, size, modified_time, created_time, content_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                file_info.get('path'),
                file_info.get('filename'),
                file_info.get('extension'),
                file_info.get('file_type'),
                file_info.get('size'),
                file_info.get('modified_time'),
                file_info.get('created_time'),
                file_info.get('content_text', '')
            ))
            
            file_id = cursor.lastrowid
        
        # 插入或更新全文搜索索引
        cursor.execute('''
            INSERT INTO files_fts(rowid, filename, content_text)
            VALUES (?, ?, ?)
        ''', (file_id, file_info.get('filename'), file_info.get('content_text', '')))
        
        self.conn.commit()
        return file_id
    
    def update_file_topic(self, file_id: int, topic_id: int, embedding: Optional[str] = None):
        """更新文件的主题ID和嵌入向量"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            UPDATE files 
            SET topic_id = ?, embedding_vector = ?
            WHERE id = ?
        ''', (topic_id, embedding, file_id))
        
        self.conn.commit()
    
    def get_file_by_path(self, path: str) -> Optional[Dict]:
        """根据路径获取文件记录"""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT * FROM files WHERE path = ?', (path,))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    def get_file_by_id(self, file_id: int) -> Optional[Dict]:
        """根据ID获取文件记录"""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT * FROM files WHERE id = ?', (file_id,))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    def search_files_by_keyword(self, keyword: str, limit: int = 50) -> List[Dict]:
        """
        使用全文搜索查找文件
        
        Args:
            keyword: 搜索关键词
            limit: 返回结果数量限制
            
        Returns:
            文件记录列表
        """
        cursor = self.conn.cursor()
        
        # 使用FTS5全文搜索
        cursor.execute('''
            SELECT f.* 
            FROM files f
            JOIN files_fts fts ON f.id = fts.rowid
            WHERE files_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        ''', (keyword, limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_files_by_topic(self, topic_id: int, limit: int = 50) -> List[Dict]:
        """获取指定主题的所有文件"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT * FROM files 
            WHERE topic_id = ?
            LIMIT ?
        ''', (topic_id, limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_all_files(self) -> List[Dict]:
        """获取所有文件记录"""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT * FROM files')
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_files_without_topic(self) -> List[Dict]:
        """获取未分配主题的文件"""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT * FROM files WHERE topic_id IS NULL')
        
        return [dict(row) for row in cursor.fetchall()]
    
    def delete_file(self, file_id: int):
        """删除文件记录"""
        cursor = self.conn.cursor()
        
        cursor.execute('DELETE FROM files WHERE id = ?', (file_id,))
        cursor.execute('DELETE FROM files_fts WHERE rowid = ?', (file_id,))
        
        self.conn.commit()
    
    def delete_file_by_path(self, path: str):
        """根据路径删除文件记录"""
        cursor = self.conn.cursor()
        
        # 先获取ID
        file = self.get_file_by_path(path)
        if file:
            self.delete_file(file['id'])
    
    # 主题相关操作
    
    def insert_topic(self, topic_id: int, name: str, keywords: List[str], 
                     representative_docs: List[str] = None):
        """插入主题记录"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO topics (id, name, keywords, representative_docs)
            VALUES (?, ?, ?, ?)
        ''', (
            topic_id,
            name,
            json.dumps(keywords, ensure_ascii=False),
            json.dumps(representative_docs or [], ensure_ascii=False)
        ))
        
        self.conn.commit()
    
    def get_topic(self, topic_id: int) -> Optional[Dict]:
        """获取主题信息"""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT * FROM topics WHERE id = ?', (topic_id,))
        row = cursor.fetchone()
        
        if row:
            topic = dict(row)
            topic['keywords'] = json.loads(topic['keywords'])
            topic['representative_docs'] = json.loads(topic['representative_docs'])
            return topic
        
        return None
    
    def get_all_topics(self) -> List[Dict]:
        """获取所有主题"""
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT * FROM topics ORDER BY id')
        
        topics = []
        for row in cursor.fetchall():
            topic = dict(row)
            topic['keywords'] = json.loads(topic['keywords'])
            topic['representative_docs'] = json.loads(topic['representative_docs'])
            topics.append(topic)
        
        return topics
    
    def get_file_count(self) -> int:
        """获取文件总数"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) as count FROM files')
        return cursor.fetchone()['count']
    
    def get_topic_count(self) -> int:
        """获取主题总数"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) as count FROM topics')
        return cursor.fetchone()['count']
    
    def get_stats(self) -> Dict:
        """获取数据库统计信息"""
        cursor = self.conn.cursor()
        
        stats = {}
        
        # 总文件数
        cursor.execute('SELECT COUNT(*) as count FROM files')
        stats['total_files'] = cursor.fetchone()['count']
        
        # 总主题数
        cursor.execute('SELECT COUNT(*) as count FROM topics')
        stats['total_topics'] = cursor.fetchone()['count']
        
        # 各类型文件数量
        cursor.execute('''
            SELECT file_type, COUNT(*) as count 
            FROM files 
            GROUP BY file_type
        ''')
        stats['files_by_type'] = {row['file_type']: row['count'] for row in cursor.fetchall()}
        
        # 已分类文件数
        cursor.execute('SELECT COUNT(*) as count FROM files WHERE topic_id IS NOT NULL')
        stats['classified_files'] = cursor.fetchone()['count']
        
        return stats
    
    def clear_all_data(self):
        """清空所有数据（慎用）"""
        cursor = self.conn.cursor()
        
        cursor.execute('DELETE FROM files')
        cursor.execute('DELETE FROM topics')
        cursor.execute('DELETE FROM metadata')
        cursor.execute('DELETE FROM files_fts')
        
        self.conn.commit()
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
    
    def __del__(self):
        """析构函数，确保连接关闭"""
        self.close()


if __name__ == "__main__":
    # 测试代码
    db = Database("test.db")
    
    # 插入测试文件
    file_info = {
        'path': '/test/file.txt',
        'filename': 'file.txt',
        'extension': '.txt',
        'file_type': 'document',
        'size': 1024,
        'modified_time': datetime.now(),
        'created_time': datetime.now(),
        'content_text': 'This is a test file about machine learning.'
    }
    
    file_id = db.insert_file(file_info)
    print(f"插入文件ID: {file_id}")
    
    # 搜索测试
    results = db.search_files_by_keyword("machine learning")
    print(f"搜索结果: {results}")
    
    # 统计信息
    stats = db.get_stats()
    print(f"统计信息: {stats}")
    
    db.close()
