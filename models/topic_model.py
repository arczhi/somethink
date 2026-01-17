"""
主题模型管理器
基于BERTopic进行文档主题建模和相似度搜索
"""

import os
import pickle
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import numpy as np

from data.database import Database
from utils.config import config


class TopicModel:
    """主题模型管理类"""
    
    def __init__(self, database: Database, model_name: str = None):
        self.db = database
        self.model_name = model_name or config.get_model_name()
        
        self.embedding_model = None
        self.topic_model = None
        self.documents = []
        self.embeddings = None
        
        self.model_path = config.models_dir / "topic_model.pkl"
        self.embeddings_path = config.models_dir / "embeddings.npy"
        
    def load_or_create_model(self):
        """加载已有模型或创建新模型"""
        if self._model_exists():
            print("加载已有主题模型...")
            self._load_model()
        else:
            print("创建新主题模型...")
            self._create_model()
    
    def _model_exists(self) -> bool:
        """检查模型是否存在"""
        return self.model_path.exists()
    
    def _load_embedding_model(self):
        """加载嵌入模型"""
        if self.embedding_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                import torch
                print(f"正在加载嵌入模型: {self.model_name}")
                # 自动检测GPU
                if torch.cuda.is_available():
                    device = 'cuda'
                    print("检测到GPU，使用GPU加速")
                else:
                    device = 'cpu'
                    print("未检测到GPU，使用CPU")
                self.embedding_model = SentenceTransformer(
                    self.model_name,
                    device=device
                )
                print("嵌入模型加载完成")
            except Exception as e:
                print(f"加载嵌入模型失败: {e}")
                # 如果失败，尝试降级方案：不使用语义搜索
                print("将禁用语义搜索功能，仅使用关键词搜索")
                self.embedding_model = None
                return
    
    def _create_model(self):
        """创建新的主题模型"""
        # 1. 加载嵌入模型
        self._load_embedding_model()
        
        # 如果模型加载失败，跳过主题建模
        if self.embedding_model is None:
            print("嵌入模型未加载，跳过主题建模")
            return
        
        # 2. 从数据库获取所有文档
        files = self.db.get_all_files()
        
        if len(files) == 0:
            print("没有可用的文档，跳过主题建模")
            return
        
        # 3. 准备文档文本
        self.documents = []
        file_ids = []
        
        for file in files:
            content = file.get('content_text', '') or ''
            if content.strip():
                self.documents.append(content)
                file_ids.append(file['id'])
        
        if len(self.documents) < 10:
            print(f"文档数量不足（{len(self.documents)} < 10），跳过主题建模")
            return
        
        print(f"准备对 {len(self.documents)} 个文档进行主题建模...")
        
        # 4. 生成文档嵌入
        print("生成文档嵌入向量...")
        self.embeddings = self.embedding_model.encode(
            self.documents, 
            show_progress_bar=True,
            convert_to_numpy=True
        )
        
        # 5. 训练BERTopic模型
        print("训练主题模型...")
        self._train_topic_model()
        
        # 6. 保存主题信息到数据库
        self._save_topics_to_db(file_ids)
        
        # 7. 保存模型
        self._save_model()
        
        print("主题模型创建完成！")
    
    def _train_topic_model(self):
        """训练BERTopic模型"""
        try:
            from bertopic import BERTopic
            from umap import UMAP
            from hdbscan import HDBSCAN
            from sklearn.feature_extraction.text import CountVectorizer
            
            # 配置UMAP（降维）
            umap_model = UMAP(
                n_neighbors=15,
                n_components=5,
                min_dist=0.0,
                metric='cosine',
                random_state=42
            )
            
            # 配置HDBSCAN（聚类）
            hdbscan_model = HDBSCAN(
                min_cluster_size=5,
                min_samples=3,
                metric='euclidean',
                cluster_selection_method='eom'
            )
            
            # 配置词向量化（用于主题表示）
            vectorizer_model = CountVectorizer(
                max_features=1000,
                stop_words='english',  # 可以添加中文停用词
                ngram_range=(1, 2)
            )
            
            # 创建BERTopic模型
            self.topic_model = BERTopic(
                embedding_model=self.embedding_model,
                umap_model=umap_model,
                hdbscan_model=hdbscan_model,
                vectorizer_model=vectorizer_model,
                top_n_words=10,
                language='multilingual',
                calculate_probabilities=False,  # 节省内存
                verbose=True
            )
            
            # 训练模型（使用预计算的嵌入）
            topics, probs = self.topic_model.fit_transform(
                self.documents, 
                self.embeddings
            )
            
            # 输出主题信息
            topic_info = self.topic_model.get_topic_info()
            print(f"\n发现 {len(topic_info) - 1} 个主题:")  # -1 because topic -1 is outliers
            print(topic_info.head(10))
            
        except Exception as e:
            print(f"训练主题模型失败: {e}")
            raise
    
    def _save_topics_to_db(self, file_ids: List[int]):
        """保存主题信息到数据库"""
        if not self.topic_model:
            return
        
        # 获取文档的主题分配
        topics = self.topic_model.topics_
        
        # 保存主题信息
        topic_info = self.topic_model.get_topic_info()
        
        for _, row in topic_info.iterrows():
            topic_id = int(row['Topic'])
            
            if topic_id == -1:  # 跳过离群点
                continue
            
            # 获取主题关键词
            topic_words = self.topic_model.get_topic(topic_id)
            keywords = [word for word, _ in topic_words] if topic_words else []
            
            # 主题名称（使用前3个关键词）
            topic_name = "_".join(keywords[:3]) if keywords else f"Topic_{topic_id}"
            
            # 保存到数据库
            self.db.insert_topic(
                topic_id=topic_id,
                name=topic_name,
                keywords=keywords
            )
        
        # 更新文件的主题分配
        for file_id, topic_id in zip(file_ids, topics):
            if topic_id != -1:  # 跳过离群点
                self.db.update_file_topic(file_id, topic_id)
    
    def _save_model(self):
        """保存模型到文件"""
        try:
            # 保存BERTopic模型
            with open(self.model_path, 'wb') as f:
                pickle.dump(self.topic_model, f)
            
            # 保存嵌入向量
            np.save(self.embeddings_path, self.embeddings)
            
            print(f"模型已保存到 {self.model_path}")
        
        except Exception as e:
            print(f"保存模型失败: {e}")
    
    def _load_model(self):
        """从文件加载模型"""
        try:
            # 加载嵌入模型
            self._load_embedding_model()
            
            # 加载BERTopic模型
            with open(self.model_path, 'rb') as f:
                self.topic_model = pickle.load(f)
            
            # 加载嵌入向量
            if self.embeddings_path.exists():
                self.embeddings = np.load(self.embeddings_path)
            
            print("模型加载成功")
        
        except Exception as e:
            print(f"加载模型失败: {e}")
            raise
    
    def find_similar_documents(self, query: str, top_n: int = 10) -> List[Dict]:
        """
        查找与查询相似的文档
        
        Args:
            query: 查询文本
            top_n: 返回前N个结果
            
        Returns:
            [{'file_id': int, 'similarity': float}, ...]
        """
        if not self.embedding_model:
            self._load_embedding_model()
        
        if self.embeddings is None or len(self.embeddings) == 0:
            return []
        
        # 生成查询的嵌入
        query_embedding = self.embedding_model.encode([query], convert_to_numpy=True)[0]
        
        # 计算余弦相似度
        from sklearn.metrics.pairwise import cosine_similarity
        
        similarities = cosine_similarity([query_embedding], self.embeddings)[0]
        
        # 获取Top-N索引
        top_indices = np.argsort(similarities)[::-1][:top_n]
        
        # 获取对应的文件ID
        files = self.db.get_all_files()
        
        results = []
        for idx in top_indices:
            if idx < len(files):
                results.append({
                    'file_id': files[idx]['id'],
                    'similarity': float(similarities[idx])
                })
        
        return results
    
    def get_topic_by_query(self, query: str) -> Optional[Dict]:
        """根据查询获取最相关的主题"""
        if not self.topic_model:
            return None
        
        try:
            # 预测主题
            topic, _ = self.topic_model.transform([query])
            topic_id = topic[0]
            
            if topic_id == -1:
                return None
            
            # 从数据库获取主题信息
            return self.db.get_topic(topic_id)
        
        except Exception as e:
            print(f"主题预测失败: {e}")
            return None
    
    def rebuild_model(self):
        """重建主题模型"""
        print("重建主题模型...")
        
        # 删除旧模型文件
        if self.model_path.exists():
            self.model_path.unlink()
        if self.embeddings_path.exists():
            self.embeddings_path.unlink()
        
        # 创建新模型
        self._create_model()
    
    def get_model_info(self) -> Dict:
        """获取模型信息"""
        return {
            'model_name': self.model_name,
            'model_exists': self._model_exists(),
            'num_topics': self.db.get_topic_count(),
            'num_documents': len(self.documents) if self.documents else 0
        }


if __name__ == "__main__":
    # 测试代码
    from data.database import Database
    from utils.config import config
    
    db = Database(str(config.db_file))
    topic_model = TopicModel(db)
    
    # 加载或创建模型
    topic_model.load_or_create_model()
    
    # 测试相似文档搜索
    query = "machine learning algorithms"
    results = topic_model.find_similar_documents(query, top_n=5)
    
    print(f"\n与 '{query}' 相似的文档:")
    for result in results:
        file = db.get_file_by_id(result['file_id'])
        if file:
            print(f"  [{result['similarity']:.3f}] {file['filename']}")
    
    # 显示模型信息
    info = topic_model.get_model_info()
    print(f"\n模型信息: {info}")
