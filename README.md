<b> UPDATE 4/15/2024, Almost done:  95% of the documentation is complete for using this </b>

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

setup_table arguments (NOTE: these arguments do NOT need to be passed in at time of table initialization.  The parameters/argument can be changed with separate functions later.

==================================================================================

<b>ExtentedQtableview.setup_table</b><i>(maintable_data, maintable_headers, columns_with_checkboxes, checked_indexes_rows, sub_table_data, editable_columns, datetime_columns, footer, footer_values, subtable_col_checkboxes, sub_table_headers_labels, expandable_rows, add_mainrow_option, del_mainrow_option, add_subrow_option, del_subrow_option, subtable_datetime_columns, dbleclick_edit_only, use_sql, sql_maintable_path, sql_maintable_name, sql_maintable_query, sql_subtable_path, sql_subtable_name, sql_subtable_query)</i>

<ul> 
  <li><b>maintable_data:</b> ---- <b>List[List[str]]</b>  <br />
    <pre>Accepts list of strings representing each row of table, IE: [[row1, row1, row1], [row2, row2, row2]]</li> </pre>
  <li><b>maintable_headers:</b> ---- <b>List[str]</b> <br />
    <pre>Accepts list of strings for header labels, IE: [label1, label2, label3]</li> </pre>
  <li><b>columns_with_checkboxes:</b> ---- <b>List[int]</b> <br />
    <pre>Accepts list of integers for columns you want to have checkboxes, IE: [1, 2, 5]</li> </pre>
  <li><b>checked_indexes_rows:</b> ----  <b>Dict[int: List[int]]</b> <br />
    <pre>Accepts a dictionary representing which rows you want to have checked for the columns with checkboxes, key = column number, values = row numbers 
      IE:  {1: [4, 5, 6], 2: [1, 2, 6], 5: [1, 3, 7]}</li> </pre>
  <li><b>sub_table_data:</b> ---- <b>List[List[List[str]]]</b> <br />
    <pre>Accepts a list of strings representing each row of the subtable for EACH row of the maintable, IE:  
      [ 
      [[1sub1, 1sub1, 1sub1], [1sub2, 1sub2 1sub2]], 
      [[2sub1, 2sub1, 2sub1], [2sub2, 2sub2, 2sub2]] 
      ] 
If using subtables, this argument MUST be equal to the number of rows on the main table, even if the list is blank such as []. <br />For Example if your maintable has 3 rows and you are using expandable rows, then at minimum you need to pass [[], [], []] into this parameter</li> </pre>
  <li><b>editable_columns:</b> ---- <b>List[int]</b> <br />
   <pre>Accepts list of integers representing which columns you want to be editable, IE:  [1, 2, 5]</li> </pre>
  <li><b>datetime_columns:</b> ---- <b>List[int]</b> <br />
    <pre>Accepts list of integers representing which columns you want to use datetime and have a calendar popup, IE:  [1, 2, 5]</li> </pre>
  <li><b>footer:</b> ---- <b>bool   (True/False)</b> <br />
    <pre>Accepts True or False bool to enable/disable footer</li> </pre>
  <li><b>footer_values:</b> ---- <b>Dict[int: str]</b>  <br />
    <pre>Accepts a dictionary for which columns you want to have a footer, keys are columns indexes and values can be "total" or "sum", 
           <b>IE: {1: "sum", 2: "total"}</b> 
      "sum" = will sum integers/float values in the column together 
      "total" = will add up total columns or total boxes checked in column if the column is a checkbox column 
  Note: These values on the table will change dynamically based on any rows filtered</li> </pre>
  <li><b>subtable_col_checkboxes:</b> ---- <b>List[int]</b> 
    <pre>Accepts list of integers representing which columns in sub-tables to have checkboxes, IE: [0, 1, 3]</li> </pre>
  <li><b>sub_table_headers_labels:</b> ---- <b>List[str]</b> 
    <pre>Accepts list of strings representing header labels for sub-tables, IE: [header1, header2, header3]</li> </pre>
  <li><b>expandable_rows:</b> ---- <b>bool (True/False)</b> 
    <pre>Accepts True or False bool.  <b>This MUST be enabled to use sub-tables!</b></li> </pre>
  <li><b>add_mainrow_option:</b> ---- <b>bool (True/False)</b> 
    <pre>Accepts True or False bool to enable option to add rows to main table</li></pre> 
  <li><b>del_mainrow_option:</b> ---- <b>bool (True/False)</b> 
    <pre>Accepts True or False bool to enable option for deletion of rows to main table</li></pre> 
  <li><b>add_subrow_option:</b> ---- <b>bool (True/False)</b> 
    <pre>Accepts True or False bool to enable option to add rows to sub-tables</li></pre>
  <li><b>del_subrow_option:</b> ---- <b>bool (True/False)</b> 
    <pre>Accepts True or False bool to enable option for deletion of rows to sub-tables</li></pre>
  <li><b>subtable_datetime_columns</b> ---- <b>List[int]</b> 
    <pre>Accepts list of integers representing which columns in the sub-tables you want to be datetime with calendar popups, IE: [1, 5, 7]</li></pre>
  <li><b>dbleclick_edit_only:</b> ---- <b>bool (True/False)</b>  
  <pre>Accepts True or False bool to enable editing for the main table on a separate pop-up rather than on the table itself.  <br />(useful to prevent accidental changes to the main table.</li></pre> 
  <li><b>use_sql:</b> ---- <b>bool (True/False</b> 
    <pre>Accepts True or False to enable the use of SQL tables.  <b>This MUST be set to True to use SQL tables</b></li></pre>
  <li><b>sql_maintable_path:</b> ---- <b>str</b> 
    <pre>Accepts string representing full path to the SQL database file for the main table data</li></pre>
  <li><b>sql_maintable_name:</b> ---- <b>str</b> 
    <pre>Accepts string representing name of SQL table to grab from the SQL database file</li></pre>
  <li><b>sql_maintable_query:</b> ---- <b>str</b> 
    <pre>Accepts query to do a specific SQL query to grab specific data from the SQL table. <b>NOTE: THIS HAS NOT BEEN TESTED</b></li></pre>
  <li><b>sql_subtable_path:</b> ---- <b>str</b>  
    <pre>Accepts string representing full path to SQL database file for the sub-table data</li></pre>
  <li><b>sql_subtable_name:</b> ---- <b>str</b> 
    <pre>Accepts string representing SQL table name from the SQL database file listed in the sql_subtable_path argument</li></pre>
  <li><b>sql_subtable_query</b> ---- <b>str</b> 
    <pre>Accepts query to do a specific SQL query to grab specific data from the sub-table SQL table. <b>NOTE: THIS HAS NOT BEEN TESTED</b></li</pre> 
</ul> 

<b>Modify Table Functions</b>
================================================================================
If you've already setup your table instance, with say the following:
<pre>import ExtendedQtableview
table = ExtendedQtableview.setup_table()
</pre>
<b>table.loadnew_maintable_sql</b><i>(maintable_name, maintable_sql_path, maintable_query, subtable_sql_name, subtable_sql_path, subtable_headers, subtable_query, keep_existing_filter)</i>
<ul> 
  <li><b>maintable_name:</b> ---- <b>str</b> --- <b>Required</b><br />
    <pre>Name of SQL table to get from database</li></pre>
  <li><b>maintable_sql_path:</b> ---- <b>str</b> ---- <b>Required</b><br />
  <pre>Directory path to SQL database file</pre></li>
  <li><b>maintable_query:</b> ---- <b>str</b><br />
  <pre>SQL query to pass to get specific data from table  <b>NOTE: This has NOT been tested</b></pre></li>
  <li><b>subtable_sql_name:</b> ----- <b>str</b> <br />
  <pre>Name of SQL sub table to get from database</pre></li>
  <li><b>subtable_sql_path:</b> ---- <b>str</b> <br />
  <pre>Directory path to SQL database file</pre></li>
  <li><b>subtable_headers:</b> ---- <b>List[str]</b> ---- <b>Required if passing in subtable SQL name/path</b><br />
  <pre> List of column header names for the sub tables</pre></li>
  <li><b>subtable_query:</b> ---- <b>str</b><br />
  <pre>SQL query to pass to get specific data from table  <b>NOTE: This has NOT been tested</b></pre></li>
</ul>
Note: that you do not need to pass subtable data in when using this function, it can be done with a separate function later.

<br />
<br />
<br />
<b>table.loadnew_maintable_list</b><i>(maintable_data, keep_existing_filter)</i>
<ul>
<li><b>maintable_data:</b> ---- <b>List[str]</b><br />
<pre>Accepts list of strings representing each row of table, IE: [[row1, row1, row1], [row2, row2, row2]]</pre></li>
<li><b>keep_existing_filter:</b> ---- <b>bool (True/False)</b> <br />
<pre>Whether you want to keep any existing filters applied to the current table or not.  
This is useful if you want the new table to be filtered from the get go.</pre></li>
</ul>

<br />
<br />
<b>table.loadnew_subtable_list</b><i>(subtable_data)</i>
<ul>
<li><b>subtable_data:</b> ---- <b>List[List[List[str]]]</b> <br />
<pre>Accepts a list of strings representing each row of the subtable for EACH row of the maintable, IE:  
      [ 
      [[1sub1, 1sub1, 1sub1], [1sub2, 1sub2 1sub2]], 
      [[2sub1, 2sub1, 2sub1], [2sub2, 2sub2, 2sub2]] 
      ] 
If using subtables, this argument MUST be equal to the number of rows on the main table, even if the list is blank such as []. <br />For Example if your maintable has 3 rows and you are using expandable rows, then at minimum you need to pass [[], [], []] into this parameter</pre></li>
</ul>

<br />
<br />
<br />
<b>table.loadnew_subtable_sql</b><i>(subtable_sql_name, subtable_sql_path, subtable_headers, subtable_query)</i>
<ul>
<li><b>subtable_sql_name:</b> ---- <b>str</b> ---- <b>Required</b><br />
<pre>Table name listed in the SQL database</pre></li>
<li><b>subtable_sql_path:</b> ---- <b>str</b> ---- <b>Required</b><br />
<pre>Directory path to SQL database file</pre></li>
<li><b>subtable_headers</b> ---- <b>List[str]</b> ---- <b>Required</b><br />
<pre>Accepts list of strings representing each name of the header columns</pre></li>
<li><b>subtable_query:</b> ---- <b>str</b> <br />
<pre>Query to run on SQL database to get specific data from the table.  NOTE: This has not been tested</pre></li>
</ul>

<br />
<br />
<b>table.loadnew_checkboxed_rows</b><i>(checked_rows)</i>
<ul>
<li><b>checked_rows</b> ---- <b>Dict[int: List[int]]</b> <br />
<pre>Accepts a dictionary representing which rows you want to have checked for the columns with checkboxes, key = column number, values = row numbers 
      IE:  {1: [4, 5, 6], 2: [1, 2, 6], 5: [1, 3, 7]}</pre></li>
Note: If using expandable rows, you will NEED to add +1 to your column indexes for the keys. (this doesn't need to be done if providing this data during the initialization of the table with setup_table())
</ul>

<br />
<br />
<br />
<b>table.loadnew_columns_with_checkboxes</b><i>(columns_with_checkboxes)</i>
<ul>
<li><b>columns_with_checkboxes:</b> ---- <b>List[int]</b> <br />
<pre>Change columns you want designated on the main table to be checkbox columns</pre></li>
</ul>
Note: If using expandable rows, you will NEED to add +1 to your column indexes for the keys. (this doesn't need to be done if providing this data during the initialization of the table with setup_table())

<br />
<br />
<br />
<b>table.loadnew_edible_columns</b><i>(editable_columns)</i>
<ul>
<li><b>editable_columns:</b> ---- <b>List[int]</b> <br />
<pre>Change which columns you want to be user editable</pre></li>
</ul>
Note: If using expandable rows, you will NEED to add +1 to your column indexes for the keys. (this doesn't need to be done if providing this data during the initialization of the table with setup_table())

<br />
<br />
<br />
<b>table.loadnew_datetime_columns</b><i>(datetime_columns)</i>
<ul>
<li><b>datetime_columns:</b> ---- <b>List[int]</b> <br />
<pre>Change which columns you want to be date time.  If columns are editable, will provide a calendar popup to let user change dates.</pre></li>
</ul>
Note: If using expandable rows, you will NEED to add +1 to your column indexes for the keys. (this doesn't need to be done if providing this data during the initialization of the table with setup_table())

<br />
<br />
<br />
<b>table.loadnew_footervalues</b><i>(footer_values)</i>
<ul>
<li><b>footer_values</b> ---- <b>Dict[int: str]</b> <br />
<pre>Accepts a dictionary for which columns you want to have a footer, keys are columns indexes and values can be "total" or "sum", 
           <b>IE: {1: "sum", 2: "total"}</b> 
      "sum" = will sum integers/float values in the column together 
      "total" = will add up total columns or total boxes checked in column if the column is a checkbox column 
  Note: These values on the table will change dynamically based on any rows filtered</pre></li>
</ul>
Note: If using expandable rows, you will NEED to add +1 to your column indexes for the keys. (this doesn't need to be done if providing this data during the initialization of the table with setup_table())

<br />
<br />
<br />
<b>table.loadnew_subtable_headers</b><i>(subtable_headers)</i>
<ul>
<li><b>subtable_headers:</b> ---- <b>List[str]</b> <br />
<pre>Change column headers for the sub-tables</pre></li>
</ul>

<br />
<br />
<b>table.loadnew_subtable_col_checkboxes</b><i>(subtable_col_checkboxes)</i>
<ul>
<li><b>subtable_col_checkboxes</b>  ---- <b>List[int]</b> <br />
<pre>Change which column(s) in the sub tables you want to be checkbox columns</pre></li>
</ul>

<br />
<br />
<b>table.update_add_mainrow_option</b><i>(add_mainrow_option)</i>
<ul>
<li><b>add_mainrow_option:</b> ---- <b>bool (True/False)</b> <br />
<pre>Change if you want to allow user to add rows to main table</pre></li>
</ul>

<br />
<br />
<b>table.update_del_mainrow_option</b><i>(del_mainrow_option)</i>
<ul>
<li><b>del_mainrow_option:</b> ---- <b>bool (True/False)</b> <br />
<pre>Change if you want to allow user to delete rows from main table</pre></li>
</ul>

<br />
<br />
<b>table.update_add_subrow_option</b><i>(add_subrow_option)</i>
<ul>
<li><b>add_subrow_option:</b> ---- <b>bool (True/False)</b> <br />
<pre>Change if you want to allow user to add rows to the sub-tables</pre></li>
</ul>

<br />
<br />
<b>table.update_del_subrow_option</b><i>(del_subrow_option</i>
<ul>
<li><b>del_subrow_option</b> ---- <b>bool (True/False)</b> <br />
<pre>Change if you want to allow user to delete rows from the sub-tables</pre></li>
</ul>

<br />
<br />
<b>table.loadnew_subtable_datetime</b><i>(subtable_datetime_columns)</i>
<ul>
<li><b>subtable_datetime_columns:</b> ---- <b>List[int]</b> <br />
<pre>Change which column(s) you want the sub-table to be datetime, which will allow user to update date via calendar popup.</pre></li>
</ul>

<br />
<br />
<b>table.update_dblclick_edit_only</b><i>(dblclick_edit_only)</i>
<ul>
<li><b>dblclick_edit_only:</b> ---- <b>bool (True/False)</b> <br />
<pre> Enable to allow editing of the main table through a separate screen rather than on the table itself.  Useful to prevent accidental changes.</pre></li>
</ul>

<br />
<br />
<b>table.useFooter</b><i>(footer)</i>
<ul>
<li><b>footer:</b> ---- <b>bool (True/False)</b> <br />
<pre>Enable/Disable using a footer</pre></li>
</ul>

<br />
<br />
<b>table.loadnew_headers</b><i>(headers)</i>
<ul>
<li><b>headers</b> ---- <b>List[str]</b> <br />
<pre>Change the column headers on the main table</pre></li>
</ul>

<br />
<br />
<b>table.update_using_sql</b><i>(value)</i>
<ul>
<li><b>value:</b> ---- <b>bool (True/False)</b> <br />
<pre>Change on whether to use SQL tables.  Obviously must be enabled to pull data from SQL database and use tables</pre></li>
</ul>

<br />
<br />
<b>table.use_expandable_rows</b><i>(value)</i>
<ul>
<li><b>value</b> ---- <b>bool (True/False)</b> <br />
<pre>Enable/Disable using expandable rows with sub-tables</pre></li>
</ul>

<br />
<br />
<b>table.clear_table</b><i>(keep_filter)</i>
<ul>
<li><b>keep_filter</b> ---- <b>bool (True/False)</b> <br />
<pre>Function clears table and pass in whether you want to retain the existing filter or not when loading in new table</pre></li>
</ul>

Using existing QTableView Functions
====================================================================
If you've already setup your table instance, with say the following:
<pre>import ExtendedQtableview
table = ExtendedQtableview.setup_table()
</pre>

To use existing QTableView functions, just do <b>table.table_view.(existing qtableview function)()</b>
<br />
For example:
<pre>table.table_view.resizeColumnsToContents()</pre>

Other Notes:
===================================================================
<ul><li>If you want to make other actions happen when clicking on specific columns, such as opening a PDF.  Override/rewrite the <b>doubleclick_tableChange()</b> function to make an action happen when double clicking a certain column.</li>

<li>If using SQL w/ expandable rows and you provide a sub-table name and SQL directory path.   <b>The table MUST contain a "maintable_index" column</b>.  Where the maintable_index represents the row index of the maintable.  For example,  if your sub-table on the first row of the main table should have 10 rows in it, then you will have 10 rows on the SQL table with the number 1 in the maintable_index column.  
  <br /> It's very possible you could get this data in some other way, but the first value in each row data value of the sub-table list needs to contain a reference to which main table row it belongs to:
</li>

<li>If using SQL w/ expandable rows and you provide a sub-table name and SQL directory path.   If the table name does not exist in the SQL database, a blank table will automatically be created that has a "maintable_index" column. 
</li>

<li>
</li>
</ul>



