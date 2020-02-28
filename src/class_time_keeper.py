import time

class timekeeper():
    def __init__(self):

        self.list_of_event_execution_times_tuple =[]


    def start_timing_event(self,**kwargs):
        new_event_name = kwargs.get('event_name',None)
        new_event_start_time = time.time()
        self.list_of_event_execution_times_tuple.append((new_event_name,new_event_start_time))
        print(new_event_name + ' execution started')

    def stop_timing_event(self,**kwargs):
        existing_event_name = kwargs.get('event_name', None)
        end = time.time()
        for event in self.list_of_event_execution_times_tuple:
            if event[0] == existing_event_name:
                start = event[1]
                hours, rem = divmod(end - start, 3600)
                minutes, seconds = divmod(rem, 60)
                print(existing_event_name + " completed in {:0>2} HOURS :{:0>2} MINUTES :{:05.2f} SECONDS".format(int(hours), int(minutes), seconds))
