# PDF-annotation
基于 [PyMuPDF](https://github.com/pymupdf/PyMuPDF) 开发的 PDF 处理技能，包含**关键词标注**（高亮/下划线/笔记）和**正文文本提取**功能。可作为独立 CLI 工具使用，也可作为 Skill 集成到 AI Agent 系统中。

## 功能特性

### 关键词标注 (`skill/scripts/annotate.py`)
- **三种标注模式**：高亮（Highlight）、下划线（Underline）、文本笔记（Text Note）
- **批量处理**：支持同时指定多个关键词，一次性完成多种标注
- **范围控制**：可指定起止页码，灵活处理长文档；配置正文区域百分比，排除页眉页脚干扰
- **自动配色**：未指定标注颜色时，基于 HSV 色相环均匀分布算法自动分配标注颜色，多关键词区分度高
- **智能关键词匹配**：支持全半角、大小写、中英文标点归一化比较，避免漏匹配

### 正文文本提取 (`skill/scripts/maintext.py`)
- **文本提取**：裁剪页眉页脚，仅输出正文文本
- **字符级解析**：基于 PyMuPDF 的 `rawdict` 接口逐字符提取，保留原始排版结构
- **CLI 输出**：直接打印到终端，方便管道处理或重定向保存

## 系统架构

```
用户自然语言 → 智能体 → Skill → Python Script/CLI → 开源项目 → 结果
```

## 环境要求

- Python 3.10 ~ 3.14
- 操作系统：Windows / macOS / Linux

## 安装

### 1. 创建虚拟环境：
```bash
python -m venv .venv
# 或使用conda
conda create -n pdf_annotate python=3.14
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

## 运行方法

### 命令行直接标注
```bash
python scripts/annotate.py input.pdf --highlight_words "关键词1" "关键词2" --underline_words "关键词3" --underline_colors "1,0,0" --note_words "关键词4" --header 0.08 --footer 0.92
```

### 通过 Nanobot 自然语言调用
```bash
nanobot agent -m "帮我对input.pdf里第3页所有“进行比较”做高亮处理，并做笔记。"
```

## 参数说明
### `skill/scripts/annotate.py`

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `input_path` | 待处理 PDF 文件路径（必填） | - |
| `--start_page` | 起始页码（从0开始） | 0 |
| `--end_page` | 结束页码（-1为最后一页） | -1 |
| `--header` | 页眉高度占比（0-1） | 0.08 |
| `--footer` | 页脚高度占比（0-1） | 0.92 |
| `--output_path` | 输出文件路径 | 原文件名_annotated.pdf |
| `--highlight_words` | 高亮关键词列表（空格分隔） | - |
| `--highlight_colors` | 高亮颜色列表，RGB格式 | 自动分配 |
| `--underline_words` | 下划线关键词列表 | - |
| `--underline_colors` | 下划线颜色列表，RGB格式 | 自动分配 |
| `--note_words` | 笔记关键词列表 | - |
| `--note_texts` | 笔记文本列表 | "重点内容！" |

### `skill/scripts/maintext.py`

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `input_path` | 待处理 PDF 文件路径（必填） | - |
| `--start_page` | 起始页码 | 0 |
| `--end_page` | 结束页码（-1为最后一页） | -1 |
| `--header` | 页眉高度占比 | 0.08 |
| `--footer` | 页脚高度占比 | 0.92 |

## 许可证

与上游依赖 PyMuPDF 的许可证保持一致。
