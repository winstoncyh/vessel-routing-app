import win32com.client
import os
import datetime
import pandas as pd
import difflib
import re
from math import cos, asin, sqrt

def get_outlook_outbox_folder():
    outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
    inbox_subfolder = outlook.Folders('Inbox (Subfolder)')
    outbox_folder = inbox_subfolder.folders('Outbox')
    return outbox_folder
    outlook.quit()
    outlook = None

def get_outlook_marex_folder():
    outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
    inbox_subfolder = outlook.Folders('Inbox (Subfolder)')
    winston_folder = inbox_subfolder.folders('Winston')
    reports_folder = winston_folder.folders('I2. REPORTS')
    marex_folder = reports_folder.folders('Marex')
    return marex_folder
    outlook.quit()
    outlook = None

def get_outlook_gasolineshipbroking_folder():
    outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
    gasoline_shipbroking_inbox= outlook.Folders('*MISC Gasoline Shiptracking')
    inbox = gasoline_shipbroking_inbox.folders('Inbox')
    # winston_folder = inbox_subfolder.folders('Winston')
    # reports_folder = winston_folder.folders('I2. REPORTS')
    # marex_folder = reports_folder.folders('Marex')
    return inbox
    outlook.quit()
    outlook = None

def get_outlook_gasolineshipbroking_brokerreports_folder():
    outlook = win32com.client.Dispatch("Outlook.Application").GetNamespace("MAPI")
    gasoline_shipbroking_inbox= outlook.Folders('*MISC Gasoline Shiptracking')
    broker_reports_folder = gasoline_shipbroking_inbox.folders('Broker Reports')

    # winston_folder = inbox_subfolder.folders('Winston')
    # reports_folder = winston_folder.folders('I2. REPORTS')
    # marex_folder = reports_folder.folders('Marex')
    return broker_reports_folder
    outlook.quit()
    outlook = None




def create_sql_value_parameterstring(intNumofParameters):
    ValueFieldStr = 'Values('
    for i in range(1 , intNumofParameters+1):
        if i == intNumofParameters:
            ValueFieldStr = ValueFieldStr + '?)'
        elif i < intNumofParameters:
            ValueFieldStr = ValueFieldStr + '?,'
    return ValueFieldStr


def create_sql_questionmark_parameterstring(intNumofParameters):
    ValueFieldStr = '('
    for i in range(1 , intNumofParameters+1):
        if i == intNumofParameters:
            ValueFieldStr = ValueFieldStr + '?)'
        elif i < intNumofParameters:
            ValueFieldStr = ValueFieldStr + '?,'
    return ValueFieldStr

def create_send_outlook_email(str_to_list,str_mailsubject,str_mailbodytext,attachment=None):
    import win32com.client as win32
    import time
    outlook = win32.Dispatch('outlook.application')
    mail = outlook.CreateItem(0)
    mail.To = str_to_list
    mail.Subject = str_mailsubject
    mail.Body = str_mailbodytext
    # To attach a file to the email (optional):
    if attachment != None:
        mail.Attachments.Add(attachment)
    mail.Send()
    time.sleep(30)
    outlook.Quit()
    outlook = None


def get_calling_script_directory_path(sys_object):
    if getattr(sys_object, 'frozen', False):
        # this application is frozen, program running as an exe
        scriptfilepath = os.path.dirname(sys_object.executable)
    else:
        # is application is unfrozen ie program running from python console or IDE
        scriptfilepath = os.path.dirname(os.path.realpath(__file__))
    return scriptfilepath

def assure_path_exists(path):
    dir = os.path.dirname(path)
    if not os.path.exists(dir):
        os.makedirs(dir)


def print_to_log_w_timestamp(logfilepath, strlog):
    db_write_datetime = datetime.datetime.now()
    db_write_datetimestamp_str = str(db_write_datetime.year) + '-' + str(db_write_datetime.month) + '-' + \
                                 str(db_write_datetime.day) + '_H' + str(db_write_datetime.hour) + '_M' + str(
        db_write_datetime.minute) + '_S' + str(db_write_datetime.second)
    with open(logfilepath, "a") as logfile:
        logfile.write('[' + db_write_datetimestamp_str + ']:' + str(strlog) + '\n')

