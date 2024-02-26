import sqlite3
from typing import List, Dict, Union
import pandas as pd


def create_sql_table_from_excel(excel_file_path, table_name, sql_path):
    conn = sqlite3.connect(sql_path)
    df = pd.read_excel(excel_file_path)
    df.to_sql(table_name, conn, if_exists='replace', index=False)

    conn.commit()
    conn.close()

def create_blank_sql_table(sql_path: str, table_name: str, column_names: List[str]):
    query = 'CREATE TABLE IF NOT EXISTS ' + table_name + ' ('
    query += ', '.join(column_names)
    query += ');'

    conn = sqlite3.connect(sql_path)
    cursor = conn.cursor()
    cursor.execute(query)
    conn.commit()
    conn.close()

def drop_sql_table(sql_path: str, table_name: str):
    query = f'DROP TABLE IF EXISTS {table_name}'

    conn = sqlite3.connect(sql_path)
    cursor = conn.cursor()
    cursor.execute(query)
    conn.commit()
    conn.close()

# convert passed column to proper datetime format
def df_datetime_type_conversion(df, column_to_convert_name: List[str], time: bool = False) -> pd.DataFrame:
    if not time:
        time_format = "%m/%d/%Y"
    else:
        time_format = "%m/%d/%Y %H:%M:%S"

    try:
        for col in column_to_convert_name:
            df[col] = pd.to_datetime(df[col]).dt.strftime(time_format)

            # take NaN's that may be been added and make then '' string
            df.fillna('', inplace=True)
    except:
        pass

    return df


