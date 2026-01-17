"""
SomeThink 主程序入口
整合所有模块，提供统一的应用控制器
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
if getattr(sys, 'frozen', False):
    # PyInstaller打包后的环境
    app_dir = Path(sys.executable).parent
else:
    # 本地开发环境
    app_dir = Path(__file__).parent

sys.path.insert(0, str(app_dir))

from utils.config import config
from data.database import Database
from engine.indexer import Indexer
from engine.searcher import Searcher
from models.topic_model import TopicModel
from gui.main_window import MainWindow


class SomeThinkApp:
    """SomeThink应用控制器"""
    
    def __init__(self):
        # 初始化数据库
        self.db = Database(str(config.db_file))
        
        # 初始化索引器
        self.indexer = Indexer(self.db)
        
        # 初始化主题模型
        self.topic_model = None
        self._init_topic_model()
        
        # 初始化搜索器
        self.searcher = Searcher(self.db, self.topic_model)
        
        # GUI窗口
        self.window = None
    
    def _init_topic_model(self):
        """初始化主题模型"""
        try:
            print("初始化主题模型...")
            self.topic_model = TopicModel(self.db)
            
            # 检查是否需要创建模型
            if self.db.get_file_count() > 0:
                self.topic_model.load_or_create_model()
            else:
                print("数据库为空，跳过主题模型加载")
        
        except Exception as e:
            print(f"主题模型初始化失败: {e}")
            print("将以仅关键词搜索模式运行")
            self.topic_model = None
    
    def search(self, query: str, max_results: int = 50):
        """执行搜索"""
        use_semantic = self.topic_model is not None
        return self.searcher.search(query, max_results, use_semantic)
    
    def start_indexing(self, paths=None):
        """开始索引"""
        if paths is None:
            paths = config.get_index_paths()
        
        if not paths:
            print("没有配置索引路径")
            return
        
        def progress_callback(current, total, message):
            if self.window:
                self.window.show_indexing_progress(current, total, message)
        
        def complete_callback(indexed, total):
            print(f"索引完成: {indexed}/{total}")
            
            # 重建主题模型
            if indexed > 10:
                print("重建主题模型...")
                self.topic_model = TopicModel(self.db)
                self.topic_model.load_or_create_model()
                self.searcher.topic_model = self.topic_model
            
            if self.window:
                self.window.update_status("索引完成")
        
        self.indexer.start_indexing(paths, progress_callback, complete_callback)
    
    def add_index_path(self, path: str):
        """添加索引路径"""
        config.add_index_path(path)
        
        # 立即开始索引这个路径
        self.start_indexing([path])
    
    def get_index_paths(self):
        """获取索引路径列表"""
        return config.get_index_paths()
    
    def get_stats(self):
        """获取统计信息"""
        return self.db.get_stats()
    
    def get_topic(self, topic_id: int):
        """获取主题信息"""
        return self.db.get_topic(topic_id)
    
    def rebuild_index(self):
        """重建索引"""
        # 清空数据库
        self.db.clear_all_data()
        
        # 重新索引
        self.start_indexing()
    
    def run(self):
        """运行应用"""
        # 首次运行检查
        if not config.get_index_paths():
            print("首次运行，请配置索引路径...")
            self._first_run_setup()
        
        # 创建并显示GUI
        self.window = MainWindow(self)
        
        # 检查是否需要索引
        if self.db.get_file_count() == 0:
            print("检测到空索引，开始首次索引...")
            self.start_indexing()
        
        # 启动GUI主循环
        self.window.mainloop()
    
    def _first_run_setup(self):
        """首次运行设置"""
        print("\n=== 欢迎使用 SomeThink ===")
        print("请选择要索引的文件夹")
        
        # 使用tkinter文件对话框
        import tkinter as tk
        from tkinter import filedialog
        
        root = tk.Tk()
        root.withdraw()
        
        path = filedialog.askdirectory(title="选择要索引的文件夹")
        
        if path:
            config.add_index_path(path)
            print(f"已添加索引路径: {path}")
        else:
            print("未选择路径，可以稍后在设置中添加")
        
        root.destroy()


def main():
    """主函数"""
    print("=== SomeThink 启动中 ===")
    print(f"配置目录: {config.config_dir}")
    print(f"数据库: {config.db_file}")
    
    # 创建应用实例
    app = SomeThinkApp()
    
    # 运行应用
    app.run()


if __name__ == "__main__":
    main()
