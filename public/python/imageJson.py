import re
import json
import os
import pytesseract
from PIL import Image

def extract_stock_info_from_single_image(image_path):
    """
    从单张图片提取股票信息（返回列表形式的结构化数据）
    :param image_path: 单张图片路径
    :return: 该图片的股票信息列表（[{name, turnover_rate, plate_type, sector}, ...]）
    """
    # 读取图片并OCR识别
    img = Image.open(image_path)
    ocr_text = pytesseract.image_to_string(img, lang='chi_sim+eng')
    lines = [line.strip() for line in ocr_text.split('\n') if line.strip()]

    # 正则表达式匹配（根据实际图片格式调整，这里适配之前的股票数据格式）
    pattern = re.compile(
        r'(?P<name>[\u4e00-\u9fa5]+)\s+'  # 股票名称（纯中文）
        r'(?P<turnover_rate>\d+\.\d+%)\s+'  # 换手率（如11.33%）
        r'(?P<plate_type>[\u4e00-\u9fa5/]+)\s+'  # 板型（如换手板、T字板）
        r'(?P<sector>[\u4e00-\u9fa5/]+)'  # 所属板块（如深地经济、国企改革）
    )

    # 解析单张图片的信息
    single_image_result = []
    for line in lines:
        match = pattern.match(line)
        if match:
            single_image_result.append(match.groupdict())
    return single_image_result

def batch_process_images(image_dir):
    """
    批量处理指定目录下的所有图片，整合信息并生成JSON
    :param image_dir: 图片所在目录路径
    :return: 整合去重后的JSON字符串
    """
    # 1. 获取目录下所有图片文件（可根据需要扩展支持的图片格式）
    image_formats = ('.jpg', '.jpeg', '.png', '.bmp')
    image_paths = [
        os.path.join(image_dir, filename)
        for filename in os.listdir(image_dir)
        if filename.lower().endswith(image_formats)
    ]

    if not image_paths:
        raise ValueError("指定目录下未找到图片文件")

    # 2. 循环处理每张图片，汇总所有信息
    all_stocks = []
    for path in image_paths:
        try:
            stock_info = extract_stock_info_from_single_image(path)
            all_stocks.extend(stock_info)  # 追加到总列表
        except Exception as e:
            print(f"处理图片 {path} 失败：{str(e)}，跳过该图片")

    # 3. 去重（根据股票名称去重，保留首次出现的记录）
    unique_stocks = []
    seen_names = set()
    for stock in all_stocks:
        if stock['name'] not in seen_names:
            seen_names.add(stock['name'])
            unique_stocks.append(stock)

    # 4. 转换为JSON
    return json.dumps(unique_stocks, ensure_ascii=False, indent=2)

# 示例用法
if __name__ == "__main__":
    # 替换为你的图片所在目录（如果是单张图片，可直接指定路径调用单图函数）
    image_directory = "../imageSource/"  # 对应你之前上传图片的存储目录
    try:
        # 批量处理并生成JSON
        final_json = batch_process_images(image_directory)
        print("整合后的JSON结果：")
        print(final_json)

        # 保存到本地文件
        with open("batch_stock_result.json", "w", encoding="utf-8") as f:
            f.write(final_json)
        print("\n结果已保存到 batch_stock_result.json 文件")
    except Exception as e:
        print(f"批量处理失败：{str(e)}")