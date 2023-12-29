This is a work in progress project.  For now this only features using QTableView/QAbstractTableModel and QStyleItemDelegate to simulate checkboxes.

I am not using QCheckBox(), but rather painting the image and manually handling the mouseclicks within the Delegate.  Doing it this way is FARRRR more
performant than adding QCheckBox() widgets in the Delegate.

Features that I will be adding (once i figure it out):

1) Sorting
2) QTableViews within rows (this is for expandable rows that can display additional details about whatever item is in the row)
3) Filtering


Uploading this for now.  I honestly could find no examples of anyone else using this method of painting the image and manually handling the click states of the Checkbox in python... 
and it's my first time working with Views/Models, so uploading this for anyone else that may need this for now as I work on other features.
