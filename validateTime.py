import time
from datetime import datetime

def get_current_time():
    return datetime.now()

def get_user_time_input():
    while True:
        time_input = input("请输入您得到卦象的时间 (格式为 'yyyy.mm.dd.hhmm'): ").strip()
        time_obj = validate_time_input(time_input)
        if time_obj:
            return time_obj

def validate_time_input(time_input_str):
    """
    Validate and parse time in 'yyyy.mm.dd.hhmm' format.
    Returns a datetime object if valid; prints an error message if invalid.
    """
    try:
        parts = time_input_str.strip().split('.')
        if len(parts) != 4:
            print("时间格式无效。请按照 'yyyy.mm.dd.hhmm' 的格式输入。")
            return None

        year, month, day, time_part = parts
        year = int(year)
        month = int(month)
        day = int(day)
        if not (1582 <= year <= 9999):
            print("无效的年份。年份应在 1582 年 10 月 15 日之后。")
            return None
        if not (1 <= month <= 12):
            print("无效的月份。月份应在 1 到 12 之间。")
            return None
        if not (1 <= day <= 31):
            print("无效的日期。日期应在 1 到 31 之间。")
            return None
        if len(time_part) != 4 or not time_part.isdigit():
            print("无效的时间格式。时间应为四位数字，表示小时和分钟 (hhmm)。")
            return None
        hour = int(time_part[:2])
        minute = int(time_part[2:])
        if not (0 <= hour <= 23):
            print("无效的小时。小时应在 0 到 23 之间。")
            return None
        if not (0 <= minute <= 59):
            print("无效的分钟。分钟应在 0 到 59 之间。")
            return None

        dt = datetime(year, month, day, hour, minute)
        cutoff_date = datetime(1582, 10, 15)
        if dt < cutoff_date:
            print("无效的日期。日期应在 1582 年 10 月 15 日之后。")
            return None

        return dt
    except ValueError:
        print("无效的日期或时间。请检查输入的年月日和时间。")
        return None
