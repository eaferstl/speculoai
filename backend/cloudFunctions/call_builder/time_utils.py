# time_utils.py

import datetime
import pytz

def get_day_time(timezone_str):
    timezone = pytz.timezone(timezone_str)
    now = datetime.datetime.now(timezone)
    part_of_day = "morning" if now.hour < 12 else "afternoon"
    day_of_week = now.strftime('%A')
    return day_of_week, part_of_day