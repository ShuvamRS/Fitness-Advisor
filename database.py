import sqlite3
import requests
from bs4 import BeautifulSoup


SQL_COMMANDS = {
"insert":   '''
            INSERT INTO {tableName} {cols}
            VALUES {vals};
            ''',

"update":   '''
            UPDATE {tableName}
            SET "{col}" = "{val}"
            WHERE {timeFilter} = "{time}"
            ''',

"access_date":
            '''
            SELECT MAX(Date)
            FROM Fitness
            ''',
            
"create":[  '''
            CREATE TABLE ActivityReference
            (
                AID INT PRIMARY KEY,
                Activity_Type TEXT
            );
            ''',

            '''
            CREATE TABLE Fitness
            (
                Date TEXT PRIMARY KEY,
                Distance_Meters REAL,
                Active_Minutes INTEGER,
                Steps INTEGER,
                Calories_Expended REAL,
                Calories_Consumed REAL,
                Weight_Kg REAL,
                CHECK (
                        NOT (Weight_Kg IS NULL AND Calories_Consumed IS NULL AND Calories_Expended IS NULL AND
                        Distance_Meters IS NULL AND Active_Minutes IS NULL AND Steps IS NULL)
                    )
            );
            ''',

            '''
            CREATE TABLE Activity
                (
                    StartTime INT PRIMARY KEY,
                    EndTime INT,
                    Calories_Activity REAL,
                    AID INT,
                    FOREIGN KEY (AID) REFERENCES Activity(AID) ON UPDATE CASCADE ON DELETE SET NULL
                );
            ''',

            '''
            CREATE TABLE User
                (
                    Date TEXT PRIMARY KEY,
                    First_Name TEXT,
                    Last_Name TEXT,
                    DOB TEXT,
                    Gender TEXT,
                    Height_Meters REAL,
                    Target_Weight_Kg INT,
                    Target_Period TEXT,
                    Calories_Intake_Goal INT,
                    Calories_Burn_Goal INT
                );
            '''
        ]
}



class Database:
    def __init__(self, fileName):
        self.conn = sqlite3.connect(fileName)
        self.cur = self.conn.cursor()


    def __enter__(self):
        return self


    def __exit__(self, ext_type, exc_value, traceback):
        self.cur.close()
        
        if isinstance(exc_value, Exception): self.conn.rollback()
        else: self.conn.commit()
        
        self.conn.close()

    def insert(self, tableName, **kwargs):
        self.cur.execute(
            SQL_COMMANDS["insert"].format(tableName=tableName, cols=tuple(kwargs.keys()), vals=tuple(kwargs.values()))
            )

    def update(self, tableName, time, timeFilter="Date", **kwargs):
        for col, val in kwargs.items():
            self.cur.execute(SQL_COMMANDS["update"].format(tableName=tableName, col=col, val=val, timeFilter=timeFilter, time=time))

    def updateActivityReference(self):
        url = "https://developers.google.com/fit/rest/v1/reference/activity-types#activity_type_values"
        page = requests.get(url)
        soup = BeautifulSoup(page.content, "html.parser")

        container = soup.select("td")

        self.cur.execute("DELETE FROM ActivityReference")
        for i in range(1, len(container), 2):
            self.insert(tableName="ActivityReference", AID=int(container[i].text), Activity_Type=container[i-1].text)

    def getPrevAccessDate(self):
        self.cur.execute(SQL_COMMANDS["access_date"])
        return self.cur.fetchone()[0]

    def createTables(self):
        for command in SQL_COMMANDS["create"]:
            self.cur.execute(command)