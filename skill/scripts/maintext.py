import pymupdf
import argparse
import json
import sys

from six import ensure_str


def is_valid_pdf(path: str):
    try:
        doc = pymupdf.open(path)
        doc.close()
        return True
    except Exception:
        return False


def get_maintext(doc,
                 start_page = 0,
                 end_page = -1,
                 header = 0.08,
                 footer = 0.92,
):
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

    main_text = []
    for page_id in range(start_page, end_page + 1):
        page_text = {"page": page_id, "text":[]}
        page = doc[page_id]
        text = []

        rect = pymupdf.Rect(0, header * page.rect.height, page.rect.width, footer * page.rect.height)
        text_rawdict = page.get_text("rawdict", clip=rect)

        for block in text_rawdict["blocks"]:
            if block["type"] != 0:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    for char in span["chars"]:
                        ch = char["c"]        # 字符
                        if ch not in ("\n", "\r"):
                            text.append(ch)
                text.append("\n")

        page_text["text"] = "".join(text)
        main_text.append(page_text)

    return main_text

def main():
    parser = argparse.ArgumentParser(description = "PDF正文提取")

    parser.add_argument("input_path", help = "待处理PDF文件路径")
    parser.add_argument("--start_page", type = int, default = 0, help = "起始页，从0开始，默认为0")
    parser.add_argument("--end_page", type = int, default = -1, help = "结束页，-1为最后一页，默认为-1")

    parser.add_argument("--header", type = float, default = 0.08, help = "页眉高度占比，0-1之间，默认为0.08")
    parser.add_argument("--footer", type = float, default = 0.92, help = "页脚高度占比，0-1之间，默认为0.92")


    args = parser.parse_args()
    if not is_valid_pdf(args.input_path):
        error = f"{args.input_path} is not a valid PDF"
        print(json.dumps({"status": "error", "message": error}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)

    doc = None
    try:
        doc = pymupdf.open(args.input_path)
        main_text = get_maintext(
            doc,
            start_page = args.start_page,
            end_page = args.end_page,
            header = args.header,
            footer = args.footer
        )

    except Exception as e:
        error = {"status": "error", "message": str(e)}
        print(json.dumps(error, ensure_ascii=False), file=sys.stderr)
        if doc:
            doc.close()
        sys.exit(1)

    finally:
        if doc:
            doc.close()


    for page_text in main_text:
        print(f"———— 第{page_text["page"]}页：")
        print(page_text["text"])

    print("———— 输出结束")


if __name__ == "__main__":
    main()