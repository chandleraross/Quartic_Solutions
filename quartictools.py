# Author: Chandler Ross | Quartic Solutions

#This is a module with miscelanous python tools for various quartic solution needs

# Imports
from datetime import datetime, date
import time

#Functions
def read_me(funct_list = False):
    pass


# Time Delay
def delay_until(start_time):
    '''
    This functions waits until the time and date called in order to resume the script. Assumes that the time set is in the future.
    :param start_time: The time and date you want to delay until in mm/dd/yy hh:mm format, example: '09/19/22 13:55'; String
    :return:
    '''

    # Get the current time
    now = datetime.now()

    # Convert the start time to a time object
    datetime_object = datetime.strptime(start_time, '%m/%d/%y %H:%M')

    # Get the date of now
    now_date = date(now.year, now.month, now.day)

    # Get the date of the start time
    start_date = date(datetime_object.year, datetime_object.month, datetime_object.day)

    # Get the difference between the start_date and the now_date
    date_delta = start_date - now_date

    if(date_delta.days > 1):
        #Calculate th amount of time until the end of the day
        # Get the time of day for the start time
        now_hour = now.hour
        now_minute = now.minute

        # time until end of day
        hours_left = (23 - now_hour) * 60
        minutes_left = 59 - now_minute
        minutes_of_day = hours_left + minutes_left

        #Get the amount of time for the start_time
        start_hour = datetime_object.hour * 60
        start_minute = datetime_object.minute
        start_sum = start_minute + start_hour

        # Get the number of days
        day_minutes = (date_delta.days - 1) * 24 * 60

        wait_time = minutes_of_day + start_sum + day_minutes
        print(f"Waiting for {wait_time} minutes")
        time.sleep(wait_time * 60)


    elif(date_delta.days > 0):
        # Calculate th amount of time until the end of the day
        # Get the time of day for the start time
        now_hour = now.hour
        now_minute = now.minute

        # time until end of day
        hours_left = (23 - now_hour) * 60
        minutes_left = 59 - now_minute
        minutes_of_day = hours_left + minutes_left

        # Get the amount of time for the start_time
        start_hour = datetime_object.hour * 60
        start_minute = datetime_object.minute
        start_sum = start_minute + start_hour

        # Get the wait time
        wait_time = minutes_of_day + start_sum
        print(f"Waiting for {wait_time} minutes")
        time.sleep(wait_time * 60)


    else:
        # Get the time of day for the now
        now_hour = now.hour
        now_minute = now.minute

        # Get the time of day for the start time
        start_hour = datetime_object.hour
        start_minute = datetime_object.minute

        delta_hour = start_hour - now_hour
        delta_minute = start_minute - now_minute

        wait_time = (delta_hour * 60) + delta_minute
        print(f"Waiting for {wait_time} minutes")
        time.sleep(wait_time * 60)





