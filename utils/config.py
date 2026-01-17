"""
配置管理模块
负责加载、保存和管理应用配置
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any
import platform


class Config:
    """配置管理类"""
    
    DEFAULT_CONFIG = {
        "model_name": "all-MiniLM-L6-v2",
        "index_paths": [],
        "exclude_patterns": [".git", "node_modules", "__pycache__", ".DS_Store"],
        "max_results": 50,
        "auto_index": True,
        "search_debounce_ms": 300,
        "theme": "dark",
        "language": "auto",
    }
    
    def __init__(self):
        self.settings = {}  # 先初始化settings属性
        self.config_dir = self._get_config_dir()
        self.config_file = self.config_dir / "config.json"
        self.db_file = self.config_dir / "somethink.db"
        self.models_dir = self.config_dir / "models"
        
        self._ensure_dirs()
        self.settings = self._load_config()
        
    def _get_config_dir(self) -> Path:
        """获取配置目录路径"""
        system = platform.system()
        
        if system == "Darwin":  # macOS
            base = Path.home() / "Library" / "Application Support"
        elif system == "Windows":
            base = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
        else:  # Linux
            base = Path.home() / ".config"
            
        return base / "SomeThink"
    
    def _ensure_dirs(self):
        """确保配置目录存在"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 合并默认配置（用于新增配置项）
                    return {**self.DEFAULT_CONFIG, **config}
            except Exception as e:
                print(f"加载配置失败: {e}，使用默认配置")
                return self.DEFAULT_CONFIG.copy()
        else:
            # 首次运行，创建默认配置
            self.save()
            return self.DEFAULT_CONFIG.copy()
    
    def save(self):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存配置失败: {e}")
    
    def get(self, key: str, default=None) -> Any:
        """获取配置项"""
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any):
        """设置配置项"""
        self.settings[key] = value
        self.save()
    
    def add_index_path(self, path: str):
        """添加索引路径"""
        paths = self.settings.get("index_paths", [])
        if path not in paths:
            paths.append(path)
            self.set("index_paths", paths)
    
    def remove_index_path(self, path: str):
        """移除索引路径"""
        paths = self.settings.get("index_paths", [])
        if path in paths:
            paths.remove(path)
            self.set("index_paths", paths)
    
    def get_index_paths(self) -> List[str]:
        """获取所有索引路径"""
        return self.settings.get("index_paths", [])
    
    def should_exclude(self, path: str) -> bool:
        """判断路径是否应该被排除"""
        exclude_patterns = self.settings.get("exclude_patterns", [])
        path_obj = Path(path)
        
        for pattern in exclude_patterns:
            if pattern in path_obj.parts:
                return True
        
        return False
    
    def get_model_name(self) -> str:
        """获取模型名称"""
        return self.settings.get("model_name", "all-MiniLM-L6-v2")
    
    def detect_and_set_optimal_model(self):
        """根据系统性能自动选择最优模型"""
        import psutil
        
        # 获取系统内存（GB）
        total_memory = psutil.virtual_memory().total / (1024 ** 3)
        
        if total_memory < 4:
            model_name = "paraphrase-MiniLM-L3-v2"  # 轻量级
        elif total_memory < 8:
            model_name = "all-MiniLM-L6-v2"  # 标准
        else:
            model_name = "all-MiniLM-L6-v2"  # 标准（可升级到更大模型）
        
        self.set("model_name", model_name)
        return model_name


# 全局配置实例
config = Config()
