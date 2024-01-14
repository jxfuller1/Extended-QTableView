This is a work in progress project.  

This QTableView uses a custom QHeaderView, QAbstractTableModel, QStyledItemDelegate QSortFilterProxyModel and more.  It has features that 
simulate checkboxes, sub-table widgets, searching, filtering, sorting.

Because of this implementation with custom views/models/delegates it will remain performant even with a TON of rows/columns.

Features that this currently has as of 1/14/2024:

1) Sorting
2) Filtering w/ Comboboxes at the headers
3) Expansion of rows that contain a sub-table widget for additional information
4) Checkboxes in columns
5) Setting which columns you want to be editable
6) Being able to edit cell data
7) Filter combobox options update as cell data is changed

Features left to finish:

1) In-column searching (only partially working right now)
2) Connecting to SQL database to retrieve and write to as data is changed or checkboxes checked
3) Cleaning up code so user can easily make the table and choose options
4) Being able to add new rows
5) Adding/Changing some visual aspects
6) Add Footer Row

![table](https://github.com/jxfuller1/QTableView-with-Checkboxes/assets/123666150/fd7c4bec-748d-4785-81ac-475bd6842013)

Uploading this for now.  I honestly could find no examples of anyone else using this method of painting the image and manually handling the click states of the Checkbox in python... 
and it's my first time working with Views/Models, so uploading this for anyone else that may need this for now as I work on other features.
