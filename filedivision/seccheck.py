import os
import re

# Define the expected section prefixes using 'xx' placeholders
expected_section_prefixes = [
    "xx.original",
    "xx.raw",
    "xx.duan",
    "xx.zhao",
    "xx.fu",
    "xx.traditional",
    "xx.1.original",
    "xx.1.var",
    "xx.1.philos",
    "xx.2.original",
    "xx.2.var",
    "xx.2.philos",
    "xx.3.original",
    "xx.3.var",
    "xx.3.philos",
    "xx.4.original",
    "xx.4.var",
    "xx.4.philos",
    "xx.5.original",
    "xx.5.var",
    "xx.5.philos",
    "xx.6.original",
    "xx.6.var",
    "xx.6.philos",
]


def check_file_for_missing_sections(file_path, gua_number):
    """Check a single gua file for missing sections, replacing 'xx' with actual gua number."""
    with open(file_path, "r", encoding="utf-8") as file:
        content = file.read()

    # Replace 'xx' with the actual gua number in expected sections
    actual_section_prefixes = [
        prefix.replace("xx", str(gua_number)) for prefix in expected_section_prefixes
    ]

    # Find all the section titles in the file
    found_sections = set()
    for section in actual_section_prefixes:
        if section in content:
            found_sections.add(section)

    # Determine which sections are missing
    missing_sections = [
        section for section in actual_section_prefixes if section not in found_sections
    ]

    return missing_sections


def generate_report(folder_path):
    """Generate a report of missing sections for all files in the folder, sorted by numeric order."""
    gua_files = [f for f in os.listdir(folder_path) if f.endswith(".txt")]

    if not gua_files:
        print("No Gua files found in the folder.")
        return

    print("Missing Sections Report:\n")

    # Regex pattern to extract gua number from filenames in format like "39.蹇卦.txt"
    filename_pattern = re.compile(r"^(\d+)\.")

    # Create a list of tuples (gua_number, gua_file) for sorting
    gua_files_with_numbers = []
    for gua_file in gua_files:
        match = filename_pattern.match(gua_file)
        if match:
            gua_number = int(match.group(1))  # Extract the Gua number
            gua_files_with_numbers.append((gua_number, gua_file))

    # Sort the list by the extracted gua number
    gua_files_with_numbers.sort(key=lambda x: x[0])

    # Process files in numeric order
    for gua_number, gua_file in gua_files_with_numbers:
        file_path = os.path.join(folder_path, gua_file)

        try:
            missing_sections = check_file_for_missing_sections(file_path, gua_number)

            if missing_sections:
                print(f"File: {gua_file}")
                print(f"Missing Sections: {', '.join(missing_sections)}\n")
            else:
                print(f"File: {gua_file} - All sections are present.\n")

        except Exception as e:
            print(f"Error processing file {gua_file}: {e}")


# Example usage:
generated_folder_path = "/Users/rx/Documents/VSCode/iching/ped_guaci"
generate_report(generated_folder_path)

