import os
import re

def check_headers_in_files(folder_path, start_index, end_index):
    # Define the required headers
    n_headers = ["guaci", "xiangci", "duanyi", "zhaoyong", "fupeirong", "zongjie", "philos"]
    nm_headers = ["yaoci", "zhaoyong", "fupeirong", "var", "philos"]
    
    # List and sort files numerically based on the gua number
    files = [f for f in os.listdir(folder_path) if f.endswith(".txt")]
    files = sorted(files, key=lambda x: int(re.search(r"第(\d+)卦", x).group(1)))

    selected_files = files[start_index:end_index + 1]

    # Iterate through the selected range of files
    for filename in selected_files:
        file_path = os.path.join(folder_path, filename)
        
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
        # Extract the number of the gua from the filename
        try:
            n = re.search(r"第(\d+)", filename).group(1)
        except AttributeError:
            print(f"Warning: Could not extract gua number from filename {filename}")
            continue

        # Check n headers
        missing_n_headers = [header for header in n_headers if f"{n}.{header}." not in content]

        # Check nm headers for m in range 1 to 6
        missing_nm_headers = []
        for m in range(1, 7):
            for header in nm_headers:
                if f"{n}.{m}.{header}." not in content:
                    missing_nm_headers.append(f"{n}.{m}.{header}")

        # Report missing headers if any
        if missing_n_headers or missing_nm_headers:
            print(f"File: {filename}")
            if missing_n_headers:
                print(f"  Missing n headers: {', '.join(missing_n_headers)}")
            if missing_nm_headers:
                print(f"  Missing nm headers: {', '.join(missing_nm_headers)}")
            print()
        else:
            print(f"{filename} - No mismatch.")

if __name__ == "__main__":
    folder_path = "/Users/rx/Documents/VSCode/iching/guaci"
    s, e = 1, 6
    start = s - 1
    end = e - 1
    check_headers_in_files(folder_path, start, end)
