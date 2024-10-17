import os
import re

def chinese_to_arabic(cn):
    """Convert Chinese numerals to Arabic numerals."""
    cn_num = {
        '零': 0,
        '一': 1,
        '二': 2,
        '三': 3,
        '四': 4,
        '五': 5,
        '六': 6,
        '七': 7,
        '八': 8,
        '九': 9,
    }
    cn_unit = {
        '十': 10,
        '百': 100,
        '千': 1000,
    }
    unit = 0
    ldig = []
    for c in reversed(cn):
        if c in cn_unit:
            unit = cn_unit.get(c)
            if unit == 10 and (not ldig or ldig[-1] >= 10):
                ldig.append(1 * unit)
        elif c in cn_num:
            num = cn_num.get(c)
            if unit:
                num *= unit
                unit = 0
            ldig.append(num)
        else:
            # Ignore any other characters
            pass
    if unit:
        ldig.append(unit)
    result = sum(ldig)
    return result

def parse_hexagram_yao(binary_rep):
    """Given a binary representation, returns the corresponding yao names."""
    yao_map = ['九' if bit == '1' else '六' for bit in binary_rep]  # '九' for Yang, '六' for Yin
    yao_positions = ['初', '二', '三', '四', '五', '上']  # Positions from bottom to top
    yao_names = [f"{yao_positions[i]}{yao_map[i]}" for i in range(6)]  # Combine position and nature (Yin/Yang)
    return yao_names

def load_hexagram_data(file_path):
    """Loads the hexagram data from a file, assuming data for gua n is at line n + 2."""
    hexagram_data = {}
    with open(file_path, 'r', encoding='utf-8') as file:
        all_lines = file.readlines()
        # Adjust the starting index if there are header lines
        data_start_index = 2  # Assuming first two lines are headers
        for n in range(1, 65):  # Gua numbers from 1 to 64
            line_index = n + data_start_index - 1  # Adjust for zero-based index
            if line_index < len(all_lines):
                line = all_lines[line_index].strip()
                if line:
                    # Parse the line to get binary data and other information
                    # Assuming the line contains binary representation and possibly other data
                    # Adjust the parsing as per the actual format of your lines
                    parts = line.strip().split(',')
                    if len(parts) >= 1:
                        binary_rep = parts[0].strip()
                        gua_name = parts[1].strip() if len(parts) > 1 else ''
                        explanation = parts[2].strip() if len(parts) > 2 else ''
                        hexagram_data[n] = {
                            'name': gua_name,
                            'binary': binary_rep,
                            'explanation': explanation
                        }
                    else:
                        print(f"Skipping invalid line at gua {n}: {line}")
                else:
                    print(f"Empty line at gua {n}")
            else:
                print(f"No data for gua {n}, line index {line_index} out of range")
    return hexagram_data


def split_gua_into_sections(content):
    """Splits the content into sections based on section titles."""
    sections = {}
    current_section_title = None
    for line in content.split('\n'):
        line = line.strip()
        if not line:
            continue
        # Check if the line is a section title
        if line.endswith('爻详解') or line.endswith('变卦') or line.endswith('爻的哲学含义') \
            or line.endswith('卦原文') or line == '白话文解释' or line == '《断易天机》解' \
            or line == '北宋易学家邵雍解' or line == '台湾国学大儒傅佩荣解' \
            or line == '传统解卦' or '哲学含义' in line:
            current_section_title = line
            sections[current_section_title] = ''
        else:
            if current_section_title:
                sections[current_section_title] += line + '\n'
    return sections

