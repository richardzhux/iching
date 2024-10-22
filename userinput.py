import bazicalc  # Assuming bazicalc contains load_hexagrams and the main Gua processing logic
import bazitime  # Assuming bazitime contains the time-related processing logic
from datetime import datetime

def validate_time_input(time_input):
    """
    Validate and parse time in yyyy.mm.dd.hhmm format.
    Automatically adjusts for input format and forbids dates before October 15, 1582.
    Returns a datetime object if valid. Prints an error message if invalid.
    """
    try:
        # Split the input by '.'
        parts = time_input.split('.')
        
        if len(parts) != 4:
            print("时间格式无效。请按照 'yyyy.mm.dd.hhmm' 的格式输入。")
            return None

        year, month, day, time_part = parts
        
        # Validate year, ensure it's between 1582 and 9999
        if not (1582 <= int(year) <= 9999):
            print("无效的年份。年份应在 1582 年 10 月 15 日之后。")
            return None
        
        # Validate and auto-correct month (convert 1 to 01)
        if not (1 <= int(month) <= 12):
            print("无效的月份。月份应在 1 到 12 之间。")
            return None
        month = month.zfill(2)

        # Validate and auto-correct day (convert 1 to 01)
        if not (1 <= int(day) <= 31):
            print("无效的日期。日期应在 1 到 31 之间。")
            return None
        day = day.zfill(2)

        # Validate the time part (hhmm)
        if len(time_part) != 4 or not time_part.isdigit():
            print("无效的时间格式。时间应为四位数字，表示小时和分钟 (hhmm)。")
            return None
        hour = int(time_part[:2])
        minute = int(time_part[2:])

        # Ensure hours and minutes are valid
        if not (0 <= hour < 24):
            print("无效的小时。小时应在 0 到 23 之间。")
            return None
        if not (0 <= minute < 60):
            print("无效的分钟。分钟应在 0 到 59 之间。")
            return None

        # Create the formatted date-time string
        formatted_input = f"{year.zfill(4)}-{month}-{day} {time_part[:2]}:{time_part[2:]}"
        
        # Parse the date and time
        time_obj = datetime.strptime(formatted_input, "%Y-%m-%d %H:%M")

        # Ensure the date is after October 15, 1582
        cutoff_date = datetime(1582, 10, 15)
        if time_obj < cutoff_date:
            print("无效的日期。日期应在 1582 年 10 月 15 日之后。")
            return None

        return time_obj
    except ValueError:
        print("无效的日期或时间。请检查输入的年月日和时间。")
        return None

def main():
    """
    Main function to get user input for Gua in the format of 6-9 and a custom time.
    """
    hexagrams = bazicalc.load_hexagrams('iching/guaxiang.txt')  # Adjust the path as needed

    while True:
        # Get Gua input from the user
        print("请输入您的卦象 (格式为六个数字，每个数字为6到9)")
        gua_input = input("提示：6为老阴，7少阳，8少阴，9老阳，从下到上输入: ").strip()

        if gua_input.isdigit() and len(gua_input) == 6 and all(c in '6789' for c in gua_input):
            # Convert to a list of integers for each digit
            lines = [int(c) for c in gua_input]
            break  # Valid input, exit the loop
        else:
            print("无效的卦象输入。请使用六位数字（范围为6到9）。")
    
    while True:
        # Loop to validate time input
        time_input = input("请输入您得到卦象的时间 (格式为 'yyyy.mm.dd.hhmm'): ").strip()
        time_obj = validate_time_input(time_input)

        if time_obj:
            break  # Valid input, exit the loop

    # Call bazitime and bazicalc with the user inputs
    print("\n正在进行时间相关计算...")
    bazitime.mainforinput(time_obj)  # Pass the parsed time object to bazitime
    print("\n正在进行卦象计算...")
    bazicalc.main(lines)