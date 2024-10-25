import sxtwl, random, time
from datetime import datetime

class BaZiCalculator:
    """Calculates BaZi and Five Elements based on a given datetime."""

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

    Gan = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
    Zhi = ["子", "丑", "寅", "卯", "辰", "巳",
           "午", "未", "申", "酉", "戌", "亥"]

    def __init__(self, datetime_obj):
        self.datetime_obj = datetime_obj

    def calculate_bazi(self):
        year = self.datetime_obj.year
        month = self.datetime_obj.month
        day = self.datetime_obj.day
        hour = self.datetime_obj.hour

        solar_day = sxtwl.fromSolar(year, month, day)

        year_gz = solar_day.getYearGZ()
        month_gz = solar_day.getMonthGZ()
        day_gz = solar_day.getDayGZ()
        hour_gz = solar_day.getHourGZ(hour)

        bazi_output = f"{self.Gan[year_gz.tg]}{self.Zhi[year_gz.dz]}年 " \
                      f"{self.Gan[month_gz.tg]}{self.Zhi[month_gz.dz]}月 " \
                      f"{self.Gan[day_gz.tg]}{self.Zhi[day_gz.dz]}日 " \
                      f"{self.Gan[hour_gz.tg]}{self.Zhi[hour_gz.dz]}时"

        elements_output = f"{self.five_elements[self.Gan[year_gz.tg]]} {self.five_elements[self.Zhi[year_gz.dz]]}年 " \
                          f"{self.five_elements[self.Gan[month_gz.tg]]} {self.five_elements[self.Zhi[month_gz.dz]]}月 " \
                          f"{self.five_elements[self.Gan[day_gz.tg]]} {self.five_elements[self.Zhi[day_gz.dz]]}日 " \
                          f"{self.five_elements[self.Gan[hour_gz.tg]]} {self.five_elements[self.Zhi[hour_gz.dz]]}时"

        return bazi_output, elements_output
