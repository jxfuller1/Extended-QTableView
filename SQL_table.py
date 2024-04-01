import sqlite3
from typing import List, Dict, Union
import pandas as pd


# basically same as sql_maintable_to_dataframe function, just doens't return a dataframe
def sql_query_table(sql_path: str, table: str, query: str = None) -> Union[List[tuple], None]:
    if not query:
        query = f'SELECT * FROM "{table}"'

    try:
        conn = sqlite3.connect(sql_path)
        cursor = conn.cursor()
        cursor.execute(query)

        result = cursor.fetchall()
        conn.close()
    except:
        result = None

    return result


def update_sql_table_cell(sql_path: str, table_name: str, row_index: int, new_value, column_name: str = None, column_index: int = None):
    # must provide one or the other
    if not column_name and column_index == None:
        print("ERROR, must provide column name or column_index")

    if column_index or column_name or column_index == 0:
        conn = sqlite3.connect(sql_path)
        cursor = conn.cursor()

        # get column names, this is so that i can then get the column name by index location
        # since you cant update columns in sqlite3 by index, you need the column name
        # this also makes it so that the user doesn't have to provide the column name
        if not column_name:
            cursor.execute(f'PRAGMA table_info("{table_name}")')
            columns_info = cursor.fetchall()
            column_names = [column[1] for column in columns_info]
            column_name = column_names[column_index]

        # Execute the UPDATE statement
        query = f'UPDATE "{table_name}" SET "{column_name}" = ? WHERE rowid = ?'
        cursor.execute(query, (new_value, row_index))

        conn.commit()
        conn.close()


# add row and returns it's rowid
def add_sql_row(sql_path: str, table_name: str, values: list) -> int:
    conn = sqlite3.connect(sql_path)
    cursor = conn.cursor()
    placeholders = ', '.join(['?' for x in values])

    query = f'INSERT INTO "{table_name}" VALUES ({placeholders})'

    cursor.execute(query, values)

    last_rowid = cursor.lastrowid

    conn.commit()
    conn.close()

    return last_rowid


def del_sql_row(sql_path, table_name: str, row_index: int):
    conn = sqlite3.connect(sql_path)
    cursor = conn.cursor()

    primary_key_column = 'rowid'
    query = f'DELETE FROM "{table_name}" WHERE {primary_key_column} = ?'
    cursor.execute(query, (row_index,))

    conn.commit()
    conn.close()


def sql_get_all_rowids(sql_path: str, table_name: str) -> List[int]:
    conn = sqlite3.connect(sql_path)
    cursor = conn.cursor()
    query = f'SELECT rowid FROM "{table_name}"'
    cursor.execute(query)

    rowids = [row[0] for row in cursor.fetchall()]
    conn.close()

    return rowids


# this function not being used
def sql_retrieve_rowid_by_index(sql_path, table_name: str, row_index: int) -> tuple:
    conn = sqlite3.connect(sql_path)
    cursor = conn.cursor()

    query = f'SELECT rowid FROM "{table_name}" LIMIT 1 OFFSET {row_index}'
    cursor.execute(query)
    rowid = cursor.fetchall()

    conn.close()

    return rowid


def create_sql_table_from_excel(excel_file_path: str, table_name: str, sql_path: str):
    conn = sqlite3.connect(sql_path)
    df = pd.read_excel(excel_file_path)
    df.to_sql(table_name, conn, if_exists='replace', index=False)

    conn.commit()
    conn.close()


def create_blank_sql_table(sql_path: str, table_name: str, column_names: List[str]):
    # Add single quotes around each column name in case of spaces on column names
    quoted_column_names = [f'"{column_name}"' for column_name in column_names]

    query = 'CREATE TABLE IF NOT EXISTS ' + '"' + table_name + '"' + ' ('
    query += ', '.join(quoted_column_names)
    query += ');'

    conn = sqlite3.connect(sql_path)
    cursor = conn.cursor()
    cursor.execute(query)
    conn.commit()
    conn.close()


def drop_sql_table(sql_path: str, table_name: str):
    query = f'DROP TABLE IF EXISTS "{table_name}"'

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
        query = f'SELECT * FROM "{table}"'

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
            if '"' not in column[0] or '"' not in column[-1]:
                headers[index] = '"' + column + '"'

    # maintable_index column header must be added for subtables to work
    if "maintable_index" not in headers:
        headers.insert(0, "maintable_index")

    # if table not found in database, create it
    if subtable_name not in allsub_tables:
        query = 'CREATE TABLE IF NOT EXISTS ' + '"' + subtable_name + '"' + ' ('
        query += ', '.join(headers)
        query += ');'

        conn = sqlite3.connect(sql_path)
        cursor = conn.cursor()
        cursor.execute(query)
        conn.commit()
        conn.close()

    # default sql query if none provided
    if not query_subtable:
        query_subtable = 'SELECT '
        query_subtable += ', '.join(headers)
        query_subtable += f' FROM "{subtable_name}"'

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
        row_df = row_df.drop(columns=["maintable_index"])

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


# COMMENTED OUT CODE PURELY FOR TESTING PURPOSES
# COMMENTED OUT CODE PURELY FOR TESTING PURPOSES
# COMMENTED OUT CODE PURELY FOR TESTING PURPOSES

#sql_maintable_name = ""your_table_name"
#sql_maintable_path = r"your_maintable_sql_path"
#row_index = 1
#column_index = 0
#value = "Something"


#sql_maintable_name = "your_table_name"
#excel_path = r"your_excel_file"

#create_sql_table_from_excel(excel_path, sql_maintable_name, sql_maintable_path)

#drop_sql_table(sql_maintable_path, "your_table_name")


#drop_sql_table(r"your_sql_path", "your_subtable_name")
#test = sql_query_table(r"your_sql_path", "your_subtable-Name")

#update_sql_table_cell(sql_maintable_path, sql_maintable_name, row_index, value, column_index=column_index)


#df = sql_maintable_to_dataframe(sql_maintable_path, "K058")
#print(df)

