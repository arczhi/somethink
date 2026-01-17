"""
文件索引器
负责扫描文件并建立索引
"""

import os
from pathlib import Path
from typing import List, Callable, Optional
from datetime import datetime
import threading

from utils.file_scanner import FileScanner
from utils.config import config
from data.database import Database


class Indexer:
    """文件索引器"""
    
    def __init__(self, database: Database):
        self.db = database
        self.scanner = FileScanner(exclude_patterns=config.get("exclude_patterns", []))
        self.is_indexing = False
        self.index_thread = None
        self.progress_callback = None
        
    def start_indexing(self, paths: List[str], 
                      progress_callback: Optional[Callable] = None,
                      complete_callback: Optional[Callable] = None):
        """
        开始索引指定路径
        
        Args:
            paths: 要索引的路径列表
            progress_callback: 进度回调函数 (current, total, message)
            complete_callback: 完成回调函数
        """
        if self.is_indexing:
            print("索引正在进行中...")
            return
        
        self.progress_callback = progress_callback
        
        # 在新线程中执行索引
        self.index_thread = threading.Thread(
            target=self._index_worker,
            args=(paths, complete_callback)
        )
        self.index_thread.daemon = True
        self.index_thread.start()
    
    def _index_worker(self, paths: List[str], complete_callback: Optional[Callable] = None):
        """索引工作线程"""
        self.is_indexing = True
        
        total_files = 0
        indexed_files = 0
        
        try:
            # 第一遍：统计文件数量
            if self.progress_callback:
                self.progress_callback(0, 0, "正在扫描文件...")
            
            all_files = []
            for path in paths:
                for file_info in self.scanner.scan_directory(path):
                    all_files.append(file_info)
            
            total_files = len(all_files)
            
            # 第二遍：处理文件
            for i, file_info in enumerate(all_files, 1):
                try:
                    self._index_file(file_info)
                    indexed_files += 1
                    
                    if self.progress_callback:
                        self.progress_callback(
                            i, total_files, 
                            f"正在索引: {file_info['filename']}"
                        )
                
                except Exception as e:
                    print(f"索引文件 {file_info['path']} 失败: {e}")
            
            print(f"索引完成: 共处理 {indexed_files}/{total_files} 个文件")
            
            if complete_callback:
                complete_callback(indexed_files, total_files)
        
        except Exception as e:
            print(f"索引过程出错: {e}")
        
        finally:
            self.is_indexing = False
    
    def _index_file(self, file_info: dict):
        """索引单个文件"""
        # 检查文件是否已存在
        existing = self.db.get_file_by_path(file_info['path'])
        
        # 如果存在且未修改，跳过
        if existing:
            existing_mtime = datetime.fromisoformat(str(existing['modified_time']))
            new_mtime = file_info['modified_time']
            
            if existing_mtime >= new_mtime:
                return  # 文件未修改，跳过
        
        # 提取文本内容
        try:
            file_path = Path(file_info['path'])
            content_text = self.scanner.extract_text_content(file_path)
            file_info['content_text'] = content_text
        except Exception as e:
            print(f"提取文件内容失败 {file_info['path']}: {e}")
            file_info['content_text'] = ""
        
        # 插入数据库
        self.db.insert_file(file_info)
    
    def update_single_file(self, file_path: str):
        """更新单个文件的索引"""
        path = Path(file_path)
        
        if not path.exists():
            # 文件不存在，从数据库删除
            self.db.delete_file_by_path(file_path)
            return
        
        # 获取文件信息并索引
        if self.scanner.is_supported(path):
            file_info = self.scanner.get_file_info(path)
            self._index_file(file_info)
    
    def remove_file(self, file_path: str):
        """从索引中移除文件"""
        self.db.delete_file_by_path(file_path)
    
    def get_index_status(self) -> dict:
        """获取索引状态"""
        return {
            'is_indexing': self.is_indexing,
            'stats': self.db.get_stats()
        }
    
    def wait_for_completion(self):
        """等待索引完成"""
        if self.index_thread and self.index_thread.is_alive():
            self.index_thread.join()


if __name__ == "__main__":
    # 测试代码
    from utils.config import config
    
    db = Database(str(config.db_file))
    indexer = Indexer(db)
    
    def progress(current, total, message):
        print(f"[{current}/{total}] {message}")
    
    def complete(indexed, total):
        print(f"索引完成！成功: {indexed}, 总计: {total}")
    
    # 测试索引
    test_paths = [str(Path.home() / "Documents")]
    indexer.start_indexing(test_paths, progress, complete)
    indexer.wait_for_completion()
    
    # 显示统计
    stats = db.get_stats()
    print(f"数据库统计: {stats}")
