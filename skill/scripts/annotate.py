import argparse
import sys
import json
import pymupdf
import os
import unicodedata
import colorsys

from numpy.ma.extras import average

"""判断pdf是否存在并可以打开"""
def is_valid_pdf(path: str):
    try:
        doc = pymupdf.open(path)
        doc.close()
        return True
    except Exception:
        return False



"""字符归一化处理"""
def char_normalize(s):
    s = unicodedata.normalize('NFKC', s)
    s = s.lower()
    if s == "“" or s == "”":
        s = "\""
    if s == "‘" or s == "’":
        s = "'"
    if s == "・" or s == "·":
        s = "`"
    if s == "Ⅰ":
        s = "I"
    return s



"""比较两字符，不区分大小写、全半角、标点中英文"""
def char_equality(ch1, ch2):
    if char_normalize(ch1) == char_normalize(ch2):
        return True
    else:
        return False



"""异常大小字符比较"""
def size_compare(puple1, puple2):
    if puple1[3] - puple1[1] >= 2.5 * (puple2[3] - puple2[1]) or puple1[2] - puple1[0] >= 2.5 * (puple2[2] - puple2[0]):
        return 1
    elif puple2[3] - puple2[1] >= 2.5 * (puple1[3] - puple1[1]) or puple2[2] - puple2[0] >= 2.5 * (puple1[2] - puple1[0]):
        return -1
    else:
        return 0



"""页面字符信息提取"""
def word_information(
        doc,    # PDF路径
        start_page = 0,     # 起始页码
        end_page = -1,      # 结束页码
        header= 0.08,       # 页眉百分比
        footer= 0.92,       # 页脚百分比
):
    char_list = []  # 总字符串 ["text":字符, "page":页码, "line":行数, "box":包围盒]
    for page_id in range(start_page, end_page + 1):
        page = doc[page_id]

        """读取页面正文部分"""
        main_text = pymupdf.Rect(0, header * page.rect.height, page.rect.width, footer * page.rect.height)
        text_rawdict = page.get_text("rawdict", clip=main_text)

        line_id = 0
        for block in text_rawdict["blocks"]:
            if block["type"] != 0:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    for char in span["chars"]:
                        ch = char["c"]        # 字符
                        box = char["bbox"]    # 字符包围盒

                        if ch not in ("\n", " ", "\r"):
                            char_info = {"text": ch, "page": page_id, "line": line_id, "box": box}
                            char_list.append(char_info)

                line_id += 1

    return char_list



"""
关键词匹配，输出结构如下：
         |-- "keyword"
result ----- "frequency"
         |-- "quad_info_list"
                    |__ quad_info1 ----- "times"       |-- "page"
                    |__ quad_info2   |-- "quad"        |-- "line"
                    |__ ……                 |__ quad1 ----- "box" : (x0, y0, x1, y1)
                                           |__ quad2   |-- "word"
                                           |__ ……      |-- "times"
"""
def keyword_match(keyword: str, char_list: list):
    result = {"keyword": keyword, "frequency": 0, "quad_info_list": []}
    frequency = 0

    for no, char in enumerate(char_list):
        quad_info = {"times": frequency + 1, "quad": []}
        match = True

        for num, key in enumerate(keyword):
            if no + num >= len(char_list) or char_equality(char_list[no+num]["text"], key) != True:
                match = False
                break

            quad = {
                "page": char_list[no+num]["page"],
                "line": char_list[no+num]["line"],
                "box": char_list[no+num]["box"],
                "word": keyword,
                "times": frequency + 1,
            }
            quad_info["quad"].append(quad)

        if match:
            result["quad_info_list"].append(quad_info)
            frequency += 1
            result["frequency"] = frequency


    return result



"""标记区域确定"""
def quad_confirm(quadlist: list, type: int):    # highlight=1, underline=2, note=3
    return_list = []

    if type == 1 or type == 2:
        for quad_info in quadlist:
            quad0 = quad_info["quad"][0]
            page = quad0["page"]
            line = quad0["line"]
            box = quad0["box"]

            for quad in quad_info["quad"]:
                rect = {"page": page, "line": line, "box": box}

                """同关键词包围盒在同一行，合并加入列表，否则分开处理"""
                if quad["page"] == page and quad["line"] == line:
                    rect["box"] = (
                        min(quad["box"][0], rect["box"][0]),
                        min(quad["box"][1], rect["box"][1]),
                        max(quad["box"][2], rect["box"][2]),
                        max(quad["box"][3], rect["box"][3]),
                    )

                    box = rect["box"]


                else:
                    return_list.append(rect)
                    page = quad["page"]
                    line = quad["line"]
                    box = quad["box"]
                    rect = {"page": page, "line": line, "box": box}

                """如果遍历到最后一个quad，也加入列表"""
                if quad == quad_info["quad"][-1]:
                    return_list.append(rect)


    elif type == 3:
        # print(quad_list)
        for quad_info in quadlist:
            quad = quad_info["quad"][-1]
            page = quad["page"]
            line = quad["line"]
            box = quad["box"]
            rect = {"page": page, "line": line, "box": box}
            return_list.append(rect)
            #print(rect)

        #print(return_list)
    return return_list



