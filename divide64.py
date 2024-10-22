import os
import re

def split_gua_file(input_file):
    # 创建文件夹来保存每个卦的单独文件
    output_folder = "iching/guaci"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 打开原始文件
    with open(input_file, 'r', encoding='utf-8') as file:
        content = file.read()

    # 根据“---- Page”来分割文件，假设每个页面对应一个卦
    pages = content.split('---- Page')

    # 定义正则表达式来匹配“周易第X卦_卦名”的结构
    gua_pattern = re.compile(r"周易第(\d+)卦_(.*?)_")

    # 遍历每一页内容
    for page in pages[1:]:  # 第一项是空的，因为我们用Page分割
        lines = page.split('\n')

        # 获取卦的标题
        title = None
        for line in lines:
            match = gua_pattern.search(line)
            if match:
                gua_number = match.group(1)  # 获取卦的数字
                gua_name = match.group(2).replace(" ", "")  # 获取卦名，去除空格
                title = f"第{gua_number}卦_{gua_name}"
                break

        if title:
            output_file = os.path.join(output_folder, f"{title}.txt")

            # 写入该卦的内容到单独的文件
            with open(output_file, 'w', encoding='utf-8') as out_file:
                out_file.write('\n'.join(lines))

            print(f"已创建文件: {output_file}")

# 输入txt文件的路径
input_file_path = 'yijing_full_content.txt'
split_gua_file(input_file_path)
