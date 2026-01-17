"""
搜索匹配器
负责根据关键词和语义进行文件搜索
"""

from typing import List, Dict, Tuple
import re
from pathlib import Path

from data.database import Database


class Searcher:
    """搜索引擎"""
    
    def __init__(self, database: Database, topic_model=None):
        self.db = database
        self.topic_model = topic_model
        
    def search(self, query: str, max_results: int = 50, 
               use_semantic: bool = True) -> List[Tuple[Dict, float]]:
        """
        综合搜索
        
        Args:
            query: 搜索查询词
            max_results: 最大结果数
            use_semantic: 是否使用语义搜索
            
        Returns:
            [(文件信息, 相关度分数), ...] 列表，按相关度降序
        """
        if not query.strip():
            return []
        
        # 1. 关键词搜索（权重40%）
        keyword_results = self._keyword_search(query, max_results * 2)
        
        # 2. 语义搜索（权重50%）
        semantic_results = []
        if use_semantic and self.topic_model:
            semantic_results = self._semantic_search(query, max_results * 2)
        
        # 3. 合并结果并计算综合分数
        combined_results = self._combine_results(
            keyword_results, 
            semantic_results,
            keyword_weight=0.4,
            semantic_weight=0.5 if use_semantic else 0
        )
        
        # 返回Top N结果
        return combined_results[:max_results]
    
    def _keyword_search(self, query: str, limit: int) -> List[Tuple[Dict, float]]:
        """
        关键词搜索
        
        Returns:
            [(文件, 分数), ...]
        """
        # 使用全文搜索
        results = self.db.search_files_by_keyword(query, limit)
        
        # 简单的TF-IDF风格评分
        scored_results = []
        
        for file in results:
            score = 0.0
            
            # 文件名匹配
            if query.lower() in file['filename'].lower():
                score += 0.5
            
            # 内容匹配
            content = file.get('content_text', '') or ''
            if content:
                # 统计关键词出现次数
                query_lower = query.lower()
                content_lower = content.lower()
                
                count = content_lower.count(query_lower)
                # 归一化（避免长文档得分过高）
                normalized_count = count / max(len(content.split()), 1) * 100
                score += min(normalized_count, 0.5)
            
            scored_results.append((file, score))
        
        # 按分数降序排序
        scored_results.sort(key=lambda x: x[1], reverse=True)
        
        return scored_results
    
    def _semantic_search(self, query: str, limit: int) -> List[Tuple[Dict, float]]:
        """
        语义搜索（基于主题模型）
        
        Returns:
            [(文件, 分数), ...]
        """
        if not self.topic_model:
            return []
        
        try:
            # 使用主题模型查找相似文档
            similar_docs = self.topic_model.find_similar_documents(query, top_n=limit)
            
            # 转换为标准格式
            scored_results = []
            for doc_info in similar_docs:
                file = self.db.get_file_by_id(doc_info['file_id'])
                if file:
                    scored_results.append((file, doc_info['similarity']))
            
            return scored_results
        
        except Exception as e:
            print(f"语义搜索失败: {e}")
            return []
    
    def _combine_results(self, keyword_results: List[Tuple[Dict, float]], 
                        semantic_results: List[Tuple[Dict, float]],
                        keyword_weight: float = 0.4,
                        semantic_weight: float = 0.5,
                        metadata_weight: float = 0.1) -> List[Tuple[Dict, float]]:
        """
        合并不同搜索策略的结果
        
        Returns:
            [(文件, 综合分数), ...] 按综合分数降序
        """
        # 使用字典避免重复，key为文件路径
        combined = {}
        
        # 处理关键词搜索结果
        for file, score in keyword_results:
            path = file['path']
            if path not in combined:
                combined[path] = {'file': file, 'keyword_score': 0, 'semantic_score': 0}
            combined[path]['keyword_score'] = score
        
        # 处理语义搜索结果
        for file, score in semantic_results:
            path = file['path']
            if path not in combined:
                combined[path] = {'file': file, 'keyword_score': 0, 'semantic_score': 0}
            combined[path]['semantic_score'] = score
        
        # 计算综合分数
        final_results = []
        
        for path, data in combined.items():
            # 归一化各项分数到[0, 1]
            kw_score = min(data['keyword_score'], 1.0)
            sem_score = min(data['semantic_score'], 1.0)
            
            # 加权求和
            final_score = (
                keyword_weight * kw_score + 
                semantic_weight * sem_score +
                metadata_weight * 0  # 元数据评分待实现
            )
            
            final_results.append((data['file'], final_score))
        
        # 按综合分数降序排序
        final_results.sort(key=lambda x: x[1], reverse=True)
        
        return final_results
    
    def search_by_type(self, file_type: str, query: str = "", 
                       max_results: int = 50) -> List[Dict]:
        """
        按文件类型搜索
        
        Args:
            file_type: 文件类型 (document, image, audio, video)
            query: 可选的查询词
            max_results: 最大结果数
        """
        # TODO: 实现按类型的搜索
        pass
    
    def get_recent_files(self, days: int = 7, limit: int = 50) -> List[Dict]:
        """
        获取最近修改的文件
        
        Args:
            days: 最近多少天
            limit: 返回数量
        """
        # TODO: 实现最近文件查询
        pass


if __name__ == "__main__":
    # 测试代码
    from utils.config import config
    from data.database import Database
    
    db = Database(str(config.db_file))
    searcher = Searcher(db)
    
    # 测试搜索
    results = searcher.search("machine learning", max_results=10, use_semantic=False)
    
    print(f"找到 {len(results)} 个结果:")
    for file, score in results:
        print(f"  [{score:.2f}] {file['filename']}")
