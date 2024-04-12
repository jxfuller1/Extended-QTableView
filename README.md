<b> UPDATE 4/12/2024, Almost done:  40% of the documentation is complete for using this </b>

<b>note: This uses PyQt5 and not PyQt6. This could easily be extended to PyQt6... im just personally using 5 still due to some libraries I have that require 5 still.</b>  

This is based on a table UI element from an expensive piece of software from my work that is extremely
handy for a manufacturing environment for tracking work/showing data.  I thought I'd recreate it.

My implementation of this will remain performant even with tens of thousands of rows of data.

<b>Features:</b>

1) Accepts SQL - uses SQLITE3 to read/write to tables
2) Expansion rows with additional tables
3) Columns that support checkboxes
4) Header Filtering  - w/ filter footer
5) In-column searching  (just type in the column to find what you want)
6) Export to Excel
7) Optional Footer Row
8) Optional add/remove rows
9) Optional Datetime columns w/ QCalendar
10) Optional double click to edit table(s)
11) Sorting/movable columns

![qtable](https://github.com/jxfuller1/Extended-QTableView/assets/123666150/20568e6a-dbf8-4996-8177-8c6b5736a5d3)
<p> <br /> </p>
<b>Use setup_table function to create table</b>

setup_table arguments (NOTE: these arguments do NOT need to be all passed in at time of table initialization.  The parameters/argument can be changed with separate functions later.

==================================================================================

<b>ExtentedQtableview.setup_table</b><i>(maintable_data, maintable_headers, columns_with_checkboxes, checked_indexes_rows, sub_table_data, editable_columns, datetime_columns, footer, footer_values, subtable_col_checkboxes, sub_table_headers_labels, expandable_rows, add_mainrow_option, del_mainrow_option, add_subrow_option, del_subrow_option, subtable_datetime_columns, dbleclick_edit_only, use_sql, sql_maintable_path, sql_maintable_name, sql_maintable_query, sql_subtable_path, sql_subtable_name, sql_subtable_query)</i>

<ul> 
  <li><b>maintable_data:</b>    Accepts list of strings representing each row of table, IE: [[row1, row1, row1], [row2, row2, row2]]</li> 
  <li><b>maintable_headers:</b>  Accepts list of strings for header labels, IE: [label1, label2, label3]</li> 
  <li><b>columns_with_checkboxes:</b>   Accepts list of integers for columns you want to have checkboxes, IE: [1, 2, 5]</li> 
  <li><b>checked_indexes_rows:</b>   Accepts a dictionary representing which rows you want to have checked for the columns with checkboxes, IE:  {1: [4, 5, 6], 2: [1, 2, 6], 5: [1, 3, 7]}</li> 
  <li><b>sub_table_data:</b>  Accepts a list of strings representing each row of the subtable for EACH row of the maintable, IE:  
     <br /> [ <br />
      [[1sub1, 1sub1, 1sub1], [1sub2, 1sub2 1sub2]], <br />
      [[2sub1, 2sub1, 2sub1], [2sub2, 2sub2, 2sub2]] <br />
      ] <br />
  If using subtables, this argument MUST be equal to the number of rows on the main table, even if the list is blank such as []</li> 
  <li><b>editable_columns:</b>  Accepts list of integers representing which columns you want to be editable, IE:  [1, 2, 5]</li> 
  <li><b>datetime_columns:</b>   Accepts list of integers representing which columns you want to use datetime and have a calendar popup, IE:  [1, 2, 5]</li> 
  <li><b>footer:</b>   Accepts True or False bool to enable/disable footer</li> 
  <li><b>footer_values:</b>  Accepts a dictionary for which columns you want to have a footer, keys are columns and can be "total" or "sum", IE: <br /> {1: "sum", 2: "total"}
  <br />
      "sum" = will sum integers/float values in the column together <br />
      "total" = will add up total columns or total boxes checked in column if the column is a checkbox column <br />
      Note: These values change dynamically based on any rows filtered</li> 
  <li><b>subtable_col_checkboxes:</b>  Accepts list of integers representing which columns in sub-tables to have checkboxes, IE: [0, 1, 3]</li> 
  <li><b>sub_table_headers_labels:</b>  Accepts list of strings representing header labels for sub-tables, IE: [header1, header2, header3]</li> 
  <li><b>expandable_rows:</b>  Accepts True or False bool.  This MUST be enabled to use sub-tables!</li> 
  <li><b>add_mainrow_option:</b>  Accepts True or False bool to enable option to add rows to main table</li> 
  <li><b>del_mainrow_option:</b>  Accepts True or False bool to enable option for deletion of rows to main table</li> 
  <li><b>add_subrow_option:</b>  Accepts True or False bool to enable option to add rows to sub-tables</li> 
  <li><b>del_subrow_option:</b>  Accepts True or False bool to enable option for deletion of rows to sub-tables</li> 
  <li><b>subtable_datetime_columns</b>  Accepts list of integers representing which columns in the sub-tables you want to be datetime with calendar popups, IE: [1, 5, 7]</li> 
  <li><b>dbleclick_edit_only:</b>  Accepts True or False bool to enable editing for the main table on a separate pop-up rather than on the table itself.  (useful to prevent accidental changes to the main table.</li> 
  <li><b>use_sql:</b>  Accepts True or False to enable the use of SQL tables.  This MUST be set to True to use SQL tables</li> 
  <li><b>sql_maintable_path:</b>  Accepts string representing full path to the SQL database file for the main table data</li> 
  <li><b>sql_maintable_name:</b>   Accepts string representing name of SQL table to grab from the SQL database file</li> 
  <li><b>sql_maintable_query:</b>  Accepts query to do a specific SQL query to grab specific data from the SQL table. NOTE: THIS HAS NOT BEEN TESTED</li> 
  <li><b>sql_subtable_path:</b>   Accepts string representing full path to SQL database file for the sub-table data</li> 
  <li><b>sql_subtable_name:</b>  Accepts string representing SQL table name from the SQL database file listed in the sql_subtable_path argument</li> 
  <li><b>sql_subtable_query</b>  Accepts query to do a specific SQL query to grab specific data from the sub-table SQL table. NOTE: THIS HAS NOT BEEN TESTED</li> 
</ul> 