def get_all_data_from_workbook_in_df_format(workbookFullName):
    xlApp = win32com.client.Dispatch("Excel.Application")
    xlApp.Visible = True
    xlwb = xlApp.Workbooks.Open(workbookFullName)
    df_list =[]
    for ws in xlwb.Worksheets:
        df = pd.read_excel(workbookFullName,sheetname=ws.Name)
        df_list.append(df)

    return df_list

def auto_read_headers_in_df(input_df_list):
    MaxIterationInDF = 100
    IterationLoopCount = 0
    LocationTupleList =[]
    # Find a header row, and use it as a column names list for creation of df to be used to write to sql
    for input_df in input_df_list:
        col_list = input_df.columns
        col_count = len(col_list)
        for index, row in input_df.iterrows():
            if IterationLoopCount < MaxIterationInDF:
                for x in range(0, col_count - 1):
                    rowValue = str(row[x]).upper().strip()
                    string_metric = difflib.SequenceMatcher(None, 'VESSEL', rowValue).ratio()
                    LocationTupleList.append((rowValue,index,x,string_metric))



                IterationLoopCount = IterationLoopCount+1
            else:
                break

        a=0

def normalize_df(input_df):
    input_df = input_df.applymap(str)
    input_df.fillna('')
    return input_df


def cpp_extract_load_date(input_string):
    regex = r'(\d+)\/(\d+)'
    # regex = r'(\w+\s?\w+?\s?\w+?)[\r\n\s]+?([\d,]+)[\r\n\s]+?(JET|UMS|CPP|ULSD|NAP|COND|GO|ALKY|GTL)[\r\n\s]+?([\w\-\/]+|PPT)[\r\n\s]+?([^\r\n]+)[\r\n\s]+?([^\r\n\s]+)[\r\n\s]+?([^\r\n\s]+)[\r\n\s]+?([^\r\n\s]+\s?\w+?)[\r\n\s]+?([^\r\n\s]+)[\r\n\s]+?'

    matches = re.findall(regex, input_string, re.IGNORECASE)
    returned_dt_string =input_string
    if len(matches)>0:
        if len(matches[0]) > 1:
            intMonth = int(matches[0][1])
            intDay = int(matches[0][0])
            intYear = datetime.datetime.now().year
            dt_datetime = datetime.date(intYear, intMonth, intDay)
            str_datetime = datetime.datetime.strftime(dt_datetime, '%d-%b-%y')
            returned_dt_string = str_datetime


    return returned_dt_string


def find_column_index_by_nearest_string(input_df,column_name_matching_string):

    list_of_col_index_to_name = [(i,input_df.columns[i]) for i in range(0,len(input_df.columns.values)-1)]
    df_col_names_index = pd.DataFrame(list_of_col_index_to_name,columns=['ColumnIndex','ColumnName'])
    filtered_df = df_col_names_index[df_col_names_index['ColumnName'].str.contains(column_name_matching_string)]
    column_index_found = filtered_df.iloc[0, 0]
    return column_index_found

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def parse_dates_from_words(input_date_string):
    # E,g, of input to clean would be 05/MID, 06/END, DNR-2018
    # Capture the digits and then the alphabets
    regex = r'([\d]+)([^\d]+)'
    YearNum = datetime.datetime.now().year
    DayNum = 1

    matches = re.findall(regex, input_date_string, re.IGNORECASE)

    if len(matches)==1:
        date_component = matches[0][0]
        if is_number(date_component):
            MonthNumber = date_component

    elif len(matches)==2:
        date_component_1 = matches[0][0]
        date_component_2 = matches[0][1]

        if is_number(date_component_1):
            MonthNumber = date_component_1
            MonthRange = date_component_2 #this would be mid, end or ely
            if 'ELY' in str(MonthRange).upper():
                DayNum =1
            elif 'MID' in str(MonthRange).upper():
                DayNum = 15
            elif 'END' in str(MonthRange).upper():
                DayNum = 30
        input_date_dt = datetime.datetime(YearNum, MonthNumber, DayNum)

    return input_date_dt

    a=0
    return matches

def geo_distance(lat1, lon1, lat2, lon2):
    p = 0.017453292519943295     #Pi/180
    a = 0.5 - cos((lat2 - lat1) * p)/2 + cos(lat1 * p) * cos(lat2 * p) * (1 - cos((lon2 - lon1) * p)) / 2
    return 12742 * asin(sqrt(a))