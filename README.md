This is a work in progress project.  

This is based on a table UI element from an expensive piece of software from my work that is extremely
handy for a manufacturing environment for tracking work/showing data.  I thought I'd recreate it.

This QTableView uses a custom QHeaderView, QAbstractTableModel, QStyledItemDelegate QSortFilterProxyModel and more.  It has features that 
simulate checkboxes, sub-table widgets, searching, filtering, sorting.

Because of this implementation with custom views/models/delegates it will remain performant even with a TON of rows/columns.

Features that this currently has as of 1/21/2024:

1) Sorting
2) Column Sections are movable
3) Filtering w/ Comboboxes at the headers
4) Expansion of rows that to display sub-tablewidgets to give additional information for each row
5) Checkboxes in columns
6) Setting which columns you want to be editable
7) Being able to edit cell data
8) Filter combobox options update dynamically as cell data is changed
9) In-column search   (as you type in a cell it will search the column and highlight the matching string typed)
10) Available Footer Row

Features left to finish:

2) Connecting to SQL database to retrieve and write to as data is changed or checkboxes checked
3) Cleaning up code so user can easily make the table and choose options
4) Being able to add new rows
5) Adding/Changing some visual aspects
7) Add widget that shows current filters applied below footer row that hides/shows
8) Add support for setting a column as date datatype with having, on hover, button pop-up for calendar and choosing date

![1](https://github.com/jxfuller1/QTableView-with-Checkboxes-subtables-filtering-and-more/assets/123666150/bcf1022e-7328-452f-9bd5-bb75ba64a500)

![2](https://github.com/jxfuller1/QTableView-with-Checkboxes-subtables-filtering-and-more/assets/123666150/e3418c54-464c-4091-98fb-47a3db3651b2)


Uploading this for now.  I honestly could find no examples of anyone else using this method of painting the image and manually handling the click states of the Checkbox in python... 
and it's my first time working with Views/Models, so uploading this for anyone else that may need this for now as I work on other features.