"""色相环均匀分布颜色，保证区分"""
def color_assign(
        quantity: int,
        sat: float = 1.0,
        value: float = 1.0,
        start: float = 0.0
):
    if quantity <= 0:
        quantity = 1
    colors = []

    for i in range(quantity):
        hue = i / quantity + start
        hue = hue % 1.0

        """调节蓝紫色饱和度，防止过暗"""
        if 0.58 < hue < 0.83:
            r, g, b = colorsys.hsv_to_rgb(hue, 0.3, value)
        else:
            r, g, b = colorsys.hsv_to_rgb(hue, sat, value)

        colors.append((r, g, b))
    return colors



"""将输入拆分为多个任务，每个任务包括关键词、标注类型、标注颜色和文本、标注范围"""
def tasks_split(
        highlight_wordlist: list[str] = None,          # [word1, word2, …]
        underline_wordlist: list[str] = None,          # [word1, word2, …]
        note_wordlist: list[str] = None,               # [word1, word2, …]

        highlight_color_list: list[tuple] = None,    # [color1, color2, …], color = (r, g, b)
        underline_color_list: list[tuple] = None,    # [color1, color2, …], color = (r, g, b)
        note_text_list: list[str] = None,            # [text1, text2, …]

        start_page: int = 0,
        end_page: int = -1,
):

    """检查输入格式"""
    if not isinstance(start_page, int):
        raise TypeError("start_page must be int")

    if not isinstance(end_page, int):
        raise TypeError("end_page must be int")

    if highlight_wordlist is None:
        highlight_wordlist = []

    if underline_wordlist is None:
        underline_wordlist = []

    if note_wordlist is None:
        note_wordlist = []

    if not isinstance(highlight_wordlist, list):
        raise TypeError("highlight_wordlist must be a list")

    if not isinstance(underline_wordlist, list):
        raise TypeError("underline_wordlist must be a list")

    if not isinstance(note_wordlist, list):
        raise TypeError("note_wordlist must be a list")


    """未指定标注颜色、文本时自动分配颜色、文本"""
    highlight_quantity = len(highlight_wordlist)
    if highlight_color_list is None or len(highlight_color_list) == 0:
        highlight_color_list = color_assign(highlight_quantity, sat = 1.0, value = 1.0, start = 1/6)

    underline_quantity = len(underline_wordlist)
    if underline_color_list is None or len(underline_color_list) == 0:
        underline_color_list = color_assign(underline_quantity, sat = 1.0, value = 0.6, start = 0.0)

    if note_text_list is None or len(note_text_list) == 0:
        note_text_list = ["重点内容！"]

    if not isinstance(highlight_color_list, list):
        raise TypeError("highlight_color_list must be a list")

    if not isinstance(underline_color_list, list):
        raise TypeError("underline_color_list must be a list")

    if not isinstance(note_text_list, list):
        raise TypeError("note_text_list must be a list")


    """格式输出（关键词、标记类型、标记特点、标记范围）"""
    tasks_dict = {"highlight_tasks_list": [], "underline_tasks_list": [], "note_tasks_list": []}


    """highlight_tasks"""
    for no, highlight_word in enumerate(highlight_wordlist):
        if not isinstance(highlight_word, str):
            raise TypeError("highlight_word", no, "must be a string")

        keyword = highlight_word.replace(" ", "").replace("\n", "").replace("\r", "")
        highlight_color_id = no % len(highlight_color_list)
        highlight_color = highlight_color_list[highlight_color_id]

        if not isinstance(highlight_color, tuple):
            raise TypeError("highlight_color", highlight_color_id, "must be a tuple")

        if len(highlight_color) != 3:
            raise TypeError("length of highlight_color", highlight_color_id, "must be 3")

        for v in highlight_color:
            if not isinstance(v, (int, float)):
                raise TypeError("component of highlight_color", highlight_color_id, "must be int or float")

            if not (0 <= v <= 1):
                raise TypeError("component of highlight_color", highlight_color_id, "must be between 0 and 1")

        task = {"keyword": keyword, "color": highlight_color, "start_page": start_page, "end_page": end_page}
        tasks_dict["highlight_tasks_list"].append(task)


    """underline_tasks"""
    for no, underline_word in enumerate(underline_wordlist):
        if not isinstance(underline_word, str):
            raise TypeError("underline_word", no, "must be a string")

        keyword = underline_word
        underline_color_id = no % len(underline_color_list)
        underline_color = underline_color_list[underline_color_id]

        if not isinstance(underline_color, tuple):
            raise TypeError("underline_color", underline_color_id, "must be a tuple")

        if len(underline_color) != 3:
            raise TypeError("length of underline_color", underline_color_id, "must be 3")

        for v in underline_color:
            if not isinstance(v, (int, float)):
                raise TypeError("component of underline_color", underline_color_id, "must be int or float")

            if not (0 <= v <= 1):
                raise TypeError("component of underline_color", underline_color_id, "must between 0 and 1")

        task = {"keyword": keyword, "color": underline_color, "start_page": start_page, "end_page": end_page}
        tasks_dict["underline_tasks_list"].append(task)


    """note_tasks"""
    for no, note_word in enumerate(note_wordlist):
        if not isinstance(note_word, str):
            raise TypeError("note_word", no, "must be a string")

        keyword = note_word
        note_text_id = no % len(note_text_list)
        note_text = note_text_list[note_text_id]

        if not isinstance(note_text, str):
            raise TypeError("note_text", note_text_id, "must be a string")

        task = {"keyword": keyword, "text": note_text, "start_page": start_page, "end_page": end_page}
        tasks_dict["note_tasks_list"].append(task)


    return tasks_dict