def process_gua_file(input_file, hexagram_data, output_folder):
    """Processes a single Gua file and outputs the result to the output folder."""
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"Created output folder: {output_folder}")

    with open(input_file, 'r', encoding='utf-8') as file:
        content = file.read()

    # Extract gua_number and gua_name from the filename
    filename = os.path.basename(input_file)
    filename_without_ext = os.path.splitext(filename)[0]

    # Regex pattern to extract gua number and gua name from filename
    filename_pattern = re.compile(r'^第([一二三四五六七八九十百零\d]+)卦[_：](.*?)[\(\uFF08]')
    match = filename_pattern.match(filename_without_ext)
    if not match:
        print(f"No gua information found in filename {filename}")
        return

    gua_number_str = match.group(1).strip()
    gua_name = match.group(2).strip()

    # Convert Chinese numerals to Arabic numerals if necessary
    try:
        if gua_number_str.isdigit():
            gua_number = int(gua_number_str)
        else:
            gua_number = chinese_to_arabic(gua_number_str)
    except Exception as e:
        print(f"Error converting gua number '{gua_number_str}' in filename {filename}: {e}")
        return

    print(f"Extracted gua_number: {gua_number}, gua_name: {gua_name}")

    if gua_number not in hexagram_data:
        print(f"No hexagram data found for gua number {gua_number}")
        return

    gua_data = hexagram_data[gua_number]
    binary_rep = gua_data['binary']
    explanation = gua_data['explanation']
    yao_names = parse_hexagram_yao(binary_rep)

    sections = split_gua_into_sections(content)

    # Now, write the output file in the desired format
    output_file = os.path.join(output_folder, f"{gua_number}.{gua_name}.txt")
    print(f"Creating file: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as out_file:
        # Write the main sections
        out_file.write(f"{gua_number}.周易第{gua_number}卦详解\n\n")

        # List of section titles and their prefixes
        main_sections = [
            (f"{gua_name}原文", f"{gua_number}.original.{gua_name}原文"),
            ('白话文解释', f"{gua_number}.raw.白话文解释"),
            ('《断易天机》解', f"{gua_number}.duan.《断易天机》解"),
            ('北宋易学家邵雍解', f"{gua_number}.zhao.北宋易学家邵雍解"),
            ('台湾国学大儒傅佩荣解', f"{gua_number}.fu.台湾国学大儒傅佩荣解"),
            ('传统解卦', f"{gua_number}.traditional.传统解卦"),
        ]

        # Write main sections
        for title, prefix in main_sections:
            content = sections.get(title, '')
            if content:
                out_file.write(f"{prefix}\n")
                out_file.write(content + '\n')

        # Philosophical meaning
        for key in sections.keys():
            if '哲学含义' in key:
                prefix = f"{gua_number}.philos.{key}"
                content = sections[key]
                out_file.write(f"{prefix}\n")
                out_file.write(content + '\n')
                break  # Assume only one philosophical meaning section

        # Write the yao sections
        for idx in range(6):
            yao_index = idx + 1
            position_prefix = f"{gua_number}.{yao_index}"
            # Since the yao are from bottom to top, reverse the yao_names
            yao_name = yao_names[idx]

            # Section titles
            yao_section_title = f"{yao_name}爻详解"
            variation_section_title = f"{yao_name}变卦"
            philosophy_section_title = f"{yao_name}爻的哲学含义"

            # Get content for each section
            yao_content = sections.get(yao_section_title, '')
            variation_content = sections.get(variation_section_title, '')
            philosophy_content = sections.get(philosophy_section_title, '')

            # Write yao content if available
            if yao_content:
                out_file.write(f"{position_prefix}.周易第{gua_number}卦{yao_name}爻详解\n\n")
                out_file.write(f"{position_prefix}.original.{yao_name}爻辞\n")
                out_file.write(yao_content + '\n')
            if variation_content:
                out_file.write(f"{position_prefix}.var.{yao_name}变卦\n")
                out_file.write(variation_content + '\n')
            if philosophy_content:
                out_file.write(f"{position_prefix}.philos.{yao_name}爻的哲学含义\n")
                out_file.write(philosophy_content + '\n')

    print(f"Completed writing to file: {output_file}")

def process_all_gua_files(gua_folder, hexagram_data, output_folder):
    """Processes all Gua files in the given folder and outputs the results to the output folder."""
    gua_files = [f for f in os.listdir(gua_folder) if f.endswith('.txt')]

    if not gua_files:
        print("No Gua files found in the folder.")

    for gua_file in gua_files:
        file_path = os.path.join(gua_folder, gua_file)
        print(f"Processing: {file_path}")
        process_gua_file(file_path, hexagram_data, output_folder)

# Example usage:
hexagram_data_file = '/Users/rx/Documents/VSCode Python/iching/guaxiang.txt'
hexagram_data = load_hexagram_data(hexagram_data_file)

input_folder_path = '/Users/rx/Documents/VSCode Python/iching/guaci'
output_folder_path = '/Users/rx/Documents/VSCode Python/iching/processed_guaci'

process_all_gua_files(input_folder_path, hexagram_data, output_folder_path)


"""
# Define categories based on your comments
categories = {
    "original_text": "屯卦原文",
    "duanyitianji": "《断易天机》解",
    "zhao_yongjie": "北宋易学家邵雍解",
    "fu_peirong": "台湾国学大儒傅佩荣解",
    "traditional_explanation": "传统解卦",
    "philosophical_meaning": "第三卦哲学含义",  # Or loop to generate for each gua dynamically

    # Define all six Yao entries and their variations
    "1st_yao": "周易第三卦初九爻详解",
    "1st_yao_variation": "初九变卦",
    "2nd_yao": "周易第三卦九二爻详解",
    "2nd_yao_variation": "六二变卦",
    "3rd_yao": "周易第三卦九三爻详解",
    "3rd_yao_variation": "六三变卦",
    "4th_yao": "周易第三卦九四爻详解",
    "4th_yao_variation": "六四变卦",
    "5th_yao": "周易第三卦九五爻详解",
    "5th_yao_variation": "六五变卦",
    "6th_yao": "周易第三卦上九爻详解",
    "6th_yao_variation": "上六变卦"
}

# Dynamically generate philosophical meaning and yao explanations for each Gua
def generate_gua_categories(gua_number):
    # Base name for Gua (e.g., "第三卦哲学含义")
    base_name = f"第{gua_number}卦哲学含义"
    gua_yao_name = f"周易第{gua_number}卦"
    
    categories = {
        "original_text": f"{gua_yao_name}原文",
        "duanyitianji": "《断易天机》解",
        "zhao_yongjie": "北宋易学家邵雍解",
        "fu_peirong": "台湾国学大儒傅佩荣解",
        "traditional_explanation": "传统解卦",
        "philosophical_meaning": f"{gua_yao_name}哲学含义",

        # Define all six Yao entries and their variations
        "1st_yao": f"{gua_yao_name}初x爻详解",
        "1st_yao_variation": "初x变卦",
        "2nd_yao": f"{gua_yao_name}二爻详解",
        "2nd_yao_variation": "x二变卦",
        "3rd_yao": f"{gua_yao_name}三爻详解",
        "3rd_yao_variation": "x三变卦",
        "4th_yao": f"{gua_yao_name}四爻详解",
        "4th_yao_variation": "x四变卦",
        "5th_yao": f"{gua_yao_name}五爻详解",
        "5th_yao_variation": "x五变卦",
        "6th_yao": f"{gua_yao_name}上x爻详解",
        "6th_yao_variation": "x六变卦"
    }

    return categories

import os
import re

# Function to generate the Gua categories dynamically
def generate_gua_categories():
    categories = {
        "original_text": "原文",
        "duanyitianji": "《断易天机》解",
        "zhao_yongjie": "北宋易学家邵雍解",
        "fu_peirong": "台湾国学大儒傅佩荣解",
        "traditional_explanation": "传统解卦",
        "philosophical_meaning": "哲学含义"
    }

    # Dynamically generate entries for the six yao explanations and variations
    yao_names = ["初九", "九二", "六三", "九四", "九五", "上九"]
    for i, yao in enumerate(yao_names, start=1):
        categories[f"{i}_yao"] = f"周易第{i}卦{yao}爻详解"
        categories[f"{i}_yao_variation"] = f"{yao}变卦"

    return categories

# Function to split the Gua file into categorized sections
def split_gua_into_sections(content, categories):
    sections = {key: [] for key in categories}
    current_section = None

    for line in content.split('\n'):
        line = line.strip()
        
        # Look for section titles in categories
        for key, title in categories.items():
            if title in line:
                current_section = key
                break

        # Add the line to the current section (if we are in one)
        if current_section:
            sections[current_section].append(line)

    # Merge all the lines in each section
    for key in sections:
        sections[key] = '\n'.join(sections[key])

    return sections

# Function to process each Gua file
def process_gua_files(gua_folder):
    gua_files = [f for f in os.listdir(gua_folder) if f.endswith('.txt')]
    categories = generate_gua_categories()

    for gua_file in gua_files:
        file_path = os.path.join(gua_folder, gua_file)

        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()

        sections = split_gua_into_sections(content, categories)

        # Output or store sections for each Gua
        for section_name, section_content in sections.items():
            print(f"Section: {section_name}")
            print(section_content)
            print("\n" + "="*50 + "\n")

# Specify the folder where the Gua files are stored
gua_folder = "/Users/rx/Documents/VSCode Python/iching/guaci"

# Run the processing
process_gua_files(gua_folder)

import os
import re

def parse_hexagram_yao(binary_rep):
    Given a binary representation, returns the corresponding yao names.
    yao_map = ['九' if bit == '1' else '六' for bit in binary_rep]  # '九' for Yang, '六' for Yin
    yao_positions = ['初', '二', '三', '四', '五', '上']  # Positions from bottom to top
    yao_names = [f"{yao_positions[i]}{yao_map[i]}" for i in range(6)]  # Combine position and nature (Yin/Yang)
    return yao_names

def generate_gua_categories(gua_name, yao_names):
    Generates the categories for each gua based on its Yao names.
    categories = {
        "original_text": f"{gua_name}原文",
        "duanyitianji": "《断易天机》解",
        "zhao_yongjie": "北宋易学家邵雍解",
        "fu_peirong": "台湾国学大儒傅佩荣解",
        "traditional_explanation": "传统解卦",
        "philosophical_meaning": f"{gua_name}哲学含义",
        # Dynamically generate Yao sections based on parsed yao names
        "1st_yao": f"{gua_name}{yao_names[0]}爻详解",
        "1st_yao_variation": f"{yao_names[0]}变卦",
        "2nd_yao": f"{gua_name}{yao_names[1]}爻详解",
        "2nd_yao_variation": f"{yao_names[1]}变卦",
        "3rd_yao": f"{gua_name}{yao_names[2]}爻详解",
        "3rd_yao_variation": f"{yao_names[2]}变卦",
        "4th_yao": f"{gua_name}{yao_names[3]}爻详解",
        "4th_yao_variation": f"{yao_names[3]}变卦",
        "5th_yao": f"{gua_name}{yao_names[4]}爻详解",
        "5th_yao_variation": f"{yao_names[4]}变卦",
        "6th_yao": f"{gua_name}{yao_names[5]}爻详解",
        "6th_yao_variation": f"{yao_names[5]}变卦"
    }
    return categories

def load_hexagram_data(file_path):
    Loads the hexagram data from a file.
    hexagram_data = {}
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            if line.strip():  # Skip empty lines
                try:
                    gua_name, binary_rep, explanation = line.strip().split(', ')
                    hexagram_data[gua_name] = (binary_rep, explanation)
                except ValueError:
                    print(f"Skipping invalid line: {line.strip()}")
    return hexagram_data

def split_gua_file(input_file, hexagram_data, output_folder):
    Splits the gua file into individual gua files, properly formatted with categories.
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"Created output folder: {output_folder}")
    
    with open(input_file, 'r', encoding='utf-8') as file:
        content = file.read()

    pages = content.split('---- Page')
    gua_pattern = re.compile(r"周易第(\d+)卦_(.*?)_")

    for page in pages[1:]:  # Skip the first entry, it’s empty
        lines = page.split('\n')
        title = None
        for line in lines:
            match = gua_pattern.search(line)
            if match:
                gua_number = match.group(1)
                gua_name = match.group(2).replace(" ", "")
                title = f"第{gua_number}卦_{gua_name}"
                break

        if title:
            output_file = os.path.join(output_folder, f"{title}.txt")
            print(f"Creating file: {output_file}")
            with open(output_file, 'w', encoding='utf-8') as out_file:
                # Write the original lines to the individual Gua file
                out_file.write('\n'.join(lines))
                print(f"Successfully wrote initial content to {output_file}")

            # Now process the yao based on the binary representation
            binary_rep, explanation = hexagram_data.get(gua_name, (None, None))
            if binary_rep:
                print(f"Processing Yao for: {gua_name} with binary: {binary_rep}")
                yao_names = parse_hexagram_yao(binary_rep)
                categories = generate_gua_categories(gua_name, yao_names)

                # Append the categories and explanations to the file
                with open(output_file, 'a', encoding='utf-8') as out_file:
                    out_file.write(f"\n\n--- {categories['original_text']} ---\n")
                    out_file.write(f"Explanation: {explanation}\n")
                    
                    out_file.write(f"\n--- {categories['philosophical_meaning']} ---\n")
                    out_file.write("[Philosophical meaning explanation here]\n")
                    
                    # Append each Yao and variation
                    for i in range(6):
                        out_file.write(f"\n--- {categories[f'{i+1}st_yao']} ---\n")
                        out_file.write("[Yao explanation here]\n")
                        out_file.write(f"\n--- {categories[f'{i+1}st_yao_variation']} ---\n")
                        out_file.write("[Yao variation explanation here]\n")
            else:
                print(f"No binary representation found for {gua_name}")

            print(f"Completed writing to file: {output_file}")

def process_all_gua_files(gua_folder, hexagram_data, output_folder):
    Processes all Gua files in the given folder and outputs the results to the output folder.
    gua_files = [f for f in os.listdir(gua_folder) if f.endswith('.txt')]

    if not gua_files:
        print("No Gua files found in the folder.")

    for gua_file in gua_files:
        file_path = os.path.join(gua_folder, gua_file)
        print(f"Processing: {file_path}")
        split_gua_file(file_path, hexagram_data, output_folder)

# Example usage:
hexagram_data_file = '/Users/rx/Documents/VSCode Python/iching/guaxiang.txt'
hexagram_data = load_hexagram_data(hexagram_data_file)

input_folder_path = '/Users/rx/Documents/VSCode Python/iching/guaci'
output_folder_path = '/Users/rx/Documents/VSCode Python/iching/processed_guaci'

process_all_gua_files(input_folder_path, hexagram_data, output_folder_path)

"""

