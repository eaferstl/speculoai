import datetime
import pytz
import json

def calculate_next_morning(request):
    request_json = request.get_json()
    current_time_str = request_json['current_time']
    timezone_str = request_json['timezone']
    
    timezone = pytz.timezone(timezone_str)
    current_time = datetime.datetime.strptime(current_time_str, "%Y-%m-%dT%H:%M:%S.%fZ")
    current_time = current_time.astimezone(timezone)
    
    # Calculate the next 9 AM
    next_morning = (current_time + datetime.timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    if current_time.hour >= 9:
        next_morning = next_morning + datetime.timedelta(days=1)
    
    time_difference = (next_morning - current_time).total_seconds()
    
    return json.dumps({'next_morning_seconds': int(time_difference)})