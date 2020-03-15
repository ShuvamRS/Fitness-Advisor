import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import json
import time
from datetime import datetime, timedelta
from collections import defaultdict
from database import Database
from flask import Flask, render_template, request, redirect
import sqlite3
import redis
from rq import Queue

SCOPES = (
    'https://www.googleapis.com/auth/fitness.activity.read',
    'https://www.googleapis.com/auth/fitness.body.read',
    'https://www.googleapis.com/auth/fitness.location.read'
    )

DATA_SOURCE = {
    'Weight_Kg': 'derived:com.google.weight:com.google.android.gms:merge_weight',
    'Height_Meters': 'derived:com.google.height:com.google.android.gms:merge_height',
    'Calories_Expended': 'derived:com.google.calories.expended:com.google.android.gms:merge_calories_expended',
    'Calories_Activity': 'derived:com.google.calories.expended:com.google.android.gms:from_activities',
    'Active_Minutes': 'derived:com.google.active_minutes:com.google.android.gms:merge_active_minutes',
    'Steps': 'derived:com.google.step_count.delta:com.google.android.gms:estimated_steps',
    'Distance_Meters': 'derived:com.google.distance.delta:com.google.android.gms:merge_distance_delta',
    'Activity_Segments': 'derived:com.google.activity.segment:com.google.android.gms:merge_activity_segments',
    }


def authorization():
    '''
    Every request to Fitness API must incude an authorization token.
    Google displays a consent screen and if the user approves,
    credentials get saved for future access.
    '''

    credentials = None

    # tokens.pickle stores user's access and refresh tokens
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            credentials = pickle.load(token)


    # If there are no (valid) credentials available, let the user log in.
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            credentials = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(credentials, token)

    return credentials


def retrieve_data(credentials, dataSourceId, datasetId):
    fitness_service = build('fitness', 'v1', credentials=credentials)
    return fitness_service.users().dataSources().datasets().get(userId='me', dataSourceId=dataSourceId, datasetId=datasetId).execute()


def generate_datasetId(last_access):
    '''
    Generates a time frame for requesting data.
    Return format: "startTimeInNanoSeconds-endTimeInNanoSeconds"
    '''
    now = datetime.today()
    
    if last_access == None:
        date_init = (now - timedelta(days=31)).date() # If database does not exist, fetch data for the past 31 days.
    else:
        date_init = datetime.strptime(last_access, "%Y-%m-%d").date()

    start = int(time.mktime(date_init.timetuple())*1000000000) # Convert initial date to nanoseconds
    end = int(time.mktime(now.timetuple())*1000000000) # Convert current day's date+time to nanoseconds
    
    return f"{start}-{end}"

def nanoseconds(nanotime):
    # Converts namoseconds to date-time string
    dt = datetime.fromtimestamp(nanotime // 1000000000)
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def update_db(db, credentials, datasetId):
    # Add data to Activity table
    dataset_list = []
    for datasource in ("Activity_Segments", "Calories_Activity"):
        dataset_list.append(retrieve_data(credentials, DATA_SOURCE[datasource], datasetId))

    for d1, d2 in zip(*[dataset_list[i]["point"] for i in range(2)]):
        try:
            db.insert(tableName="Activity", StartTime=d1['startTimeNanos'], endTime=d1['endTimeNanos'], Calories_Activity=d2['value'][0]['fpVal'], AID=d1['value'][0]['intVal'])
        except:
            db.update(tableName="Activity", timeFilter="StartTime", time=d1['startTimeNanos'], endTime=d1['endTimeNanos'], Calories_Activity=d2['value'][0]['fpVal'], AID=d1['value'][0]['intVal'])
    

    # Add data to Fitness table
    dataset_dict = dict()

    for dataType in ("Calories_Expended","Distance_Meters", "Active_Minutes", "Steps", "Weight_Kg"):
        dataset_dict[dataType] = retrieve_data(credentials, DATA_SOURCE[dataType], datasetId)

    
    for dataType,dataset in dataset_dict.items():
        aggregate_dict = defaultdict(int) # Used for storing sum of data collected throughout a day
        for d in dataset['point']:
            try:
                value = d['value'][0]['fpVal'] # fpVal == floating point value
            except KeyError:
                value = d['value'][0]['intVal']
                
            aggregate_dict[nanoseconds(int(d["startTimeNanos"])).split()[0]] += value # aggregate_dict has dates as keys
        
        for k,v in aggregate_dict.items():
            kwargs = {dataType: v}
            try:
                db.insert(tableName="Fitness", Date=k, **kwargs)
            except:
                db.update(tableName="Fitness", time=k, **kwargs)


def main():
    credentials = authorization()
    with Database("records.db") as db:
        try:
            db.createTables()
            db.updateActivityReference()
            last_access = None
        
        except:
            last_access = db.getPrevAccessDate()

        datasetId = generate_datasetId(last_access)
        update_db(db, credentials, datasetId)

app = Flask(__name__)
r = redis.Redis()
q = Queue(connection=r)
        
@app.route('/', methods=['POST', 'GET'])
def profile():
    if (request.method == 'POST'):
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        dob = request.form['dob']
        gender = request.form['gender']
        height = request.form['height']
        tarweight = request.form['tarweight']
        
        curWeight = request.form['curWeight']
        calories = request.form['calories']
        targetPeriod = request.form['targetPeriod']
        
        
        #Date = '2020-03-09'
        Date = str(datetime.today().date())
        # targetPeriod = '5 Months'
        # cal_in = '600'
        # cal_burn = '500'
        
        try:
            db = sqlite3.connect('records.db')
            cursor = db.cursor()
            
            
            cursor.execute("INSERT INTO User (Date, First_Name, Last_Name, DOB, Gender, Height_Meters, Target_Weight_Kg, Target_Period) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (Date, firstname, lastname, dob, gender, height, tarweight, targetPeriod))
            
            query = """UPDATE Fitness SET Calories_Consumed = ?, Weight_Kg = ? WHERE Date = ?"""
            cursor.execute(query, (calories, curWeight, Date))
            
            db.commit()
            return redirect('/')
        except:
            return 'There was an issue'
            
    else:
        return render_template('profile.html')

if (__name__ == "__main__"):
    main()
    app.run(debug = True)