import os
import re

# Define the expected section prefixes using 'n' placeholders
expected_section_prefixes = [
    'n.original', 'n.raw', 'n.duan', 'n.zhao', 'n.fu', 'n.traditional',
    'n.1.original', 'n.1.var', 'n.1.philos', 
    'n.2.original', 'n.2.var', 'n.2.philos', 
    'n.3.original', 'n.3.var', 'n.3.philos', 
    'n.4.original', 'n.4.var', 'n.4.philos', 
    'n.5.original', 'n.5.var', 'n.5.philos', 
    'n.6.original', 'n.6.var', 'n.6.philos'
]

def check_file_for_missing_sections(file_path, gua_number):
    """Check a single gua file for missing sections, replacing 'n' with actual gua number."""
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # Replace 'n' with the actual gua number in expected sections
    actual_section_prefixes = [prefix.replace('n', str(gua_number)) for prefix in expected_section_prefixes]

    # Find all the section titles in the file
    found_sections = set()
    for section in actual_section_prefixes:
        if section in content:
            found_sections.add(section)

    # Determine which sections are missing
    missing_sections = [section for section in actual_section_prefixes if section not in found_sections]

    return missing_sections

def generate_report(folder_path):
    """Generate a report of missing sections for all files in the folder."""
    gua_files = [f for f in os.listdir(folder_path) if f.endswith('.txt')]

    if not gua_files:
        print("No Gua files found in the folder.")
        return

    print("Missing Sections Report:\n")

    # Regex pattern to extract gua number from filenames in format like "39.蹇卦.txt"
    filename_pattern = re.compile(r'^(\d+)\.')

    for gua_file in gua_files:
        file_path = os.path.join(folder_path, gua_file)
        filename_without_ext = os.path.splitext(gua_file)[0]

        # Extract gua number from the filename
        match = filename_pattern.match(filename_without_ext)
        if match:
            gua_number_str = match.group(1).strip()

            try:
                gua_number = int(gua_number_str)  # Gua number is now directly extracted as an integer

                missing_sections = check_file_for_missing_sections(file_path, gua_number)

                if missing_sections:
                    print(f"File: {gua_file}")
                    print(f"Missing Sections: {', '.join(missing_sections)}\n")
                else:
                    print(f"File: {gua_file} - All sections are present.\n")

            except Exception as e:
                print(f"Error processing file {gua_file}: {e}")
        else:
            print(f"Could not extract gua number from filename {gua_file}")

# Example usage:
generated_folder_path = '/Users/rx/Documents/VSCode Python/iching/processed_guaci'
generate_report(generated_folder_path)