"""

Missing Sections Report:

File: 1.乾卦.txt
Missing Sections: 1.1.original, 1.2.original, 1.3.original, 1.4.original, 1.5.original, 1.6.original

File: 2.坤卦.txt
Missing Sections: 2.1.original, 2.1.var, 2.2.original, 2.2.var, 2.3.original, 2.3.var, 2.4.original, 2.4.var, 2.5.original, 2.5.var, 2.6.original, 2.6.var

File: 3.屯卦.txt
Missing Sections: 3.1.original, 3.2.original, 3.2.var, 3.3.original, 3.3.var, 3.4.original, 3.4.var, 3.5.original, 3.6.original, 3.6.var

File: 4.蒙卦.txt
Missing Sections: 4.1.original, 4.1.var, 4.2.original, 4.2.philos, 4.3.original, 4.3.var, 4.4.original, 4.4.var, 4.5.original, 4.5.var, 4.6.original

File: 5.需卦.txt
Missing Sections: 5.1.original, 5.2.original, 5.3.original, 5.4.original, 5.4.var, 5.5.original, 5.6.original, 5.6.var

File: 6.讼卦.txt
Missing Sections: 6.1.original, 6.1.var, 6.2.original, 6.3.original, 6.3.var, 6.4.original, 6.5.original, 6.6.original

File: 7.师卦.txt
Missing Sections: 7.1.original, 7.1.var, 7.2.original, 7.3.original, 7.3.var, 7.4.original, 7.4.var, 7.5.original, 7.5.var, 7.6.original, 7.6.var

File: 8.比卦.txt
Missing Sections: 8.1.original, 8.1.var, 8.2.original, 8.2.var, 8.3.original, 8.3.var, 8.4.original, 8.4.var, 8.5.original, 8.6.original, 8.6.var

File: 9.小畜卦.txt
Missing Sections: 9.1.original, 9.2.original, 9.3.original, 9.4.original, 9.4.var, 9.5.original, 9.6.original

File: 10.履卦.txt
Missing Sections: 10.1.original, 10.2.original, 10.3.original, 10.3.var, 10.4.original, 10.5.original, 10.6.original

File: 11.泰卦.txt
Missing Sections: 11.original, 11.traditional, 11.1.original, 11.2.original, 11.3.original, 11.4.original, 11.4.var, 11.5.original, 11.5.var, 11.6.original, 11.6.var

File: 12.否卦.txt
Missing Sections: 12.1.original, 12.1.var, 12.2.original, 12.2.var, 12.3.original, 12.3.var, 12.4.original, 12.5.original, 12.6.original

File: 13.同人卦.txt
Missing Sections: 13.1.original, 13.2.original, 13.2.var, 13.3.original, 13.4.original, 13.5.original, 13.6.original

File: 14.大有卦.txt
Missing Sections: 14.1.original, 14.2.original, 14.3.original, 14.4.original, 14.5.original, 14.5.var, 14.6.original

File: 15.谦卦.txt
Missing Sections: 15.1.original, 15.1.var, 15.2.original, 15.2.var, 15.3.original, 15.4.original, 15.4.var, 15.5.original, 15.5.var, 15.6.original, 15.6.var

File: 16.豫卦.txt
Missing Sections: 16.1.original, 16.1.var, 16.2.original, 16.2.var, 16.3.original, 16.3.var, 16.4.original, 16.5.original, 16.5.var, 16.6.original, 16.6.var

File: 17.随卦.txt
Missing Sections: 17.1.original, 17.2.original, 17.2.var, 17.3.original, 17.3.var, 17.4.original, 17.5.original, 17.6.original, 17.6.var

File: 18.蛊卦.txt
Missing Sections: 18.1.original, 18.1.var, 18.2.original, 18.3.original, 18.4.original, 18.4.var, 18.5.original, 18.5.var, 18.6.original

File: 19.临卦.txt
Missing Sections: 19.1.original, 19.2.original, 19.3.original, 19.3.var, 19.4.original, 19.4.var, 19.5.original, 19.5.var, 19.6.original, 19.6.var

File: 20.观卦.txt
Missing Sections: 20.1.original, 20.1.var, 20.2.original, 20.2.var, 20.3.original, 20.3.var, 20.4.original, 20.4.var, 20.5.original, 20.6.original

File: 21.噬嗑卦.txt
Missing Sections: 21.1.original, 21.2.original, 21.2.var, 21.3.original, 21.3.var, 21.4.original, 21.5.original, 21.5.var, 21.6.original

File: 22.贲卦.txt
Missing Sections: 22.1.original, 22.2.original, 22.2.var, 22.3.original, 22.4.original, 22.4.var, 22.5.original, 22.5.var, 22.6.original

File: 23.剥卦.txt
Missing Sections: 23.1.original, 23.1.var, 23.2.original, 23.2.var, 23.3.original, 23.3.var, 23.4.original, 23.4.var, 23.5.original, 23.5.var, 23.6.original

File: 24.复卦.txt
Missing Sections: 24.1.original, 24.2.original, 24.2.var, 24.3.original, 24.3.var, 24.4.original, 24.4.var, 24.5.original, 24.5.var, 24.6.original, 24.6.var

File: 25.无妄卦.txt
Missing Sections: 25.1.original, 25.2.original, 25.2.var, 25.3.original, 25.3.var, 25.4.original, 25.5.original, 25.6.original

File: 26.大畜卦.txt
Missing Sections: 26.1.original, 26.2.original, 26.3.original, 26.4.original, 26.4.var, 26.5.original, 26.5.var, 26.6.original

File: 27.颐卦.txt
Missing Sections: 27.1.original, 27.2.original, 27.2.var, 27.3.original, 27.3.var, 27.4.original, 27.4.var, 27.5.original, 27.5.var, 27.6.original

File: 28.大过卦.txt
Missing Sections: 28.1.original, 28.1.var, 28.2.original, 28.3.original, 28.4.original, 28.5.original, 28.6.original, 28.6.var

File: 29.坎卦.txt
Missing Sections: 29.1.original, 29.1.var, 29.2.original, 29.3.original, 29.3.var, 29.4.original, 29.4.var, 29.4.philos, 29.5.original, 29.5.philos, 29.6.original, 29.6.var, 29.6.philos

File: 30.离卦.txt
Missing Sections: 30.1.original, 30.2.original, 30.2.var, 30.3.original, 30.4.original, 30.5.original, 30.5.var, 30.6.original

File: 31.咸卦.txt
Missing Sections: 31.1.original, 31.1.var, 31.2.original, 31.2.var, 31.3.original, 31.4.original, 31.5.original, 31.6.original, 31.6.var

File: 32.恒卦.txt
Missing Sections: 32.1.original, 32.1.var, 32.2.original, 32.3.original, 32.4.original, 32.5.original, 32.5.var, 32.6.original, 32.6.var

File: 33.遁卦.txt
Missing Sections: 33.1.original, 33.1.var, 33.2.original, 33.2.var, 33.3.original, 33.4.original, 33.5.original, 33.6.original

File: 34.大壮卦.txt
Missing Sections: 34.1.original, 34.2.original, 34.3.original, 34.4.original, 34.5.original, 34.5.var, 34.6.original, 34.6.var

File: 35.晋卦.txt
Missing Sections: 35.1.original, 35.1.var, 35.2.original, 35.2.var, 35.3.original, 35.3.var, 35.4.original, 35.5.original, 35.5.var, 35.6.original

File: 36.明夷卦.txt
Missing Sections: 36.1.original, 36.2.original, 36.2.var, 36.3.original, 36.4.original, 36.4.var, 36.5.original, 36.5.var, 36.6.original, 36.6.var

File: 37.家人卦.txt
Missing Sections: 37.1.original, 37.2.original, 37.2.var, 37.3.original, 37.4.original, 37.4.var, 37.5.original, 37.6.original

File: 38.睽卦.txt
Missing Sections: 38.1.original, 38.2.original, 38.3.original, 38.3.var, 38.4.original, 38.5.original, 38.5.var, 38.6.original

File: 39.蹇卦.txt
Missing Sections: 39.1.original, 39.1.var, 39.2.original, 39.2.var, 39.3.original, 39.4.original, 39.4.var, 39.5.original, 39.6.original, 39.6.var

File: 40.解卦.txt
Missing Sections: 40.1.original, 40.1.var, 40.2.original, 40.3.original, 40.3.var, 40.4.original, 40.5.original, 40.5.var, 40.6.original, 40.6.var

File: 41.损卦.txt
Missing Sections: 41.1.original, 41.2.original, 41.3.original, 41.3.var, 41.4.original, 41.4.var, 41.5.original, 41.5.var, 41.6.original

File: 42.益卦.txt
Missing Sections: 42.1.original, 42.2.original, 42.2.var, 42.3.original, 42.3.var, 42.4.original, 42.4.var, 42.5.original, 42.6.original

File: 43.夬卦.txt
Missing Sections: 43.1.original, 43.2.original, 43.3.original, 43.4.original, 43.5.original, 43.6.original, 43.6.var

File: 44.姤卦.txt
Missing Sections: 44.1.original, 44.1.var, 44.2.original, 44.3.original, 44.4.original, 44.5.original, 44.6.original

File: 45.萃卦.txt
Missing Sections: 45.1.original, 45.1.var, 45.2.original, 45.2.var, 45.3.original, 45.3.var, 45.4.original, 45.5.original, 45.6.original, 45.6.var

File: 46.升卦.txt
Missing Sections: 46.1.original, 46.1.var, 46.2.original, 46.3.original, 46.4.original, 46.4.var, 46.5.original, 46.5.var, 46.6.original, 46.6.var

File: 47.困卦.txt
Missing Sections: 47.1.original, 47.1.var, 47.2.original, 47.3.original, 47.3.var, 47.4.original, 47.5.original, 47.6.original, 47.6.var

File: 48.井卦.txt
Missing Sections: 48.1.original, 48.1.var, 48.2.original, 48.3.original, 48.4.original, 48.4.var, 48.5.original, 48.6.original, 48.6.var

File: 49.革卦.txt
Missing Sections: 49.1.original, 49.2.original, 49.2.var, 49.3.original, 49.4.original, 49.5.original, 49.6.original, 49.6.var

File: 50.鼎卦.txt
Missing Sections: 50.1.original, 50.1.var, 50.2.original, 50.3.original, 50.4.original, 50.5.original, 50.5.var, 50.6.original

File: 51.震卦.txt
Missing Sections: 51.1.original, 51.2.original, 51.2.var, 51.3.original, 51.3.var, 51.4.original, 51.5.original, 51.5.var, 51.6.original, 51.6.var

File: 52.艮卦.txt
Missing Sections: 52.1.original, 52.1.var, 52.2.original, 52.2.var, 52.3.original, 52.4.original, 52.4.var, 52.5.original, 52.5.var, 52.6.original

File: 53.渐卦.txt
Missing Sections: 53.1.original, 53.1.var, 53.2.original, 53.2.var, 53.3.original, 53.4.original, 53.4.var, 53.5.original, 53.6.original

File: 54.归妹卦.txt
Missing Sections: 54.1.original, 54.2.original, 54.3.original, 54.3.var, 54.4.original, 54.5.original, 54.5.var, 54.6.original, 54.6.var

File: 55.丰卦.txt
Missing Sections: 55.1.original, 55.2.original, 55.2.var, 55.3.original, 55.4.original, 55.5.original, 55.5.var, 55.6.original, 55.6.var

File: 56.旅卦.txt
Missing Sections: 56.1.original, 56.1.var, 56.2.original, 56.2.var, 56.2.philos, 56.3.original, 56.4.original, 56.5.original, 56.5.var, 56.6.original

File: 57.巽卦.txt
Missing Sections: 57.1.original, 57.1.var, 57.1.philos, 57.2.original, 57.2.philos, 57.3.original, 57.3.philos, 57.4.original, 57.4.var, 57.4.philos, 57.5.original, 57.5.philos, 57.6.original, 57.6.philos

File: 58.兑卦.txt
Missing Sections: 58.1.original, 58.2.original, 58.3.original, 58.3.var, 58.4.original, 58.5.original, 58.6.original, 58.6.var

File: 59.涣卦.txt
Missing Sections: 59.1.original, 59.1.var, 59.2.original, 59.3.original, 59.3.var, 59.4.original, 59.4.var, 59.5.original, 59.6.original

File: 60.节卦.txt
Missing Sections: 60.1.original, 60.2.original, 60.2.philos, 60.3.original, 60.3.var, 60.4.original, 60.4.var, 60.5.original, 60.6.original, 60.6.var

File: 61.中孚卦.txt
Missing Sections: 61.1.original, 61.2.original, 61.3.original, 61.3.var, 61.4.original, 61.4.var, 61.5.original, 61.6.original

File: 62.小过卦.txt
Missing Sections: 62.1.original, 62.1.var, 62.2.original, 62.2.var, 62.3.original, 62.4.original, 62.5.original, 62.5.var, 62.6.original, 62.6.var

File: 63.既济卦.txt
Missing Sections: 63.1.original, 63.2.original, 63.2.var, 63.3.original, 63.3.philos, 63.4.original, 63.4.var, 63.5.original, 63.6.original, 63.6.var

File: 64.未济卦.txt
Missing Sections: 64.1.original, 64.1.var, 64.2.original, 64.2.philos, 64.3.original, 64.3.var, 64.4.original, 64.5.original, 64.5.var, 64.6.original

"""
