import sys
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QComboBox, QHBoxLayout, QApplication, QMainWindow, QPushButton

# change testing_file3 to the file with the Qtableview
import testing_file3

import SQL_table
import time

class LazyDataViewer(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app

        self.setGeometry(200, 200, 600, 400)
        self.sql_maintable_path = r"\\NAS3\Users\Jason Fuller\Desktop\tables\maintables.db"

        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout()

        self.main_horizontal = QHBoxLayout()
        self.sql_combo = QComboBox()
        self.add_table_names()
        self.sql_combo.currentIndexChanged.connect(self.clear_table)

        self.add_new_main_table = QPushButton("Add table data")
        self.add_new_main_table.clicked.connect(self.table_data)

        self.add_expanse = QPushButton("Add Expanse")
        self.add_expanse.clicked.connect(self.change_expandable_test)

        self.change_subtable_headers = QPushButton("sub headers")
        self.change_subtable_headers.clicked.connect(self.sub_headers)

        self.change_sub_data = QPushButton("change sub-data")
        self.change_sub_data.clicked.connect(self.sub_data)

        self.change_use_sql = QPushButton("change use sql")
        self.change_use_sql.clicked.connect(self.change_using_sql)

        self.change_col_check = QPushButton("Chnage Col checkboxes")
        self.change_col_check.clicked.connect(self.change_col_checkboxes)

        self.main_horizontal.addStretch()
        self.main_horizontal.addWidget(self.sql_combo)
        self.main_horizontal.addWidget(self.add_new_main_table)
        self.main_horizontal.addWidget(self.add_expanse)
        self.main_horizontal.addWidget(self.change_sub_data)
        self.main_horizontal.addWidget(self.change_subtable_headers)
        self.main_horizontal.addWidget(self.change_col_check)
        self.main_horizontal.addWidget(self.change_use_sql)
        self.main_horizontal.addStretch()


        self.secondary_horizontal = QHBoxLayout()

        self.change_editable = QPushButton("change editable")
        self.change_editable.clicked.connect(self.change_editable_col)

        self.change_datetime = QPushButton("change datetime")
        self.change_datetime.clicked.connect(self.change_datetime_col)
        self.change_sub_col_check1 = QPushButton("change sub col check")
        self.change_sub_col_check1.clicked.connect(self.change_sub_col_check)
        self.change_sub_col_date1 = QPushButton("change sub date")
        self.change_sub_col_date1.clicked.connect(self.change_sub_col_date)

        self.change_main_add_row = QPushButton("change add mainrow")
        self.change_main_add_row.clicked.connect(self.change_main_row)
        self.change_main_del_row = QPushButton("change del mainrow")
        self.change_main_del_row.clicked.connect(self.change_delmain_row)
        self.change_sub_add_row = QPushButton("change add subrow")
        self.change_sub_add_row.clicked.connect(self.change_submain_row)
        self.change_sub_del_row = QPushButton("change del subrow")
        self.change_sub_del_row.clicked.connect(self.change_subdel_row)

        self.secondary_horizontal.addStretch()
        self.secondary_horizontal.addWidget(self.change_editable)
        self.secondary_horizontal.addWidget(self.change_datetime)
        self.secondary_horizontal.addWidget(self.change_sub_col_check1)
        self.secondary_horizontal.addWidget(self.change_sub_col_date1)
        self.secondary_horizontal.addWidget(self.change_main_add_row)
        self.secondary_horizontal.addWidget(self.change_main_del_row)
        self.secondary_horizontal.addWidget(self.change_sub_add_row)
        self.secondary_horizontal.addWidget(self.change_sub_del_row)
        self.secondary_horizontal.addStretch()

       # table = self.table_SQLsetup_variables()
        self.table = testing_file3.setup_table(app=self.app)

        self.main_layout.addLayout(self.main_horizontal)
        self.main_layout.addLayout(self.secondary_horizontal)
        self.main_layout.addWidget(self.table)

        self.main_widget.setLayout(self.main_layout)

        self.setCentralWidget(self.main_widget)  # Set the QTableView as the central widget

    def change_using_sql(self):
        self.table.update_using_sql(True)

    def change_main_row(self):
        self.table.update_add_mainrow_option(True)

    def change_delmain_row(self):
        self.table.update_del_mainrow_option(True)

    def change_submain_row(self):
        self.table.update_add_subrow_option(True)

    def change_subdel_row(self):
        self.table.update_del_subrow_option(True)

    def change_sub_col_check(self):
        sub_col = [0]
        self.table.loadnew_subtable_col_checkboxes(sub_col)

    def change_sub_col_date(self):
        sub_col = [1]
        self.table.loadnew_subtable_datetime(sub_col)

    def change_datetime_col(self):
        datetime_col = [3]
        self.table.loadnew_datetime_columns(datetime_col)

    def change_col_checkboxes(self):
        col_with_checks = [6, 7, 8, 14]
        self.table.loadnew_columns_with_checkboxes(col_with_checks)

    def change_editable_col(self):
        editable = [3]
        self.table.loadnew_edible_columns(editable)

    def sub_data(self):
        sub_data = [[["a", "b"], ["c", "d"]], [["g", ""], ["l", "m"]]]
        self.table.loadnew_subtable_list(sub_data)

    def sub_headers(self):
        sub_headers = ["sub1", "sub2"]
        self.table.loadnew_subtable_headers(sub_headers)

    def table_data(self):
        headers = ["GD", "GT", "GDates", "GNo", "Gome"]
        table_list = [["z", "True", "z", "z"], ["b", "False", "bf", "bg"]]
        self.table.loadnew_headers(headers)
        self.table.loadnew_maintable_list(table_list)

    def change_headers_test(self):
        headers = ["D", "T", "Dates", "No Butts", "something"]
        self.table.loadnew_headers(headers)

    def change_expandable_test(self):
        self.table.use_expandable_rows(True)

    def add_table_names(self):
        tables = SQL_table.sql_tables(self.sql_maintable_path)
        self.sql_combo.addItems(tables)

    def clear_table(self):
        table_name = self.sql_combo.currentText()
        sub_table_name = table_name + "_subtable"
        self.table.clear_table(keep_filter=True)
        self.table.loadnew_maintable_sql(maintable_name=table_name, maintable_sql_path=r"\\NAS3\Users\Jason Fuller\Desktop\tables\maintables.db",
                                         subtable_sql_name=sub_table_name, subtable_sql_path=r"\\NAS3\Users\Jason Fuller\Desktop\tables\subtables.db",
                                         subtable_headers=["NCR No.", "Disposition", "Date", "Extra", "Completed"], keep_existing_filter=True)

    def table_SQLsetup_variables(self) -> QWidget:
        use_sql = True
        sql_maintable_name = "K057"
        sql_maintable_path = r"\\NAS3\Users\Jason Fuller\Desktop\tables\maintables.db"
        sql_subtable_path = r"\\NAS3\Users\Jason Fuller\Desktop\tables\subtables.db"
        sql_subtable_name = "K057_subtable"
        sub_table_headers_labels = ["NCR No.", "Disposition", "Date", "Extra", "Completed"]
        expandable_rows = False

        columns_with_checkboxes = [5, 6, 7, 13]
        datetime_columns = [2]

        footer = True
        # can be total or sum (sum for adding integers/float values, total for adding total rows or if checkbox column
        # adds total checked
        footer_values = {1: "total", 5: "total", 6: "total"}
        subtable_col_checkboxes = [3]
        add_mainrow_option = True
        del_mainrow_option = True
        add_subrow_option = True
        del_subrow_option = True
        subtable_datetime_columns = [2]
        editable_columns = [0]

        self.table = testing_file3.setup_table(app=self.app, use_sql=use_sql, sql_maintable_name=sql_maintable_name, sql_maintable_path=sql_maintable_path,
                                          sql_subtable_path=sql_subtable_path, sql_subtable_name=sql_subtable_name,
                                          sub_table_headers_labels=sub_table_headers_labels, expandable_rows=expandable_rows,
                                          datetime_columns=datetime_columns, columns_with_checkboxes=columns_with_checkboxes,
                                          footer=footer, footer_values=footer_values, subtable_col_checkboxes=subtable_col_checkboxes,
                                          add_mainrow_option=add_mainrow_option, del_mainrow_option=del_mainrow_option,
                                          add_subrow_option=add_subrow_option, del_subrow_option=del_subrow_option,
                                          subtable_datetime_columns=subtable_datetime_columns, editable_columns=editable_columns)

        return self.table


if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = LazyDataViewer(app)
    viewer.show()
    sys.exit(app.exec_())