"""输入拆分后的任务列表，按顺序添加标记，输出标记后的pdf"""
def text_annotate(
        doc,
        keyword: str,
        if_highlight = 0,
        if_underline = 0,
        if_note = 0,
        highlight_color=(1, 1, 0),
        underline_color=(1, 0, 0),
        note_text = "重点！",
        start_page = 0,
        end_page = -1,
        header = 0.08,
        footer = 0.92,
):

    """检查输入参数格式是否正确"""


    total_pages = len(doc)
    if start_page < 0 or start_page >= total_pages:
        raise ValueError(f"total pages: {total_pages}, start_page must be between 0 and {total_pages - 1}")

    if end_page < -1 or end_page >= total_pages:
        raise ValueError(f"total pages: {total_pages}, end_page must be between -1 and {total_pages - 1}")

    if end_page == -1:
        end_page = total_pages - 1

    if end_page < start_page:
        start_page, end_page = end_page, start_page

    if not isinstance(header, (int, float)):
        raise TypeError("header must be int or float")

    if not isinstance(footer, (int, float)):
        raise TypeError("footer must be int or float")

    if not (0 <= header <= 1):
        raise ValueError("header must be between 0 and 1")

    if not (0 <= footer <= 1):
        raise ValueError("footer must be between 0 and 1")

    if header >= footer:
        raise ValueError("header must be less than footer")


    char_list = word_information(
        doc = doc,
        start_page = start_page,
        end_page = end_page,
        header = header,
        footer = footer
    )

    keyword_list = keyword_match(keyword, char_list)
    print("关键词：", keyword, "指定范围内出现次数：", keyword_list["frequency"])
    quad_info_list = keyword_list["quad_info_list"]

    if if_highlight:
        quad_list = quad_confirm(quad_info_list, 1)
        for quad in quad_list:
            page_id = quad["page"]
            page = doc[page_id]

            x0, y0, x1, y1 = quad["box"]
            rect = pymupdf.Rect(x0, y0, x1, y1)
            highlighted = page.add_highlight_annot(rect)
            highlighted.set_colors(stroke=highlight_color)
            highlighted.update()

    if if_underline:
        quad_list = quad_confirm(quad_info_list, 2)
        for quad in quad_list:
            page_id = quad["page"]
            page = doc[page_id]

            x0, y0, x1, y1 = quad["box"]
            y_offset = 4
            y1 += y_offset
            rect = pymupdf.Rect(x0, y0, x1, y1)
            underlined = page.add_underline_annot(rect)
            underlined.set_colors(stroke=underline_color)
            underlined.update()

    if if_note:
        quad_list = quad_confirm(quad_info_list, 3)
        for quad in quad_list:
            page_id = quad["page"]
            page = doc[page_id]

            x0, y0, x1, y1 = quad["box"]
            rect = pymupdf.Rect(x0, y0, x1, y1)
            noted = page.add_text_annot(rect.br, note_text)
            noted.update()



def output_path_rename(output_path: str):
    base_name = output_path.replace(".pdf", "")
    count = 1

    while os.path.exists(output_path):
        #print("Warning:", output_path, "is already exist")
        output_path = f"{base_name}_{count}.pdf"
        count += 1

    return output_path


def color_input(color_taple: str):
    color_str = color_taple.strip().strip('()').strip('""')
    compose = [p.strip() for p in color_str.split(',')]
    if len(compose) != 3:
        raise ValueError(f"invalid input color: {color_taple}, which should have 3 numbers, like (1, 1, 0)")
    return (float(compose[0]), float(compose[1]), float(compose[2]))



