from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import sqlite3
from datetime import datetime, date, timedelta
import time
from collections import defaultdict
import re
from weather import Weather

def nanoseconds(nanotime):
    # Converts namoseconds to date-time string
    dt = datetime.fromtimestamp(nanotime // 1000000000)
    return dt.strftime('%Y-%m-%d %H:%M:%S')

class WeightLossCalculator:
    def __init__(self):
        self.element_dict = {
                    'gender': '#gender',
                        'age': '//*[@id="age"]',
                        'height_meter': '//*[@id="height_meter"]',
                        'height_cm': '//*[@id="height_cm"]',
                        'current_weight_kg': '//*[@id="metric_weight"]/input',
                        'target_weight_kg': '//*[@id="weight_to_lose_kilos"]',
                        'target_period': '//*[@id="weight_to_lose_days"]',
                        'daily_activity': '//*[@id="daily_activity"]'
                }

        self.activity_level = {
                    "neglegible": "Desk job, little to no exercise",
                        "light": "Light activity (exercise 1-3 times per week)",
                        "moderate": "Moderate activity (exercise 3-5 times per week)",
                        "high": "High activity (exercise 6-7 times per week)"
                }

    def calculate(self, driver, fields):
        driver.get('http://www.bmi-calculator.net/weight-loss-calculator/')
        driver.find_element_by_xpath('//*[@id="mode_switch"]').click()  # switch to Metric system
        for k, v in fields.items():
            try:
                driver.find_element_by_xpath(self.element_dict[k]).send_keys(str(v))
            except:
                driver.find_element_by_css_selector(self.element_dict[k]).send_keys(str(v))

        # Click button to get calculated results
        driver.find_element_by_xpath('//*[@id="content"]/form/table/tbody/tr[9]/td/input[3]').click()
        # Return the paragraph result
        return driver.find_element_by_xpath('/html/body/div[1]/div[2]/div[2]/p').text


    def get_user_data(self, cur):
        fields = ("DOB", "Gender", "Height_meters", "Target_weight_kg", "Target_period")
        # Query recently added data for each column in the table
        user_info = []
        for field in fields:
            cur.execute(\
                            f'''
                                SELECT {field}
                                FROM User
                                Where Date == (SELECT MAX(Date) FROM User WHERE {field} IS NOT NULL)
                        ''')
            user_info.append(cur.fetchone()[0])

        # Get age from Date of Birth
        age = date.today().year - datetime.strptime(user_info[0], "%Y-%m-%d").year
        gender =user_info[1]
        # Convert height into meters and centimeters
        m = int(user_info[2])
        cm = int(round(user_info[2] % m, 2)*100)


        # Get current weight from Fitness table
        cur.execute(\
                    f'''
                        SELECT Weight_Kg
                        FROM Fitness
                        WHERE Date == (
                        SELECT MAX(Date)
                        FROM Fitness
                        WHERE Weight_Kg IS NOT NULL
                        );
                ''')

        current_weight = cur.fetchone()[0]

        # Get activity level based on exercise frequencies (excludes outdoor walking).
        activitySet = set()
        dateTime_last_week = (datetime.today() - timedelta(days=7)).date()
        dateTime_last_week_nanos = int(time.mktime(dateTime_last_week.timetuple())*1000000000)

        cur.execute(\
                    f'''
                        SELECT startTime
                        FROM Activity NATURAL JOIN ActivityReference
                        WHERE StartTime >= {str(dateTime_last_week_nanos)} AND Activity_Type != "Walking*";
                ''')
        for elem in cur.fetchall():
            activitySet.add(nanoseconds(elem[0]).split()[0])

        weeklyActivityFrequency = len(activitySet)

        if weeklyActivityFrequency == 0:
            daily_activity = self.activity_level["neglegible"]
        elif weeklyActivityFrequency < 3:
            daily_activity = self.activity_level["light"]
        elif weeklyActivityFrequency < 6:
            daily_activity = self.activity_level["moderate"]
        else:
            daily_activity = self.activity_level["high"]

        return dict(gender=gender, age=age, height_meter=m, height_cm=cm, current_weight_kg=int(current_weight), target_weight_kg=int(user_info[3]), target_period=user_info[4], daily_activity=daily_activity)


def activity_average(cur, period=7):
    # For each activity, this function returns average workout time and average calories burned
    # for a time period specified(in days).
    calories_dict = defaultdict(lambda: defaultdict(int))
    workout_time_dict = defaultdict(lambda: defaultdict(int))
    dateTime = (datetime.today() - timedelta(days=period)).date()
    dateTimeNanos = int(time.mktime(dateTime.timetuple())*1000000000)

    cur.execute(
            f'''
                SELECT *
                FROM Activity NATURAL JOIN ActivityReference
                WHERE StartTime >= {dateTimeNanos};
        ''')

    datetimeFormat = '%Y-%m-%d %H:%M:%S'
    for record in cur.fetchall():
        date = nanoseconds(record[0]).split()[0]
        timeDiff = datetime.strptime(nanoseconds(record[1]), datetimeFormat) - datetime.strptime(nanoseconds(record[0]), datetimeFormat)
        calories_dict[record[4]][date] += record[2]
        workout_time_dict[record[4]][date] += timeDiff.seconds

    average_time_dict = {}
    for k,v in workout_time_dict.items():
        average_time_dict[k] = sum(v.values()) // len(workout_time_dict[k])

    average_calories_dict = {}
    for k,v in calories_dict.items():
        average_calories_dict[k] = sum(v.values()) // len(calories_dict[k])

    return average_time_dict, average_calories_dict

def get_contextual_recommendation():
    outdoor_flag = True
    w = Weather("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")

    forecast = w.three_hours_forecast()
    if not (forecast["will_have_rain"] and forecast["will_have_fog"] and forecast["will_have_snow"]):
        outdoor_flag = False

    cur_weather = w.current_weather()
    dateTime = str(datetime.today()).split('.')[0]
    if (dateTime < cur_weather["sunrise_time"] or dateTime > cur_weather["sunset_time"]):
        outdoor_flag = False

    return outdoor_flag


def collaborative_filtering(recommended_cal_exp, outdoor_flag):
    # Return a dictionary formatted exactly like the following.
    return {"Exercise_Type": {"calories": 0, "time": 0}}


def get_personalized_recommendation(cur, avg_time_dict, avg_cal_exp_dict, cal_exp_goal, cal_in_goal, curr_cal_exp, curr_cal_in, outdoor_flag):
    recommended_daily_cal = cal_exp_goal + cal_in_goal

    # Get average calories consumed for 1 week
    prevDate = (datetime.today() - timedelta(days=7)).date()
    cur.execute(\
            f'''
                SELECT AVG(Calories_Consumed)
                FROM Fitness
                WHERE Date >= {prevDate}
                '''
        )
    avg_cal_in = cur.fetchone()[0]

    if avg_cal_in == None:
        avg_cal_in = 0

    # Adjust the suggested calories expenditure amount based on average calories consumed.
    cal_in_diff = cal_in_goal - avg_cal_in
    recommended_cal_exp = cal_exp_goal # Default value if data for calories consumed is not available.
    if cal_in_diff > 0: # If user consumes less calories than what is suggested, reduce suggested calories expenditure amount.
        recommended_cal_exp -= cal_in_diff
    elif cal_in_diff < 0: # If user consumes more calories than what is suggested, increase suggested calories expenditure amount.
        recommended_cal_exp += cal_in_diff

    # More outdoor activities need to be added from https://developers.google.com/fit/rest/v1/reference/activity-types
    googleFit_outdoorActivities = ["Biking", "Walking*", "Walking (fitness)"]

    # Exclude outdoor activities from the list if weather conditions are not suitable.
    if outdoor_flag == False:
        for activity in googleFit_outdoorActivities:
            try:
                avg_cal_exp_dict.pop(activity)
            except KeyError:
                pass

    if len(avg_cal_exp_dict) == 0:
        return collaborative_filtering(recommended_cal_exp, outdoor_flag)

    avg_cal_exp_list = sorted(avg_cal_exp_dict.items(), key=lambda x:x[1])
    recomended_activities = defaultdict(lambda: defaultdict(int))

    recommended_cal_exp = 5000

    while recommended_cal_exp > 0:
        for activity in avg_cal_exp_list:
            if (recommended_cal_exp - activity[1]) < 0:
                recomended_activities[activity[0]]["calories"] += recommended_cal_exp
                recomended_activities[activity[0]]["time"] += (avg_time_dict[activity[0]] // activity[1]) * recommended_cal_exp
                recommended_cal_exp = 0
                break
            recomended_activities[activity[0]]["calories"] += activity[1]
            recomended_activities[activity[0]]["time"] += avg_time_dict[activity[0]]
            recommended_cal_exp -= activity[1]

    return recomended_activities
    

def get_recommendation(status=None):
    DB_file = "records.db"
    pattern_calories_exp = r"about (\d+) calories"
    pattern_calories_in = r"consume (\d+) calories"

    conn = sqlite3.connect(DB_file)
    cursor = conn.cursor()

    if status == "NEW": # If user updates Current_Weight/Target_Weight/Target_Period
        # Execute Selenium Chrome Webdriver in silent mode
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        driver = webdriver.Chrome(options=chrome_options)
        calculator = WeightLossCalculator()
        user_data = calculator.get_user_data(cursor)
        suggestion_msg = calculator.calculate(driver, fields=user_data)
        try:
            cal_exp = re.search(pattern_calories_exp, suggestion_msg).group(1)
            cal_in = re.search(pattern_calories_in, suggestion_msg).group(1)


            cursor.execute(\
                            f'''
                                INSERT INTO USER (Date, Calories_Intake_Goal, Calories_Burn_Goal)
                                VALUES (?, ?, ?)
                                ''', (str(datetime.today().date()), int(cal_in), int(cal_exp)))

        except sqlite3.IntegrityError:
            cursor.execute(\
                            f'''
                                UPDATE User
                                SET Calories_Intake_Goal = ?,
                                Calories_Burn_Goal = ?
                                WHERE Date = ?;
                                ''', (int(cal_in), int(cal_exp), str(datetime.today().date())))
            conn.commit()

        except AttributeError:
            pass


    cursor.execute(\
            '''
		SELECT Calories_Burn_Goal, Calories_Intake_Goal
		FROM User
		WHERE Date >= (
			SELECT DATE
			FROM User
			WHERE Calories_Intake_Goal IS NOT NULL);
		''')

    cal_exp_goal, cal_in_goal = cursor.fetchone()
    avg_time_dict, avg_cal_exp_dict = activity_average(cur=cursor)

    cursor.execute(\
            '''
		SELECT Calories_Expended, Calories_Consumed
		FROM Fitness
		WHERE Date = ?;
		''', (str(datetime.today().date()),))

    curr_cal_exp, curr_cal_in = cursor.fetchone()

    outdoor_flag = get_contextual_recommendation()
    recommendation = get_personalized_recommendation(cursor, avg_time_dict, avg_cal_exp_dict, cal_exp_goal, cal_in_goal, curr_cal_exp, curr_cal_in, outdoor_flag)
    conn.close()
    return recommendation