import sys
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QComboBox, QHBoxLayout, QApplication, QMainWindow

# change testing_file3 to the file with the Qtableview
import testing_file3

import time

class LazyDataViewer(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app

        self.setGeometry(200, 200, 600, 400)

        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout()

        self.main_horizontal = QHBoxLayout()
        self.sql_combo = QComboBox()
        self.sql_combo.addItem("For SQL tables to be added")

        self.main_horizontal.addWidget(self.sql_combo)

        table = self.table_SQLsetup_variables()

        self.main_layout.addLayout(self.main_horizontal)
        self.main_layout.addWidget(table)

        self.main_widget.setLayout(self.main_layout)

        self.setCentralWidget(self.main_widget)  # Set the QTableView as the central widget


    def table_SQLsetup_variables(self) -> QWidget:
        # note IF EXPANDABLE ROWS CHOSEN, make your columns_with_checkboxes not go by column index (so add +1 to the columns list)

        use_sql = True
        sql_maintable_name = "K057"
        sql_maintable_path = r"\\NAS3\Users\Jason Fuller\Desktop\tables\maintables.db"
        sql_subtable_path = r"\\NAS3\Users\Jason Fuller\Desktop\tables\subtables.db"
        sql_subtable_name = "K057_subtable"
        sub_table_headers_labels = ["NCR No.", "Disposition", "Date", "Extra", "Completed"]
        expandable_rows = True

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

        table = testing_file3.setup_table(app=self.app, use_sql=use_sql, sql_maintable_name=sql_maintable_name, sql_maintable_path=sql_maintable_path,
                                          sql_subtable_path=sql_subtable_path, sql_subtable_name=sql_subtable_name,
                                          sub_table_headers_labels=sub_table_headers_labels, expandable_rows=expandable_rows,
                                          datetime_columns=datetime_columns, columns_with_checkboxes=columns_with_checkboxes,
                                          footer=footer, footer_values=footer_values, subtable_col_checkboxes=subtable_col_checkboxes,
                                          add_mainrow_option=add_mainrow_option, del_mainrow_option=del_mainrow_option,
                                          add_subrow_option=add_subrow_option, del_subrow_option=del_subrow_option,
                                          subtable_datetime_columns=subtable_datetime_columns, editable_columns=editable_columns)

        return table


if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = LazyDataViewer(app)
    viewer.show()
    sys.exit(app.exec_())
