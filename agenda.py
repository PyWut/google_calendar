"""
Todo: events niet lokaal opslaan want update niet met service
"""


import datetime
import pickle
import os
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from colorama import Fore, Style, init
#initialise colorama
init()

SCOPES = ["https://www.googleapis.com/auth/calendar", "https://www.googleapis.com/auth/tasks"]
INSTRUCTIONS = "Press 0 for getting events\n1 for making an event\n2 to delete an event\n3 to quit"

class Event:
    today = datetime.date.today()
    color = Fore.GREEN

    def __init__(self, name, event_id, date_text):
        self.name = name
        self.event_id = event_id
        self.datetime = datetime.datetime.strptime(date_text, "%Y-%m-%dT%H:%M:%S")
        self.date = self.datetime.date().strftime("%d-%m-%Y")
        self.time = self.datetime.time()
        self.set_color(self.datetime.date())

    def set_color(self, date_obj):
        """
        Change color depending on urgency to make task
        """
        time_delta_days = abs((date_obj - self.today).days)
        if time_delta_days <= 3:
            self.color = Fore.RED
        elif time_delta_days <= 5:
            self.color = Fore.YELLOW

    def print(self):
        print(f"{self.color}You have an activity with the name: {self.name}\non {self.date}, {self.time}{Style.RESET_ALL}\n")
    
class Calendar:
    events_list = []
    calendar_to_check = None
    def __init__(self, token_file):
        if os.path.exists(token_file):
            with open(token_file, "rb") as token:
                creds = pickle.load(token)
        else:
            creds = False
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(token_file, "wb") as token:
                pickle.dump(creds, token)
        self.service = build("calendar", "v3", credentials=creds)
 
    def is_duplicate(self, event_id_to_test):
        for event in self.events_list:
            if event_id_to_test == event.event_id:
                return True
        return False

    def get_events(self, print_event=False):
        # Call the Calendar API
        if self.calendar_to_check is None:
            self.set_calendar_to_check()

        now = datetime.datetime.utcnow()
        target_time = (now - datetime.timedelta(days=1)).isoformat() + "Z" # "Z" indicates UTC time
        print("Getting upcoming events\n")

        events_result = self.service.events().list(calendarId=self.calendar_to_check, timeMin=target_time,
                                            maxResults=10, singleEvents=True,
                                            orderBy="startTime").execute()

        events = events_result.get("items", [])
        self.events_list = []
        if events:
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                event_summary = start, event["summary"]
                if not "T" in start:
                    start += "T00:00:00"
                if "+" in start:
                    idx = start.find("+")
                    start = start[:idx]

                event_id = event["id"]
                #event_date = f"{event_summary[0][8:10]}-{event_summary[0][5:7]}-{event_summary[0][0:4]}"
                if not self.is_duplicate(event_id):
                    self.events_list.append(Event(name=event_summary[1], event_id=event_id, date_text=start))
        
        if print_event:
            for event in self.events_list:
                event.print()

    def set_calendar_to_check(self):
        calendars = self.service.calendarList().list(pageToken=None).execute()
        for cld in calendars["items"]:
            if cld["summary"].lower() == "school":
                self.calendar_to_check = cld["id"]
                break
        else:
            raise RuntimeError("No calendar found with name school")

    def make_event(self):
        if self.calendar_to_check is None:
            self.set_calendar_to_check()
            
        name_activity = input("The name of your activity: ")
        date = input("The date of the event (DD-MM-YYYY): ")
        try:
            date = datetime.datetime.strptime(date, "%d-%m-%Y").strftime("%Y-%m-%d")
            event_info = {
                "summary": name_activity,
                "start": {"date": date, "timeZone": "Europe/Brussels"},
                "end": {"date": date, "timeZone": "Europe/Brussels"},
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 60 * 8},
                    ],
                }
            }
        
            print("\nMaking the event")
            self.service.events().insert(calendarId=self.calendar_to_check, sendNotifications=True, body=event_info).execute()
            print("Event has been made\n")
        except Exception as e:
            print(str(e))
        
    def remove_event(self):
        self.get_events()
        print("Please type one of the following names of events to delete: ")
        for event in self.events_list:
            print(f"- {event.name}")
        try:
            inp = str(input("\nName of the event: ")).lower()
            for event in self.events_list:
                if inp.strip().lower() == event.name.lower():
                    self.service.events().delete(calendarId=self.calendar_to_check, eventId=event.event_id, sendNotifications=False).execute()
                    self.events_list.remove(event)
                    print(f"Event with the name {event.name} has been deleted\n")
                    break
        except ValueError:
            pass


if __name__ == "__main__":
    calendar = Calendar(token_file="token.pickle")
    print("Welcome to Google Calendar Manager\n\n")
    while True:
        try:
            print(INSTRUCTIONS)
            inp = int(input("\nYour input: "))
            print("\n")
            if inp == 0:
                calendar.get_events(print_event=True)
            elif inp == 1:
                calendar.make_event()
            elif inp == 2:
                calendar.remove_event()
            elif inp == 3:
                break
            else:
                print("Please press 0, 1, 2 or 3")
        except ValueError:
            print("Please press 0, 1, 2 or 3\n")
