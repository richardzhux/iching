import os
import random
import bazicalc

# Function to load hexagrams from file
def load_hexagrams(file_path):
    hexagrams = {}
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
        for line in lines[1:]:  # Skip the header
            parts = line.strip().split(', ')
            if len(parts) == 3:
                gua, binary, jieshi = parts
                hexagrams[binary] = (gua, jieshi)
    return hexagrams

# Function to calculate main, transformed, mutual, inverse, and reverse hexagrams
def calculate_all_hexagrams(hex_lines, hexagrams):
    # Original hexagram binary
    binary = ''.join(['1' if x in [7, 9] else '0' for x in hex_lines])
    
    # Lookup the main hexagram
    gua, jieshi = hexagrams.get(binary, (None, "卦象未找到"))
    
    # Calculate changed hexagram (only if there are old yin or old yang lines)
    changed_binary_list = list(binary)
    has_moving_line = False
    for idx, x in enumerate(hex_lines):
        if x == 9:
            changed_binary_list[idx] = '0'  # Old Yang changes to Yin
            has_moving_line = True
        elif x == 6:
            changed_binary_list[idx] = '1'  # Old Yin changes to Yang
            has_moving_line = True
    if has_moving_line:
        changed_binary = ''.join(changed_binary_list)
        changed_gua, changed_jieshi = hexagrams.get(changed_binary, (None, "变卦未找到"))
    else:
        changed_gua, changed_jieshi = None, "没有动爻，故无变卦"
    
    # Calculate inverse hexagram (错卦)
    inverse_binary = ''.join(['1' if b == '0' else '0' for b in binary])
    inverse_gua, inverse_jieshi = hexagrams.get(inverse_binary, (None, "错卦未找到"))
    
    # Calculate reverse hexagram (综卦)
    reverse_binary = binary[::-1]
    reverse_gua, reverse_jieshi = hexagrams.get(reverse_binary, (None, "综卦未找到"))
    
    # Calculate mutual hexagram (互卦): Take lines 2-4 (middle) and form new binary
    if len(binary) == 6:
        mutual_binary = binary[1:4] + binary[2:5]
        mutual_gua, mutual_jieshi = hexagrams.get(mutual_binary, (None, "互卦未找到"))
    else:
        mutual_gua, mutual_jieshi = None, "互卦未找到"
    
    # Output all results
    return {
        "main": (gua, jieshi),
        "changed": (changed_gua, changed_jieshi),
        "inverse": (inverse_gua, inverse_jieshi),
        "reverse": (reverse_gua, reverse_jieshi),
        "mutual": (mutual_gua, mutual_jieshi)
    }

# Function to search for a corresponding hexagram file
def find_hexagram_file(hexagram_name, folder='guaci'):
    # Iterate over all files in the specified folder
    for file_name in os.listdir(folder):
        if hexagram_name in file_name:  # Look for a file containing the hexagram name
            file_path = os.path.join(folder, file_name)
            return file_path
    return None

# Function to output hexagram explanation
def output_hexagram_info(hexagram_name, file_type):
    folder = 'guaci'
    file_path = find_hexagram_file(hexagram_name, folder)
    
    if file_path:
        print(f"\n{file_type}: {hexagram_name} 对应的文件: {file_path}")
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            print(f"内容: \n{content}\n")
    else:
        print(f"未找到 {file_type} 对应的文件: {hexagram_name}")

# Main function to calculate hexagrams and output results
def main(hex_lines):
    hexagrams = load_hexagrams('guaxiang.txt')     
    reversed_lines = hex_lines[::-1]

    print("\n您的卦象:")
    for i, line in enumerate(reversed_lines):
        print(f"第 {6 - i} 爻: {'--- 阳' if line in [7, 9] else '- - 阴'} {' O' if line == 9 else ' X' if line == 6 else ''}")
            
    results = calculate_all_hexagrams(hex_lines, hexagrams)
    
    print(hex_lines)
    print(f"\n本卦: {results['main'][0]} - 解释: {results['main'][1]}")
    print(f"变卦: {results['changed'][0]} - 解释: {results['changed'][1]}")
    print(f"互卦: {results['mutual'][0]} - 解释: {results['mutual'][1]}")
    print(f"错卦: {results['inverse'][0]} - 解释: {results['inverse'][1]}")
    print(f"综卦: {results['reverse'][0]} - 解释: {results['reverse'][1]}\n")

    # Output the corresponding hexagram files based on 本卦 and 变卦
    if results['main'][0]:
        output_hexagram_info(results['main'][0], "本卦")
    
    if results['changed'][0] and results['changed'][0] != "没有动爻，故无变卦":
        output_hexagram_info(results['changed'][0], "变卦")

if __name__ == "__main__":
    main()
