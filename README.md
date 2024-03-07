This is a work in progress project.  

This is based on a table UI element from an expensive piece of software from my work that is extremely
handy for a manufacturing environment for tracking work/showing data.  I thought I'd recreate it.

This QTableView uses a custom QHeaderView, QAbstractTableModel, QStyledItemDelegate QSortFilterProxyModel and more.  It has features that 
simulate checkboxes, sub-table widgets, searching, filtering, sorting.

Because of this implementation with custom views/models/delegates it will remain performant even with a TON of rows/columns.

<b>Features that this currently has as of 3/7/2024:</b>

1) Sorting
2) Column Sections are movable
3) Filtering w/ Comboboxes at the headers
4) Expansion of rows that display sub-tablewidgets to give additional information for each row
5) Checkboxes in columns for main table and sub-table widgets
6) Setting which columns you want to be editable or non-editable
7) Filter combobox options update dynamically as cell data is changed
8) In-column searching   (as you type in a cell it will search the column and highlight the matching string typed)
9) Optionable Footer Row
10) Current Filters applied will show up below footer
11) Date column datatype added that allows you to change the date with a Calendar popup in main table and sub-tables
12) Optional add/remove rows in main table and sub-tables by right clicking vertical headers
13) Option to make table editing only happen on double clicks   (double clicking opens up qdialog to change data for row)
14) support for using SQL database.
    <ul>a) Grabbing data from SQL tables to populate Qtableview</ul>
    <ul>b) Changes to table will be reflected to the SQL database.  (which includes the sub-tables)</ul>
    <ul>c) supports only using Sqlite3.</ul>
    <ul>d) The way this is written, won't cause issues with multiple people making changes at the same time.</ul>
15) Export visible rows to Excel
    



<b>Items left to finish:</b>
   
1) remove code for changing selection state of the checkboxes when mouse hovers over them....or find a different way, it doesn't work very well
   with current implementation... it's just a little visual indicator anyway.
   
2) Remove code for custom combobox filter dropdown locations, this uses the qapplication from pyqt5 to remove the default animations for the comboboxes,
   however this means the user has to pass down the qapplication to the qtableview.... which i don't want.

3) Add clear function to Qtableview if user clears table to populate table with new data. The clear function will make sure all necessary variables get
   safely reset
   <ul> After some testing on this, i need to restructure the code a bit to make the table re-usable so that the user can clear it and re-populate... this 
   will take a little bit of time.</ul>

5) Need to do some additional testing with the various options to squash bugs
   
6) Make documentation for the use of this

   
Header drop down filters and sub-tables for each row:
![1](https://github.com/jxfuller1/QTableView-with-Checkboxes-subtables-filtering-and-more/assets/123666150/bcf1022e-7328-452f-9bd5-bb75ba64a500)

In-Column Searching
![2](https://github.com/jxfuller1/QTableView-with-Checkboxes-subtables-filtering-and-more/assets/123666150/e3418c54-464c-4091-98fb-47a3db3651b2)

Footer and Currently Applied Filter Display
![1](https://github.com/jxfuller1/QTableView-with-Checkboxes-subtables-filtering-and-more/assets/123666150/b34bb368-fdc4-4391-b834-cd6e90b46f69)

Support for Calendar Date column(s)
![2](https://github.com/jxfuller1/QTableView-with-Checkboxes-subtables-filtering-and-more/assets/123666150/3b0c6d3b-7e34-40d5-a5fe-e85b9f4090ed)


Uploading this for now.  I honestly could find no examples of anyone else using this method of painting the image and manually handling the click states of the Checkbox in python... 
and it's my first time working with Views/Models, so uploading this for anyone else that may need this for now as I work on other features.
