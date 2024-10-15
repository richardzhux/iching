import sxtwl, random, time
from datetime import datetime

# Mapping of Heavenly Stems and Earthly Branches to Five Elements (五行)
five_elements = {
    '甲': '阳木', '乙': '阴木',
    '丙': '阳火', '丁': '阴火',
    '戊': '阳土', '己': '阴土',
    '庚': '阳金', '辛': '阴金',
    '壬': '阳水', '癸': '阴水',
    '子': '阳水', '丑': '阴土',
    '寅': '阳木', '卯': '阴木',
    '辰': '阳土', '巳': '阴火',
    '午': '阳火', '未': '阴土',
    '申': '阳金', '酉': '阴金',
    '戌': '阳土', '亥': '阴水'
}

# Heavenly Stems and Earthly Branches
Gan = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
Zhi = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]

# Function to get the current time with timezone info
def get_current_time():
    local_tz = time.tzname
    now = datetime.now()
    utc_offset = time.strftime('%z')
    dst = "DST" if time.daylight and time.localtime().tm_isdst > 0 else "None"
    formatted_time = now.strftime(f"%Y.%m.%d %H:%M GMT {utc_offset[:3]}:{utc_offset[3:]} ({dst})")
    return formatted_time

# Get the Bazi (Four Pillars) and their corresponding Five Elements
def get_bazi_and_elements(year, month, day, hour):
    # Get the solar day
    solar_day = sxtwl.fromSolar(year, month, day)
    
    # Get Heavenly Stem and Earthly Branch for Year, Month, Day, and Hour
    year_gz = solar_day.getYearGZ()
    month_gz = solar_day.getMonthGZ()
    day_gz = solar_day.getDayGZ()
    hour_gz = solar_day.getHourGZ(hour)
    
    # Map the Heavenly Stem and Earthly Branch to Five Elements
    year_element = five_elements[Gan[year_gz.tg]] + " " + five_elements[Zhi[year_gz.dz]]
    month_element = five_elements[Gan[month_gz.tg]] + " " + five_elements[Zhi[month_gz.dz]]
    day_element = five_elements[Gan[day_gz.tg]] + " " + five_elements[Zhi[day_gz.dz]]
    hour_element = five_elements[Gan[hour_gz.tg]] + " " + five_elements[Zhi[hour_gz.dz]]
    
    # Format the Bazi output
    bazi_output = f"{Gan[year_gz.tg]}{Zhi[year_gz.dz]}年 {Gan[month_gz.tg]}{Zhi[month_gz.dz]}月 {Gan[day_gz.tg]}{Zhi[day_gz.dz]}日 {Gan[hour_gz.tg]}{Zhi[hour_gz.dz]}时"
    
    # Format the Five Elements output
    elements_output = f"{year_element}年 {month_element}月 {day_element}日 {hour_element}时"
    
    return bazi_output, elements_output

# Example usage
def main():
    print("\nPlease think carefully about what you hope to learn......")
    time.sleep(random.uniform(0, 3))   # 提供情绪价值
    print("Now let me think!\n") 
    time.sleep(random.uniform(3, 5)) 
        
    # Get the current time
    formatted_time = get_current_time()
    
    # Get the current date and time
    now = datetime.now()
    year = now.year
    month = now.month
    day = now.day
    hour = now.hour  # Use 24-hour format for time
    
    # Get the Bazi and Five Elements
    bazi_output, elements_output = get_bazi_and_elements(year, month, day, hour)
    
    # Print the final output
    print(formatted_time)
    print(bazi_output)
    print(elements_output)


def mainforinput(formatted_time):

    # Extract the year, month, day, and hour from the user-provided time
    year = formatted_time.year
    month = formatted_time.month
    day = formatted_time.day
    hour = formatted_time.hour  # Use 24-hour format for time
    
    # Get the Bazi and Five Elements based on the provided time
    bazi_output, elements_output = get_bazi_and_elements(year, month, day, hour)
    
    # Print the final output
    print(formatted_time.strftime("%Y.%m.%d %H:%M"))
    print(bazi_output)
    print(elements_output)

