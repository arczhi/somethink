# SomeThink - 智能本地文件搜索工具

<div align="center">

**基于主题模型的增强搜索引擎**

![alt text](image.png)

你是否经常忘记自己的文件放在哪些地方？记得一些关键词，但不记得文件名称？

不如来试试 SomeThink

支持 macOS · Windows · Linux

</div>

## ✨ 特性

- 🎯 **智能主题匹配**: 使用 BERTopic 进行语义理解，而不仅仅是关键词匹配
- 🚀 **极速搜索**: 本地索引 + 智能缓存，毫秒级响应
- 🎨 **极简界面**: 专注搜索体验，无干扰设计
- 📁 **多格式支持**: 文档、图片、音乐、视频全覆盖
- 💡 **性能自适应**: 根据设备性能自动选择合适的模型
- 🔄 **实时监控**: 自动检测文件变化，保持索引更新

## 📦 安装

### 从源码运行

```bash
# 克隆仓库
git clone https://github.com/arczhi/somethink.git
cd somethink

# 安装依赖
pip install -r requirements.txt

# 运行应用
python main.py
```

### 下载预编译版本

前往 [Releases](https://github.com/yourusername/somethink/releases) 下载适合您系统的版本。

## 🚀 快速开始

1. **首次运行**: 启动后会自动检测系统配置并下载适合的模型
2. **选择索引目录**: 选择您想要搜索的文件夹
3. **等待索引**: 首次索引可能需要几分钟，之后会自动增量更新
4. **开始搜索**: 输入关键词，即时获得智能匹配结果

## 🛠️ 技术栈

- **GUI**: CustomTkinter - 现代化的 Tkinter 界面
- **主题建模**: BERTopic - 主题提取与分类
- **文本嵌入**: Sentence-Transformers - 轻量级语义向量化
- **数据库**: SQLite - 本地索引存储
- **文件监控**: Watchdog - 实时文件变化检测

## 📖 使用说明

### 支持的文件类型

| 类型 | 格式 |
|------|------|
| 📄 文档 | txt, md, pdf, docx, pptx |
| 🖼️ 图片 | jpg, png, gif, bmp, svg |
| 🎵 音频 | mp3, flac, wav, m4a |
| 🎬 视频 | mp4, avi, mkv, mov |

### 搜索技巧

- **关键词搜索**: 直接输入文件名或内容关键词
- **主题搜索**: 输入抽象概念，如 "机器学习"、"旅行照片"
- **组合搜索**: 多个关键词空格分隔

### 快捷键

- `Enter` - 打开选中文件
- `Cmd/Ctrl + O` - 在文件管理器中显示
- `Cmd/Ctrl + ,` - 打开设置
- `Esc` - 清空搜索

## ⚙️ 配置

配置文件位于: `~/.somethink/config.json`

```json
{
  "model_name": "all-MiniLM-L6-v2",
  "index_paths": ["/Users/username/Documents"],
  "exclude_paths": [".git", "node_modules"],
  "max_results": 50,
  "auto_index": true
}
```

## 🔧 开发

### 项目结构

```
somethink/
├── gui/              # 界面层
│   ├── main_window.py
│   └── components/
├── engine/           # 搜索引擎
│   ├── indexer.py
│   ├── searcher.py
│   └── matcher.py
├── models/           # 模型层
│   ├── topic_model.py
│   └── embeddings.py
├── utils/            # 工具模块
│   ├── file_scanner.py
│   └── config.py
├── data/             # 数据层
│   └── database.py
└── main.py           # 入口文件
```

### 运行测试

```bash
pytest tests/
```

### 构建可执行文件

```bash
# macOS/Linux
pyinstaller --onefile --windowed --icon=assets/icon.icns main.py

# Windows
pyinstaller --onefile --windowed --icon=assets/icon.ico main.py
```

## 🤝 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [BERTopic](https://github.com/MaartenGr/BERTopic) - 主题建模
- [Sentence-Transformers](https://github.com/UKPLab/sentence-transformers) - 文本嵌入
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) - 现代化 UI

## 📮 联系

有问题或建议？欢迎提交 [Issue](https://github.com/yourusername/somethink/issues)

---

<div align="center">
Made with ❤️ by SomeThink Team
</div>
