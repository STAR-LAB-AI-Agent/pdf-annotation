---
name: pdf_annotate
description: PDF关键词标注技能，支持高亮、下划线、文本便签注释。支持字符归一化匹配（中英文标点、罗马数字Ⅰ/I、全半角、大小写），自动过滤页眉页脚区域。可批量搜索多个关键词，追加标注到PDF。
metadata:
  nanobot:
    always: true
requires:
  bins: ["python"]
inputs:
  - name: input_path
    type: string
    description: "待处理PDF文件路径"
    required: true
  - name: highlight_words
    type: array
    items:
      type: string
    description: "高亮关键词列表，如 ['切比雪夫', '滤波器']"
    required: false
  - name: highlight_colors
    type: array
    items:
      type: string
    description: "高亮颜色列表，r,g,b格式，如 ['1,1,0', '0,1,1']，按顺序使用列表中颜色，不传则自动分配"
    required: false
  - name: underline_words
    type: array
    items:
      type: string
    description: "下划线关键词列表"
    required: false
  - name: underline_colors
    type: array
    items:
      type: string
    description: "下划线颜色列表，r,g,b格式，按顺序使用列表中颜色，不传则自动分配"
    required: false
  - name: note_words
    type: array
    items:
      type: string
    description: "笔记关键词列表"
    required: false
  - name: note_texts
    type: array
    items:
      type: string
    description: "笔记文本列表，按顺序标注文本内容"
    required: false
  - name: start_page
    type: integer
    description: "起始页码，从0开始，默认0"
    default: 0
  - name: end_page
    type: integer
    description: "结束页码，-1代表最后一页，默认-1"
    default: -1
  - name: header
    type: number
    description: "页眉占页面高度比例，默认0.08"
    default: 0.08
  - name: footer
    type: number
    description: "页脚占页面高度比例，默认0.92"
    default: 0.92
  - name: output_path
    type: string
    description: "输出PDF路径，默认'<原名>_annotated.pdf'"
    required: false
outputs:
  - name: result_file
    type: string
    description: "标注完成的PDF文件路径"
---

# PDF智能标注技能
本技能包含两个脚本：`scripts/annotate.py`（标注执行）和 `scripts/maintext.py`（正文提取），部署在项目根目录下。

## 调用方式
当用户提供明确关键词时，直接调用 `scripts/annotate.py`。

| 技能输入 | 命令行参数 | 说明                                                   |
|----------|-----------|------------------------------------------------------|
| `input_path` | 位置参数 | PDF文件路径                                              |
| `highlight_words` | `--highlight_words` | 高亮关键词列表，展开为多个独立参数，如 `"关键词" "重点"`                     |
| `highlight_colors` | `--highlight_colors` | 高亮颜色列表，循环使用表内颜色，展开为多个独立参数，格式 `"(1,1,0)"` 或 `"1,1,0"` |
| `underline_words` | `--underline_words` | 下划线关键词列表，展开为多个独立参数，如 `"关键词" "重点"`                    |
| `underline_colors` | `--underline_colors` | 下划线颜色列表，循环使用表内颜色，展开为多个独立参数，格式 `"(1,1,0)"`            |
| `note_words` | `--note_words` | 笔记关键词列表，展开为多个独立参数，如 `"关键词" "重点"`                     |
| `note_texts` | `--note_texts` | 每处笔记内容，展开为多个独立参数，如 `"关键词" "重点"`                      |
| `start_page` | `--start_page` | 整数                                                   |
| `end_page` | `--end_page` | 整数                                                   |
| `header` | `--header` | 浮点数                                                  |
| `footer` | `--footer` | 浮点数                                                  |
| `output_path` | `--output_path` | 字符串                                                  |

示例：
python scripts\annotate.py "test.pdf" --highlight-words "关键词1" "关键词2" --highlight-colors "1,1,0" "1,0,0" "0,1,0" --underline-words "关键词3" "关键词4" --header 0.08 --footer 0.92

当用户未提供明确关键词时，先调用 `scripts/maintext.py` 提取文本，AI分析后提取关键词，再调用 `scripts/annotate.py`。
参数说明：

| 参数 | 必选 | 说明 | 默认值 |
|------|------|------|---|
| `input_pdf` | 是 | PDF文件路径（位置参数） | - |
| `--start_page` | 否 | 起始页码 | 0 |
| `--end_page` | 否 | 结束页码，-1为最后一页 | -1 |
| `--header` | 否 | 页眉裁剪比例 0~1 | 0.08 |
| `--footer` | 否 | 页脚裁剪比例 0~1 | 0.92 |

示例：
python scripts\maintext.py "test.pdf" --header 0.1 --footer 0.9
## 决策逻辑

1. 用户有明确关键词 → 直接标注
2. 用户无明确关键词 → maintext.py提取 → AI判断 → 标注
3. 混合模式 → 已知关键词+AI补充 → 合并标注

## 使用规则
1. 文件路径必须使用**Windows绝对路径**，例如`C:\Users\Lenovo\Desktop\test.pdf`；
2.便签为PDF标准弹出注释，在Edge/Adobe阅读器鼠标悬浮才显示文字，不会直接打印在页面；
3. 用户要求PDF标注时，调用此脚本。脚本不能解决问题时告知用户，不要自行解决。
4. 脚本单次运行只能对所有关键词进行同一标注，当用户要求对关键词进行不同类型标注时，按每种标注类型分次调用脚本
5. 参数缺失时询问用户，禁止采用除脚本外其他方案。
6. 脚本执行完成后，返回新PDF保存路径和标注数量。
7. 执行失败时告知用户结果