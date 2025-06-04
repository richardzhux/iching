import re

def organize_text(file_path, output_path, gua_number):
    # Define the main headers and sub-headers
    main_headers = ["gaoci", "xiangci", "duanyi", "zhaoyong", "fupeirong", "zongjie", "philos"]
    sub_headers = ["yaoci", "zhaoyong", "fupeirong", "var", "philos"]
    
    # Initialize content dictionary for organization
    organized_content = {header: "" for header in main_headers}
    sub_content = {i: {header: "" for header in sub_headers} for i in range(1, 7)}

    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    current_main_header = None
    current_sub_header = None
    current_line_number = None

    for line in lines:
        # Match main headers
        main_header_match = re.match(r"(蒙\.亨|象曰：|《断易天机》解|时运：|传统解卦|哲学含义)", line)
        if main_header_match:
            if "蒙" in line:
                current_main_header = "gaoci"
            elif "象曰" in line:
                current_main_header = "xiangci"
            elif "《断易天机》解" in line:
                current_main_header = "duanyi"
            elif "时运：" in line:
                current_main_header = "fupeirong"
            elif "传统解卦" in line:
                current_main_header = "zongjie"
            elif "哲学含义" in line:
                current_main_header = "philos"
            if current_main_header:
                organized_content[current_main_header] += line.strip() + "\n"
            continue
        
        # Match sub-header with line numbers (e.g., 初六, 九二)
        sub_header_match = re.match(r"(初六|九二|六三|六四|六五|上九)", line)
        if sub_header_match:
            sub_line_text = sub_header_match.group(1)
            current_line_number = ["初六", "九二", "六三", "六四", "六五", "上九"].index(sub_line_text) + 1
            current_sub_header = "yaoci"
            sub_content[current_line_number][current_sub_header] += line.strip() + "\n"
            continue
        
        # Match sub-header types
        sub_header_type_match = re.match(r"(白话文解释|《象辞》说|凶：|台湾国学大儒傅佩荣解|变卦|哲学含义)", line)
        if sub_header_type_match:
            sub_header_type = sub_header_type_match.group(1)
            if "白话文解释" in line or "爻辞释义" in line:
                current_sub_header = "yaoci"
            elif "凶：" in line or "吉：" in line:
                current_sub_header = "zhaoyong"
            elif "台湾国学大儒傅佩荣解" in line:
                current_sub_header = "fupeirong"
            elif "变卦" in line:
                current_sub_header = "var"
            elif "哲学含义" in line:
                current_sub_header = "philos"
            if current_line_number and current_sub_header:
                sub_content[current_line_number][current_sub_header] += line.strip() + "\n"
            continue

        # Continue appending to the current section
        if current_main_header:
            organized_content[current_main_header] += line.strip() + "\n"
        elif current_line_number and current_sub_header:
            sub_content[current_line_number][current_sub_header] += line.strip() + "\n"

    # Write to the output file
    with open(output_path, 'w', encoding='utf-8') as output_file:
        # Write main headers
        for header in main_headers:
            if organized_content[header].strip():
                output_file.write(f"{gua_number}.{header}.\n")
                output_file.write(organized_content[header].strip() + "\n\n")
        
        # Write sub headers
        for line_number in range(1, 7):
            for header in sub_headers:
                if sub_content[line_number][header].strip():
                    output_file.write(f"{gua_number}.{line_number}.{header}.\n")
                    output_file.write(sub_content[line_number][header].strip() + "\n\n")

if __name__ == "__main__":
    input_file = "/Users/rx/Documents/VSCode/iching/guaci/第4卦_蒙卦(山水蒙).txt"
    output_file = "/Users/rx/Documents/VSCode/iching/guaci/第4卦_蒙卦(山蒙).txt"
    gua_number = 4  # Specify the gua number
    organize_text(input_file, output_file, gua_number)