def main():
    parser = argparse.ArgumentParser(description = "PDF标注，支持高亮、下划线、笔记")

    parser.add_argument("input_path", help="待处理PDF文件路径")
    parser.add_argument("--start_page", type=int, default=0, help="起始页，从0开始，默认为0")
    parser.add_argument("--end_page", type=int, default=-1, help="结束页，-1为最后一页，默认为-1")

    parser.add_argument("--header", type=float, default=0.08, help="页眉高度占比，0-1之间，默认为0.08")
    parser.add_argument("--footer", type=float, default=0.92, help="页脚高度占比，0-1之间，默认为0.92")

    parser.add_argument("--output_path", type = str, default = None, help = "标注PDF文件输出路径，默认为“源文件名_annotated.pdf”")

    """高亮输入格式"""
    parser.add_argument("--highlight_words", nargs = '*', default = [], help = "高亮关键词列表，空格分隔，如: --highlight_words 进行比较 切比雪夫")
    parser.add_argument("--highlight_colors", nargs = '*', default = [], help = "高亮颜色列表，(r,g,b)格式（取值为0-1），空格分隔，如: --highlight_colors (1,1,0) (0,1,1)")


    """下划线输入格式"""
    parser.add_argument("--underline_words", nargs = '*', default = [] , help = "下划线关键词列表，空格分隔，如: --underline_words 进行比较 切比雪夫")
    parser.add_argument("--underline_colors", nargs = '*', default = [] , help = "下划线颜色列表，r,g,b格式（取值为0-1），空格分隔，如: --underline_colors (1,1,0) (0,1,1)")

    """笔记输入格式"""
    parser.add_argument("--note_words", nargs = '*', default = [], help = "笔记关键词列表，空格分隔，如: --note_words 进行比较 切比雪夫")
    parser.add_argument("--note_texts", nargs = '*', default = [], help = "笔记文本列表，空格分隔，如: --note_text 重点内容！ 必考！")


    args = parser.parse_args()

    if not is_valid_pdf(args.input_path):
        error = f"{args.input_path} is not a valid PDF"
        print(json.dumps({"status": "error", "message": error}, ensure_ascii = False), file=sys.stderr)
        sys.exit(1)

    try:
        highlight_color_list = [color_input(c) for c in args.highlight_colors] if args.highlight_colors else []
        underline_color_list = [color_input(c) for c in args.underline_colors] if args.underline_colors else []
    except ValueError as e:
        print(json.dumps({"status": "error", "message": str(e)}, ensure_ascii = False), file = sys.stderr)
        sys.exit(1)


    try:
        tasks_direction = tasks_split(
            highlight_wordlist = args.highlight_words,
            highlight_color_list = highlight_color_list,

            underline_wordlist = args.underline_words,
            underline_color_list = underline_color_list,

            note_wordlist = args.note_words,
            note_text_list= args.note_texts if args.note_texts else None,

            start_page = args.start_page,
            end_page = args.end_page,
        )
    except Exception as e:
        print(json.dumps({"status": "error", "message": f"tasks_split failed: {e}"}, ensure_ascii = False), file = sys.stderr)
        sys.exit(1)


    doc = pymupdf.open(args.input_path)
    for highlight_task in tasks_direction["highlight_tasks_list"]:
        text_annotate(
            doc = doc,
            keyword = highlight_task["keyword"],

            if_highlight = 1,
            if_underline = 0,
            if_note = 0,

            highlight_color = highlight_task["color"],

            start_page = highlight_task["start_page"],
            end_page = highlight_task["end_page"],

            header = args.header,
            footer = args.footer,
        )

    for underline_task in tasks_direction["underline_tasks_list"]:
        text_annotate(
            doc = doc,
            keyword = underline_task["keyword"],

            if_highlight = 0,
            if_underline = 1,
            if_note = 0,

            highlight_color = underline_task["color"],

            start_page = underline_task["start_page"],
            end_page = underline_task["end_page"],

            header = args.header,
            footer = args.footer,
        )

    for note_task in tasks_direction["note_tasks_list"]:
        text_annotate(
            doc = doc,
            keyword = note_task["keyword"],

            if_highlight = 0,
            if_underline = 0,
            if_note = 1,

            note_text = note_task["text"],

            start_page = note_task["start_page"],
            end_page = note_task["end_page"],

            header = args.header,
            footer = args.footer,
        )

    output_path = args.output_path
    if not output_path:
        output_path = args.input_path.replace(".pdf", "_annotated.pdf")

    output_path = output_path_rename(output_path)

    doc.save(output_path)
    print("文件已保存：", output_path)
    doc.close()


if __name__ == "__main__":
    main()