def sql_tables(sql_path) -> List[str]:
    conn = sqlite3.connect(sql_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    names = cursor.fetchall()

    # Extract table names from the tuples
    names = [table[0] for table in names]

    conn.close()

    return names


def sql_maintable_to_dataframe(sql_path: str, table: str, query: str = None) -> Union[pd.DataFrame, None]:
    if not query:
        query = f"SELECT * FROM {table}"

    try:
        conn = sqlite3.connect(sql_path)
        df = pd.read_sql(query, conn)

        # take NULLs/None(s) from sqlite3 table and make that '' strings for a tableview
        df.fillna('', inplace=True)

        conn.close()
    except:
        df = None

    return df

def sql_subtable_to_dataframe(sql_path: str, allsub_tables: List[str], subtable_name: str,
                              subtable_headers: List[str], query_subtable: str = None) -> Union[pd.DataFrame, None]:
    """
    Note: if providing own query, you'll need to add "maintable_index" as a column to add in order for subtables
    for the maintable to work.  So ALL subtables within the sub table database need to contain a maintable_index column with index values
    that represent each row of the maintable.  That way the program will be able to figure out which sub table data is
    for which row in the main table.

    """
    headers = subtable_headers.copy()

    # check for spaces in the header names and add "' '" to the ends if header has spaces if ' ' not already added
    # this is due to limitations of sqlite3 not being able to handle spaces in column header names
    for index, column in enumerate(headers):
        if ' ' in column:
            if "'" not in column[0] or "'" not in column[-1]:
                headers[index] = "'" + column + "'"

    # maintable_index column header must be added for subtables to work
    if "maintable_index" not in headers:
        headers.insert(0, "maintable_index")

    # if table not found in database, create it
    if subtable_name not in allsub_tables:
        query = 'CREATE TABLE IF NOT EXISTS ' + subtable_name + ' ('
        query += ', '.join(headers)
        query += ');'

        conn = sqlite3.connect(sql_path)
        cursor = conn.cursor()
        cursor.execute(query)
        conn.commit()
        conn.close()

    # default sql query if none provided
    if not query_subtable:
        query_subtable = "SELECT "
        query_subtable += ', '.join(headers)
        query_subtable += f" FROM {subtable_name}"

    try:
        conn = sqlite3.connect(sql_path)
        df = pd.read_sql(query_subtable, conn)
        conn.close()
    except:
        df = None

    return df


def subtable_df_to_list(subtable_df: pd.DataFrame, maintable_df: pd.DataFrame) -> List[List[str]]:
    maintable_index = maintable_df.index.to_list()
    total_subtable_data = []
    for index in maintable_index:
        total_row_data = []
        row_df = subtable_df[subtable_df["maintable_index"] == index]

        # drop the maintable_index, don't want it for displaying on table, this is just a reference for row on the main
        # table it correlates with
        row_df.drop(columns=["maintable_index"], inplace=True)

        # convert all items in dataframe to stringtype before making lists to prevent any issues when sending to qtableview
        row_df = row_df.astype(str)

        for row_index, row in row_df.iterrows():
            total_row_data.append(row.to_list())

        total_subtable_data.append(total_row_data)

    return total_subtable_data


def maintable_df_to_list(maintable_df: pd.DataFrame) -> Union[List[List[str]], None]:
    total_maintable_data = []

    # convert all items in dataframe to stringtype before making lists to prevent any issues when sending to qtableview
    maintable_df = maintable_df.astype(str)

    for row_index, row in maintable_df.iterrows():
        total_maintable_data.append(row.to_list())

    if len(total_maintable_data) != 0:
        return total_maintable_data
    else:
        return None


def dataframe_rows_checkboxed(df: pd.DataFrame, columns_with_checkboxes: List[str]) -> Union[Dict[int, int], None]:
    checkboxed_rows = {}

    columns = df.columns.to_list()

    for i in columns_with_checkboxes:
        col_number = columns.index(i)

        # convert col to str type for universal checking and get the row indexes where the value is 'True' or 'T' or "1"
        df[i] = df[i].astype(str)
        true_indexes = df.index[(df[i] == "1") | (df[i] == "True") | (df[i] == "T")].tolist()

        checkboxed_rows[col_number] = true_indexes

    if len(checkboxed_rows) != 0:
        return checkboxed_rows
    else:
        return None

# COMMENTED OUT CODE PURELY FOR TESTING PURPOSES
# COMMENTED OUT CODE PURELY FOR TESTING PURPOSES
# COMMENTED OUT CODE PURELY FOR TESTING PURPOSES
#create_sql_table_from_excel(r"C:\Users\jxful\OneDrive\Desktop\sql\table_database.xls", "K057", r'C:\Users\jxful\OneDrive\Desktop\sql\maintables.db')


#    table_names = sql_tables(r'C:\Users\jxful\OneDrive\Desktop\sql\maintables.db')
#    #print(table_names)
    
#table = "K057"
#df = sql_maintable_to_dataframe(r'\\NAS3\Users\Jason Fuller\Desktop\tables\maintables.db', table)
#print(df)
#for index, row in df.iterrows():
#    print(row.to_list())
    
#    if df:
#        maintable_df = df_datetime_type_conversion(df, column_to_convert_name=["Date"])
#        checked_rows = dataframe_rows_checkboxed(maintable_df, ['Conformed', "N/A", "Have", "POA"])
#        maintable_data = maintable_df_to_list(maintable_df)
    
#allsub_tables = sql_tables(r"\\NAS3\Users\Jason Fuller\Desktop\tables\subtables.db")
#print(allsub_tables)
#subtable_df = sql_subtable_to_dataframe(r"\\NAS3\Users\Jason Fuller\Desktop\tables\subtables.db", allsub_tables, "K057_subtable", ["'NCR No.'", "Disposition", "Date", "Extra", "Completed"])
#print(subtable_df)

#    if subtable_df and df:
#        subtable_data_list = subtable_df_to_list(subtable_df, df)


# what parameters i need to send
#  maintable SQL path, main table name, datetime column name if datetime option being used, column names for checkboxes if checkboxes option being used,
# subtable SQL path if subtables option chosen, all table names from SQL .db file, sub-table name, sub-table column headers

# what i need it to return


def collect_maintabledata_fromSQL_databases(main_df: pd.DataFrame, maintable_datetime_columnname: List[str] = None,
                                            maintable_checkbox_columnnames: List[str] = None) -> \
                                                                [List[List[str]], List[str], Dict[int, str]]:
    checked_rows = None
    if maintable_datetime_columnname:
        main_df = df_datetime_type_conversion(main_df, column_to_convert_name=maintable_datetime_columnname)

    if maintable_checkbox_columnnames:
        checked_rows = dataframe_rows_checkboxed(main_df, maintable_checkbox_columnnames)

    maintable_data = maintable_df_to_list(main_df)

    return maintable_data, checked_rows


def collect_subtabledata_fromSQL_database(sub_df: pd.DataFrame, sql_subtable_path: str, allsub_tables: List[str], sql_subtable_name: str,
                                          sub_table_headers_labels: List[str], sql_subtable_query: str = None):

   # def subtable_df_to_list(subtable_df: pd.DataFrame, maintable_df: pd.DataFrame) -> List[List[str]]:

    pass