<b>CODING IS NOW COMPLETE.  <u>Documentation for how to properly use this to come shortly!</u>
You can pass in the parameters when initialization the table and/or use custom functions I made to change the parameters of the table afterwards</b>

This is based on a table UI element from an expensive piece of software from my work that is extremely
handy for a manufacturing environment for tracking work/showing data.  I thought I'd recreate it.

My implementation of this will remain performant even with tens of thousands of rows of data.


<b>Features that this currently has as of 4/1/2024:</b>

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
    

<b>Items left to finish:  ALMOST ALL FINISHED, YAY!!!</b>
   
1) Make documentation for the use of this

   
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
