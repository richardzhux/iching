import os
import re


def chinese_to_arabic(cn):
    """Convert Chinese numerals to Arabic numerals."""
    cn_num = {
        "零": 0,
        "一": 1,
        "二": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
    }
    cn_unit = {
        "十": 10,
        "百": 100,
        "千": 1000,
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
            pass  # Ignore any other characters
    if unit:
        ldig.append(unit)
    return sum(ldig)


def parse_hexagram_yao(binary_rep):
    """Given a binary representation, return the corresponding yao names."""
    yao_map = [
        "九" if bit == "1" else "六" for bit in binary_rep
    ]  # '九' for Yang, '六' for Yin
    yao_positions = ["初", "二", "三", "四", "五", "上"]  # Positions from bottom to top
    yao_names = [
        f"{yao_positions[i]}{yao_map[i]}" for i in range(6)
    ]  # Combine position and nature (Yin/Yang)
    return yao_names


def load_hexagram_data(file_path):
    """Load the hexagram data from the file, assuming data for gua n is at line n + 2."""
    hexagram_data = {}
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            all_lines = file.readlines()

            # There should be at least 64 entries starting from line 3 (index 2)
            for n in range(1, 65):  # Gua numbers from 1 to 64
                line_index = (
                    n + 2 - 1
                )  # Adjust to 0-based index (n + 2 is the actual line number)
                if line_index < len(all_lines):
                    line = all_lines[line_index].strip()
                    if line:
                        parts = line.split(",")
                        if len(parts) == 3:
                            hexagram_name = parts[0].strip()
                            binary_rep = parts[1].strip()
                            explanation = parts[2].strip()

                            if len(binary_rep) == 6 and all(
                                c in "01" for c in binary_rep
                            ):
                                # Store the data using the gua number (n) as key
                                hexagram_data[n] = {
                                    "name": hexagram_name,
                                    "binary": binary_rep,
                                    "explanation": explanation,
                                }
                            else:
                                print(
                                    f"Invalid binary representation for gua {n}: '{binary_rep}'"
                                )
                        else:
                            print(f"Skipping invalid line for gua {n}: {line}")
                else:
                    print(f"Line index {line_index} out of range for gua {n}")
    except Exception as e:
        print(f"Error loading hexagram data: {e}")

    return hexagram_data


def split_gua_into_sections(content):
    """Splits the content into sections based on section titles."""
    sections = {}
    current_section_title = None
    for line in content.split("\n"):
        line = line.strip()
        if not line:
            continue
        # Check if the line is a section title
        if (
            line.endswith("爻详解")
            or line.endswith("变卦")
            or line.endswith("爻的哲学含义")
            or line.endswith("卦原文")
            or line == "白话文解释"
            or line == "《断易天机》解"
            or line == "北宋易学家邵雍解"
            or line == "台湾国学大儒傅佩荣解"
            or line == "传统解卦"
            or "哲学含义" in line
        ):
            current_section_title = line
            sections[current_section_title] = ""
        else:
            if current_section_title:
                sections[current_section_title] += line + "\n"
    return sections


def process_gua_file(input_file, hexagram_data, output_folder):
    """Processes a single Gua file and outputs the result to the output folder."""
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"Created output folder: {output_folder}")

    with open(input_file, "r", encoding="utf-8") as file:
        content = file.read()

    # Extract gua_number and gua_name from the filename
    filename = os.path.basename(input_file)
    filename_without_ext = os.path.splitext(filename)[0]

    # Regex pattern to extract gua number and gua name from filename
    filename_pattern = re.compile(
        r"^第([一二三四五六七八九十百零\d]+)卦[_：](.*?)[\(\uFF08]"
    )
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
        print(
            f"Error converting gua number '{gua_number_str}' in filename {filename}: {e}"
        )
        return

    print(f"Extracted gua_number: {gua_number}, gua_name: {gua_name}")

    # Check if the gua number exists in hexagram_data
    if gua_number not in hexagram_data:
        print(
            f"No hexagram data found for gua number {gua_number}. Hexagram data keys: {list(hexagram_data.keys())}"
        )
        return

    gua_data = hexagram_data[gua_number]
    binary_rep = gua_data["binary"]
    explanation = gua_data["explanation"]
    yao_names = parse_hexagram_yao(binary_rep)

    sections = split_gua_into_sections(content)

    output_file = os.path.join(output_folder, f"{gua_number}.{gua_name}.txt")
    print(f"Creating file: {output_file}")
    with open(output_file, "w", encoding="utf-8") as out_file:
        # Write the main sections
        out_file.write(f"{gua_number}.周易第{gua_number}卦详解\n\n")

        # List of section titles and their prefixes
        main_sections = [
            (f"{gua_name}原文", f"{gua_number}.original.{gua_name}原文"),
            ("白话文解释", f"{gua_number}.raw.白话文解释"),
            ("《断易天机》解", f"{gua_number}.duan.《断易天机》解"),
            ("北宋易学家邵雍解", f"{gua_number}.zhao.北宋易学家邵雍解"),
            ("台湾国学大儒傅佩荣解", f"{gua_number}.fu.台湾国学大儒傅佩荣解"),
            ("传统解卦", f"{gua_number}.traditional.传统解卦"),
        ]

        for title, prefix in main_sections:
            content = sections.get(title, "")
            if content:
                out_file.write(f"{prefix}\n")
                out_file.write(content + "\n")

        # Write the yao sections (1 to 6)
        yao_positions = [
            "初",
            "二",
            "三",
            "四",
            "五",
            "上",
        ]  # Yao positions from 初 to 上
        for idx in range(6):
            yao_index = idx + 1
            position_prefix = f"{gua_number}.{yao_index}"
            yao_position = yao_positions[idx]

            # Look for sections by skipping the Yin/Yang indicator (六 or 九)
            yao_section_title = f"{yao_position}爻详解"
            original_section_title = f"{yao_position}爻辞"
            variation_section_title = f"{yao_position}变卦"
            philosophy_section_title = f"{yao_position}爻的哲学含义"

            # Create regex patterns to match the sections, ignoring 六/九
            yao_section_regex = re.compile(f"[九六]?{yao_position}爻详解")
            original_regex = re.compile(f"[九六]?{yao_position}爻辞")
            variation_regex = re.compile(f"[九六]?{yao_position}变卦")
            philosophy_regex = re.compile(f"[九六]?{yao_position}爻的哲学含义")

            # Extract the relevant content by matching the sections
            yao_content = extract_section_by_regex(sections, yao_section_regex)
            original_content = extract_section_by_regex(sections, original_regex)
            variation_content = extract_section_by_regex(sections, variation_regex)
            philosophy_content = extract_section_by_regex(sections, philosophy_regex)

            # Write the yao, original, var, and philos content for each Yao
            if yao_content:
                out_file.write(
                    f"{position_prefix}.周易第{gua_number}卦{yao_position}爻详解\n\n"
                )
                out_file.write(yao_content + "\n")
            if original_content:
                out_file.write(f"{position_prefix}.original.{yao_position}爻辞\n")
                out_file.write(original_content + "\n")
            if variation_content:
                out_file.write(f"{position_prefix}.var.{yao_position}变卦\n")
                out_file.write(variation_content + "\n")
            if philosophy_content:
                out_file.write(f"{position_prefix}.philos.{yao_position}爻的哲学含义\n")
                out_file.write(philosophy_content + "\n")

    print(f"Completed writing to file: {output_file}")


def extract_section_by_regex(sections, regex):
    """Extracts a section from the content based on the regex pattern."""
    for key, content in sections.items():
        if regex.search(key):
            return content
    return None


def process_all_gua_files(gua_folder, hexagram_data, output_folder):
    """Processes all Gua files in the given folder and outputs the results to the output folder."""
    gua_files = [f for f in os.listdir(gua_folder) if f.endswith(".txt")]

    if not gua_files:
        print("No Gua files found in the folder.")

    for gua_file in gua_files:
        file_path = os.path.join(gua_folder, gua_file)
        print(f"Processing: {file_path}")
        process_gua_file(file_path, hexagram_data, output_folder)


# Example usage:
hexagram_data_file = "/Users/rx/Documents/VSCode Python/iching/guaxiang.txt"
hexagram_data = load_hexagram_data(hexagram_data_file)

input_folder_path = "/Users/rx/Documents/VSCode Python/iching/guaci"
output_folder_path = "/Users/rx/Documents/VSCode Python/iching/processed_guaci"

process_all_gua_files(input_folder_path, hexagram_data, output_folder_path)
