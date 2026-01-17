"""
主窗口 - SomeThink极简搜索界面
"""

import customtkinter as ctk
from typing import List, Tuple, Dict
import threading
import os
import subprocess
import platform


class MainWindow(ctk.CTk):
    """主窗口类"""
    
    def __init__(self, app_controller):
        super().__init__()
        
        self.controller = app_controller
        
        # 窗口配置
        self.title("SomeThink")
        self.geometry("800x600")
        
        # 设置主题
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # 搜索防抖定时器
        self.search_timer = None
        
        # 创建界面
        self._create_widgets()
        
        # 绑定事件
        self._bind_events()
    
    def _create_widgets(self):
        """创建界面组件"""
        # 主容器
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True, padx=40, pady=40)
        
        # 标题
        self.title_label = ctk.CTkLabel(
            self.main_frame,
            text="SomeThink",
            font=ctk.CTkFont(size=32, weight="bold")
        )
        self.title_label.pack(pady=(0, 40))
        
        # 搜索框容器
        self.search_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.search_frame.pack(fill="x", pady=(0, 30))
        
        # 搜索输入框
        self.search_entry = ctk.CTkEntry(
            self.search_frame,
            placeholder_text="🔍 输入关键词搜索...",
            font=ctk.CTkFont(size=16),
            height=50,
            border_width=2
        )
        self.search_entry.pack(fill="x")
        
        # 结果区域容器
        self.results_container = ctk.CTkFrame(self.main_frame)
        self.results_container.pack(fill="both", expand=True)
        
        # 滚动区域
        self.results_scroll = ctk.CTkScrollableFrame(
            self.results_container,
            fg_color="transparent"
        )
        self.results_scroll.pack(fill="both", expand=True)
        
        # 底部状态栏
        self.status_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent", height=30)
        self.status_frame.pack(fill="x", pady=(10, 0))
        
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="就绪",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.status_label.pack(side="left")
        
        # 设置按钮
        self.settings_button = ctk.CTkButton(
            self.status_frame,
            text="⚙️ 设置",
            width=80,
            height=28,
            font=ctk.CTkFont(size=12),
            command=self._show_settings
        )
        self.settings_button.pack(side="right")
    
    def _bind_events(self):
        """绑定事件"""
        # 搜索框输入事件（防抖）
        self.search_entry.bind("<KeyRelease>", self._on_search_changed)
        
        # 回车键打开选中文件
        self.search_entry.bind("<Return>", self._on_enter_pressed)
    
    def _on_search_changed(self, event):
        """搜索框内容变化"""
        # 取消之前的定时器
        if self.search_timer:
            self.after_cancel(self.search_timer)
        
        # 设置新的定时器（300ms防抖）
        self.search_timer = self.after(300, self._perform_search)
    
    def _perform_search(self):
        """执行搜索"""
        query = self.search_entry.get().strip()
        
        if not query:
            self._clear_results()
            self.update_status("就绪")
            return
        
        self.update_status(f"正在搜索: {query}...")
        
        # 在新线程中执行搜索
        threading.Thread(
            target=self._search_worker,
            args=(query,),
            daemon=True
        ).start()
    
    def _search_worker(self, query: str):
        """搜索工作线程"""
        try:
            results = self.controller.search(query)
            
            # 在主线程更新UI
            self.after(0, lambda: self._display_results(results, query))
        
        except Exception as e:
            self.after(0, lambda: self.update_status(f"搜索出错: {e}"))
    
    def _display_results(self, results: List[Tuple[Dict, float]], query: str):
        """显示搜索结果"""
        # 清空之前的结果
        self._clear_results()
        
        if not results:
            self._show_no_results(query)
            return
        
        # 显示结果
        for file_info, score in results:
            self._create_result_item(file_info, score)
        
        self.update_status(f"找到 {len(results)} 个结果")
    
    def _create_result_item(self, file_info: Dict, score: float):
        """创建单个结果项"""
        # 结果项容器
        item_frame = ctk.CTkFrame(
            self.results_scroll,
            fg_color=("gray90", "gray20"),
            corner_radius=10
        )
        item_frame.pack(fill="x", pady=5, padx=5)
        
        # 内容容器
        content_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        content_frame.pack(fill="x", padx=15, pady=12)
        
        # 文件图标和名称
        icon = self._get_file_icon(file_info['file_type'])
        filename = file_info['filename']
        
        name_label = ctk.CTkLabel(
            content_frame,
            text=f"{icon} {filename}",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        name_label.pack(anchor="w")
        
        # 主题和相关度
        topic_text = "未分类"
        if file_info.get('topic_id'):
            topic = self.controller.get_topic(file_info['topic_id'])
            if topic:
                topic_text = topic.get('name', f"主题 {file_info['topic_id']}")
        
        info_text = f"主题: {topic_text} | 相关度: {int(score * 100)}%"
        
        info_label = ctk.CTkLabel(
            content_frame,
            text=info_text,
            font=ctk.CTkFont(size=11),
            text_color="gray",
            anchor="w"
        )
        info_label.pack(anchor="w", pady=(5, 0))
        
        # 文件路径
        path_label = ctk.CTkLabel(
            content_frame,
            text=file_info['path'],
            font=ctk.CTkFont(size=10),
            text_color="gray60",
            anchor="w"
        )
        path_label.pack(anchor="w", pady=(2, 0))
        
        # 绑定点击事件
        for widget in [item_frame, content_frame, name_label, info_label, path_label]:
            widget.bind("<Button-1>", lambda e, path=file_info['path']: self._open_file(path))
            widget.bind("<Enter>", lambda e, f=item_frame: f.configure(fg_color=("gray85", "gray25")))
            widget.bind("<Leave>", lambda e, f=item_frame: f.configure(fg_color=("gray90", "gray20")))
    
    def _get_file_icon(self, file_type: str) -> str:
        """获取文件类型图标"""
        icons = {
            'document': '📄',
            'image': '🖼️',
            'audio': '🎵',
            'video': '🎬',
            'unknown': '📎'
        }
        return icons.get(file_type, '📎')
    
    def _open_file(self, file_path: str):
        """打开文件"""
        try:
            system = platform.system()
            
            if system == "Darwin":  # macOS
                subprocess.run(["open", file_path])
            elif system == "Windows":
                os.startfile(file_path)
            else:  # Linux
                subprocess.run(["xdg-open", file_path])
            
            self.update_status(f"已打开: {os.path.basename(file_path)}")
        
        except Exception as e:
            self.update_status(f"打开文件失败: {e}")
    
    def _show_no_results(self, query: str):
        """显示无结果提示"""
        no_result_label = ctk.CTkLabel(
            self.results_scroll,
            text=f"未找到与 \"{query}\" 相关的结果",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        no_result_label.pack(pady=50)
        
        self.update_status("未找到结果")
    
    def _clear_results(self):
        """清空结果区域"""
        for widget in self.results_scroll.winfo_children():
            widget.destroy()
    
    def _on_enter_pressed(self, event):
        """回车键按下"""
        # 如果有结果，打开第一个
        children = self.results_scroll.winfo_children()
        if children:
            # 模拟点击第一个结果
            pass
    
    def _show_settings(self):
        """显示设置窗口"""
        settings_window = SettingsWindow(self, self.controller)
        settings_window.grab_set()  # 模态窗口
    
    def update_status(self, message: str):
        """更新状态栏"""
        self.status_label.configure(text=message)
    
    def show_indexing_progress(self, current: int, total: int, message: str):
        """显示索引进度"""
        progress_text = f"索引中: {current}/{total} - {message}"
        self.update_status(progress_text)


class SettingsWindow(ctk.CTkToplevel):
    """设置窗口"""
    
    def __init__(self, parent, controller):
        super().__init__(parent)
        
        self.controller = controller
        
        self.title("设置")
        self.geometry("600x400")
        
        self._create_widgets()
    
    def _create_widgets(self):
        """创建设置界面"""
        # 主容器
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 标题
        title_label = ctk.CTkLabel(
            main_frame,
            text="设置",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=(0, 20))
        
        # 索引路径
        path_frame = ctk.CTkFrame(main_frame)
        path_frame.pack(fill="x", pady=10)
        
        path_label = ctk.CTkLabel(
            path_frame,
            text="索引路径:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        path_label.pack(anchor="w", padx=10, pady=5)
        
        # 路径列表
        self.path_list = ctk.CTkTextbox(path_frame, height=100)
        self.path_list.pack(fill="x", padx=10, pady=5)
        
        # 加载当前路径
        paths = self.controller.get_index_paths()
        self.path_list.insert("1.0", "\n".join(paths))
        
        # 添加路径按钮
        add_button = ctk.CTkButton(
            path_frame,
            text="添加路径",
            command=self._add_path
        )
        add_button.pack(pady=5)
        
        # 重建索引按钮
        rebuild_frame = ctk.CTkFrame(main_frame)
        rebuild_frame.pack(fill="x", pady=10)
        
        rebuild_label = ctk.CTkLabel(
            rebuild_frame,
            text="索引管理:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        rebuild_label.pack(anchor="w", padx=10, pady=5)
        
        rebuild_button = ctk.CTkButton(
            rebuild_frame,
            text="重建索引和主题模型",
            command=self._rebuild_index
        )
        rebuild_button.pack(padx=10, pady=5)
        
        # 统计信息
        stats_frame = ctk.CTkFrame(main_frame)
        stats_frame.pack(fill="x", pady=10)
        
        stats_label = ctk.CTkLabel(
            stats_frame,
            text="统计信息:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        stats_label.pack(anchor="w", padx=10, pady=5)
        
        stats = self.controller.get_stats()
        stats_text = f"文件总数: {stats['total_files']}\n"
        stats_text += f"主题数: {stats['total_topics']}\n"
        stats_text += f"已分类: {stats['classified_files']}"
        
        self.stats_display = ctk.CTkLabel(
            stats_frame,
            text=stats_text,
            font=ctk.CTkFont(size=12),
            anchor="w"
        )
        self.stats_display.pack(anchor="w", padx=20, pady=5)
    
    def _add_path(self):
        """添加索引路径"""
        from tkinter import filedialog
        
        path = filedialog.askdirectory(title="选择要索引的文件夹")
        
        if path:
            current_text = self.path_list.get("1.0", "end").strip()
            if current_text:
                self.path_list.insert("end", "\n" + path)
            else:
                self.path_list.insert("1.0", path)
            
            self.controller.add_index_path(path)
    
    def _rebuild_index(self):
        """重建索引"""
        # 确认对话框
        dialog = ctk.CTkInputDialog(
            text="确定要重建索引吗？这将删除现有数据并重新扫描所有文件。\n输入 'yes' 确认:",
            title="确认重建"
        )
        
        response = dialog.get_input()
        
        if response and response.lower() == 'yes':
            self.controller.rebuild_index()
            self.update_status("正在重建索引...")
            self.destroy()


if __name__ == "__main__":
    # 测试界面
    app = MainWindow(None)
    app.mainloop()
