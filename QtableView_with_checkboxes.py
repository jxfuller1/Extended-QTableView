import sys
import time
import bisect
import SQL_table
import pandas as pd
from datetime import datetime

import random   #this is for testing purposes
from typing import List, Union, Tuple, Dict

from PyQt5.QtGui import QColor, QPen, QFont, QStandardItemModel, QWheelEvent, QMouseEvent, QKeyEvent, QPalette, \
    QStandardItem
from PyQt5.QtWidgets import QApplication, QTableView, QVBoxLayout, QMainWindow, QAbstractItemView, \
    QAbstractItemDelegate, QStyledItemDelegate, QPushButton, QWidget, QItemDelegate, QStyleOptionButton, QStyle, \
    QTableWidget, QHeaderView, QLabel, QLineEdit, QDialogButtonBox, QDialog, QTableWidgetItem, QComboBox, QFrame, \
    QCheckBox, QStyleOptionViewItem, QScrollBar, QHBoxLayout, QSizePolicy, QSpacerItem, QCalendarWidget, QDateEdit, \
    QMenu, QAction, QMessageBox, QFileDialog
from PyQt5.QtCore import Qt, QAbstractTableModel, QEvent, QVariant, QSize, QRect, QModelIndex, pyqtSignal, \
    QSortFilterProxyModel, QPoint, pyqtSlot, QCoreApplication, QTimer, QLocale, QItemSelectionModel, QDate

"""
Notes:  to make specific actions happen on double click based on column clicked, override doubleclick_tableChange function
in the QTableView, for example if you'd rather have a PDF open when double clicking column 1

"""

# function purely for testing performance
def random_indexes_for_testing(total_rows: int) -> List:
    random_indexes = []

    for i in range(total_rows-1):
        a = random.randint(0, total_rows-1)
        if a not in random_indexes:
            random_indexes.append(a)

    return random_indexes


class LineEdit(QLineEdit):

    def __init__(self, dblclick_edit_only, index, parent=None):
        super().__init__(parent)
        self.index = index
        self.dblclick_edit_only = dblclick_edit_only

    def focusInEvent(self, event):
        super().focusInEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.dblclick_edit_only:
            main_table = self.parent().parent()
            source_index = main_table.indexFromProxytoSource(self.index.row(), 0)
            main_table.doubleclick_tableChange(source_index, self)


class CustomCalendarWidget(QCalendarWidget):
    cleardate = pyqtSignal()

    def __init__(self, parent=None):
        super(CustomCalendarWidget, self).__init__(parent)

        self.custom_button = QPushButton("Clear Date", self)
        self.custom_button.clicked.connect(self.clearOut_date)

        self.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)

    def clearOut_date(self):
        self.cleardate.emit()

    def paintCell(self, painter, rect, date):
        super(CustomCalendarWidget, self).paintCell(painter, rect, date)
        self.custom_button.setGeometry(self.width()-65, self.height()-18, 65, 18)


class CustomDateEdit(QDateEdit):
    onDateChanged = pyqtSignal(object)
    cleardateChanged = pyqtSignal(object)

    def __init__(self, parent=None):
        super(CustomDateEdit, self).__init__(parent)

        self.setCalendarPopup(True)
        self.popup_installed = False

        # Create and set the custom calendar widget
        custom_calendar_widget = CustomCalendarWidget(self)
        custom_calendar_widget.cleardate.connect(self.clear_date_changed)
        self.setCalendarWidget(custom_calendar_widget)

    def showEvent(self, event):
        # Override showEvent to access the calendar popup and install event filter
        super(CustomDateEdit, self).showEvent(event)

        if not self.popup_installed:
            # Access the calendar popup
            calendar_popup = self.findChild(QCalendarWidget)

            if calendar_popup:
                self.popup_installed = True
                calendar_popup.clicked.connect(self.on_calendar_clicked)

    def on_calendar_clicked(self, date):
        self.onDateChanged.emit(self)

    def clear_date_changed(self):
        self.cleardateChanged.emit(self)


# delegate for entire qtableview
class ButtonDelegate(QStyledItemDelegate):
    onexpansionChange = pyqtSignal(int, bool)
    oncheckboxstateChange = pyqtSignal(int, int, str)
    # this signal is for updating the vertical header when editor is opened on cell for the arrow
    oneditorStarted = pyqtSignal(object, object)

    # passing keypresses from line edit to tableview to support in-column searching
    keyPressed = pyqtSignal(QLineEdit, QKeyEvent)
    datekeyPressed = pyqtSignal(QDateEdit)
    cleardatekeyPressed = pyqtSignal(QDateEdit)

    def __init__(self, checked_indexes_rows, checked_indexed_columns, editable_columns, datetime_columns, expandable_rows,
                 dblclick_edit_only, parent=None):
        super(ButtonDelegate, self).__init__(parent)

        self.valid_date_formats = ["yyyy-MM-dd", "MM/dd/yyyy", "dd-MM-yyyy", "yyyy/MM/dd"]

        # set matching date format to 1 by default, will auto change if another format found
        self.matching_date_format = self.valid_date_formats[1]

        self.last_press_index = QModelIndex()
        self.last_release_index = QModelIndex()
        self.checked_indexes_rows = checked_indexes_rows
        self.checked_indexed_columns = checked_indexed_columns
        self.editable_columns = editable_columns
        self.datetime_columns = datetime_columns
        self.expandable_rows = expandable_rows
        self.dblclick_edit_only = dblclick_edit_only

        # this var for if user just clicks off popup without clicking a date, if cell has nothing in it, then it won't
        # popuplate the cell
        self.dateEditor_key_press = False
        self.clear_date_pressed = False

        self.expanded_rows = []

    def eventFilter(self, obj, event):
        if isinstance(obj, QLineEdit) and event.type() == QKeyEvent.KeyPress:
            # Emit the signal when a key is pressed in the QLineEdit
            self.keyPressed.emit(obj, event)

        return super().eventFilter(obj, event)

    def paint(self, painter, option, index):
        # map clicked row to source model index  (this needs to be done if user sorts/filters)
        index = index.model().mapToSource(index)

        if self.checked_indexed_columns and index.column() in self.checked_indexed_columns:
            button = QStyleOptionButton()

            # i don't know why but height needs to always be an odd number (or always even) for the y position
            # to be returned correctly on row height changes....otherwise for whatever reason it causes a 1 pixel difference
            # in y positioning for the checkboxes
            height = option.rect.height()
            if option.rect.height() % 2 == 0:
                height = option.rect.height() - 1

            # set checkboxes to top/middle of cells
            new_x = option.rect.x() + int(option.rect.width()/2) - 5
            new_y = option.rect.y() - int(height/2) + 9

            new_rect = QRect(new_x, new_y, option.rect.width(), option.rect.height())
            button.rect = new_rect

            if index == self.highlighted_index:
                button.state |= QStyle.State_MouseOver
            else:
                button.state |= QStyle.State_Enabled

       #     button.state |= QStyle.State_Enabled
            if index.row() in self.checked_indexes_rows.get(index.column()):
                button.state |= QStyle.State_On
            else:
                button.state |= QStyle.State_Off

            QApplication.style().drawControl(QStyle.CE_CheckBox, button, painter)

        # display text from qabstractmodel
        if self.checked_indexed_columns and index.column() != 0 and index.column() not in self.checked_indexed_columns:
            text = index.data(Qt.DisplayRole)
            text_rect = option.rect.adjusted(3, 2, -3, -2)
            painter.drawText(text_rect, Qt.AlignTop | Qt.AlignLeft, text)

        if not self.checked_indexed_columns and index.column() != 0:
            text = index.data(Qt.DisplayRole)
            text_rect = option.rect.adjusted(3, 2, -3, -2)
            painter.drawText(text_rect, Qt.AlignTop | Qt.AlignLeft, text)

        if index.column() == 0 and self.expandable_rows:
            # Set the fixed size for the box
            box_size = 13

            new_y = option.rect.y() + 3
            new_x = option.rect.x() + int(option.rect.width()/2) - 5

            box_rect = QRect(new_x-4, new_y, box_size, box_size)

            painter.drawRect(box_rect)

            # Set the color for the box around the text
            border_color = QColor(0, 0, 0)  # Black
            painter.setPen(border_color)

            if index.row() in self.expanded_rows:
                text = "-"
            else:
                text = "+"

            text_rect = QRect(option.rect.x()-6+box_size, option.rect.y()+3, option.rect.width()-16, box_size)  # Move the text to the top
            painter.setPen(border_color)
            painter.drawText(text_rect, Qt.AlignCenter, text)

        if index.column() == 0 and not self.expandable_rows:
            text = index.data(Qt.DisplayRole)
            text_rect = option.rect.adjusted(3, 2, -3, -2)
            painter.drawText(text_rect, Qt.AlignTop | Qt.AlignLeft, text)

        self.highlighted_index = QModelIndex()

    def editorEvent(self, event, model, option, index):
        # map clicked row to source model index (needs to be done if user sorts/filters)
        index = index.model().mapToSource(index)

        expansion_rows = False
        if index.column() == 0 and self.expandable_rows:
            expansion_rows = True

        if self.checked_indexed_columns and index.column() in self.checked_indexed_columns or expansion_rows:
            button_rect = option.rect
            if event.type() == QEvent.MouseButtonPress:
                if button_rect.contains(event.pos()):
                    self.last_press_index = index
                    self.change_button_state(index.row(), index.column())
                return True

            elif event.type() == QEvent.MouseButtonRelease:
                if button_rect.contains(event.pos()):
                    self.last_release_index = index
                    self.change_button_state(index.row(), index.column())
                return True

            elif event.type() == event.MouseMove:
                # create a bounding box slightly smaller than the cell itself.  When mouse movements are detected, if within
                # the boudning box this will change mouse over state in paint().  If mouse within cell but outside this smaller
                # bounding box in the cell, it will remove mouse over state in paint()
                new_rect = QRect(option.rect.x()+6, option.rect.y()+4,  option.rect.width()-12, option.rect.height()-8)
                if new_rect.contains(event.pos()):
                # Update the highlighted index when the mouse is over the checkbox
                    if self.highlighted_index != index:
                        self.highlighted_index = index
                        return True  # Ensure the view gets updated
                else:
                    # Reset the highlighted index when the mouse moves out of the cell
                    self.highlighted_index = QModelIndex()
                    return True

            else:
                return True

        if event.type() == event.MouseButtonPress:
            self.parent().search_text = ""

        return super(ButtonDelegate, self).editorEvent(event, model, option, index)

    def change_button_state(self, row: int, column: int):
        if column == 0 and self.expandable_rows:
            if self.last_press_index == self.last_release_index:
                if row in self.expanded_rows:
                    self.expanded_rows.remove(row)
                    self.pressed_expansion(row, expand=False)
                else:
                    self.expanded_rows.append(row)
                    self.pressed_expansion(row, expand=True)

                self.last_press_index = QModelIndex()
                self.last_release_index = QModelIndex()

        elif column in self.checked_indexed_columns and not self.dblclick_edit_only:
            if self.last_press_index == self.last_release_index:
                if row in self.checked_indexes_rows.get(column):
                    self.checked_indexes_rows[column].remove(row)

                    # emit to update proxy filter that checkbox states changed and update footer number and update SQL if
                    # sql database option chosen
                    self.oncheckboxstateChange.emit(column, row, "False")
                else:
                    self.checked_indexes_rows[column].append(row)
                    self.oncheckboxstateChange.emit(column, row, "True")

                self.last_press_index = QModelIndex()
                self.last_release_index = QModelIndex()

                self.pressed_checkbox(row, column)

    def pressed_expansion(self, row: int, expand: bool):
        self.onexpansionChange.emit(row, expand)

    # THIS COMMENTED FUNCTION NOT BEING USED - but keep around just in case
    def pressed_checkbox(self, row: int, column: int):
        pass
        #if row not in self.checked_indexes_rows.get(column):
        #    print(f"Removed; Row index {row}, Column index {column}")
        #elif row in self.checked_indexes_rows.get(column):
        #    print(f"Added; Row index {row}, Column index {column}")

    def createEditor(self, parent, option, index):
        expansion_rows = False
        if index.column() == 0 and self.expandable_rows:
            expansion_rows = True

        if self.editable_columns and index.column() in self.editable_columns:
            editor = LineEdit(self.dblclick_edit_only, index, parent)
            editor.setReadOnly(False)
            self.oneditorStarted.emit(index, editor)
            editor.installEventFilter(self)
            return editor

        elif self.datetime_columns and index.column() in self.datetime_columns:
            editor = CustomDateEdit(parent)
            editor.onDateChanged.connect(self.on_date_editor_changed)
            editor.cleardateChanged.connect(self.clear_calendar_date)
            editor.setMaximumWidth(18)
            editor.setFocusPolicy(Qt.NoFocus)
            editor.setCalendarPopup(True)
            return editor

        elif self.checked_indexed_columns and index.column() in self.checked_indexed_columns:
            return

        elif index.column() and not expansion_rows or index.column() == 0 and not expansion_rows:
            editor = LineEdit(self.dblclick_edit_only, index, parent)
            editor.setReadOnly(True)
            self.oneditorStarted.emit(index, editor)
            editor.installEventFilter(self)
            return editor

        return

    def setEditorData(self, editor, index):
        # Set the initial content of the editor here
        if not self.datetime_columns:
            editor.setText(index.data(Qt.DisplayRole))

        elif self.datetime_columns and index.column() in self.datetime_columns:
            cell_value = index.data(Qt.DisplayRole)

            # find matching date format being used
            matching_format = self.find_matching_format(cell_value, self.valid_date_formats)

            # set date on calendar popup if valid date in cell, else set todays date
            date = QDate.fromString(cell_value, matching_format)

            if date.isValid() and cell_value != "":
                editor.calendarWidget().setSelectedDate(date)
            else:
                today = QDate.currentDate()
                editor.calendarWidget().setSelectedDate(today)

        elif self.datetime_columns and index.column() not in self.datetime_columns:
            editor.setText(index.data(Qt.DisplayRole))

    def updateEditorGeometry(self, editor, option, index):
        # Set the geometry of the editor within the cell
        if not self.datetime_columns:
            cell_rect = option.rect
            editor.setGeometry(cell_rect.x(), cell_rect.y(), cell_rect.width(), 20)

        elif self.datetime_columns and index.column() in self.datetime_columns:
            cell_rect = option.rect
            editor.setGeometry(cell_rect.x() + cell_rect.width() - 18, cell_rect.y(), 18, 19)

        elif self.datetime_columns and index.column() not in self.datetime_columns:
            cell_rect = option.rect
            editor.setGeometry(cell_rect.x(), cell_rect.y(), cell_rect.width(), 20)

    def setModelData(self, editor, model, index):
        if not self.datetime_columns:
            value = editor.text()
            source_index = model.mapToSource(index)  # Map to the source index
            source_model = model.sourceModel()  # Get the source model from the proxy model
            source_model.setData(source_index, value, Qt.EditRole)

        elif self.datetime_columns and index.column() not in self.datetime_columns:
            value = editor.text()
            source_index = model.mapToSource(index)  # Map to the source index
            source_model = model.sourceModel()  # Get the source model from the proxy model
            source_model.setData(source_index, value, Qt.EditRole)

        elif self.datetime_columns and index.column() in self.datetime_columns and self.dateEditor_key_press:
            date = editor.date()
            date_string = date.toString(self.matching_date_format)
            source_index = model.mapToSource(index)  # Map to the source index
            source_model = model.sourceModel()  # Get the source model from the proxy model
            source_model.setData(source_index, date_string, Qt.EditRole)
            self.dateEditor_key_press = False

        # this is for the clear button in the calendar
        elif self.datetime_columns and index.column() in self.datetime_columns and self.clear_date_pressed:
            source_index = model.mapToSource(index)  # Map to the source index
            source_model = model.sourceModel()  # Get the source model from the proxy model
            source_model.setData(source_index, "", Qt.EditRole)
            self.clear_date_pressed = False

    def on_date_editor_changed(self, dateclicked):
        self.dateEditor_key_press = True
        self.datekeyPressed.emit(dateclicked)

    def clear_calendar_date(self, dateclearclicked):
        self.clear_date_pressed = True
        self.cleardatekeyPressed.emit(dateclearclicked)

    # for finding matching date format string being used
    def find_matching_format(self, date_string, date_formats):
        for date_format in date_formats:
            try:
                # Try to convert the string using the current date format
                date = QDate.fromString(date_string, date_format)
                if date.isValid():
                    # The conversion was successful, and the date is valid
                    # set matching date format variable to matching date format
                    self.matching_date_format = self.valid_date_formats[date_formats.index(date_format)]
                    return date_format
            except ValueError:
                # Conversion failed for the current format
                pass

        # No matching format found
        return None


class HiddenRowsProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.filter_dict = {}

        # dict represents all columns/rows with checkmarks
        self.filter_checked_rows = {}

        # this is to support the columns with checkbox sorting
        self.cust_sort_order = {}

    def setFilterData(self, filter_dict: dict, checked_rows: dict = None):
        if not checked_rows:
            self.filter_dict = filter_dict
        if checked_rows:
            self.filter_dict = filter_dict
            self.filter_checked_rows = checked_rows

        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        if not self.filter_dict:
            return True

        source_model = self.sourceModel()

        for column, filter_values in self.filter_dict.items():
            index = source_model.index(source_row, column, source_parent)
            data = source_model.data(index, Qt.DisplayRole)

            if column in self.filter_checked_rows and len(filter_values) != 0:
                if "False" in filter_values and index.row() not in self.filter_checked_rows[column]:
                    return False
                if "True" in filter_values and index.row() in self.filter_checked_rows[column]:
                    return False

            elif data in filter_values:
                return False

        return True

    # custom sorting for the columsn with checkboxes
    def lessThan(self, left, right):
        leftData = self.sourceModel().data(left)
        rightData = self.sourceModel().data(right)

        # custom sorting for the columsn with checkboxes
        if left.column() in self.cust_sort_order:
            if left.row() in self.cust_sort_order[left.column()] and right.row() in self.cust_sort_order[left.column()]:
                return self.cust_sort_order[left.column()].index(left.row()) < self.cust_sort_order[left.column()].index(right.row())
        else:
            return leftData < rightData


class LazyDataModel(QAbstractTableModel):
    sql_value_change = pyqtSignal(int, int, str)

    def __init__(self, data: List[str] = None, columns_with_checkboxes: List[int] = None,
                 column_headers: List[str] = None, expandable_rows: bool = False):
        super().__init__()

        if not data:
            self.table_data = []
        else:
            self.table_data = data

        if not column_headers:
            self.column_headers = []
        else:
            self.column_headers = column_headers

        self.checkbox_indexes = columns_with_checkboxes
        self.row_clicked = -1
        self.expandable_rows = expandable_rows

        # add header for column expansion if expandable rows added to table
        if self.expandable_rows:
            self.column_headers.insert(0, "")

        self.font = QFont()
        self.font.setBold(True)
        self.font.setPointSize(8)  # Set the desired font size

    def update_headers(self, new_column_headers):
        # add header for column expansion if expandable rows added to table
        if self.expandable_rows:
            new_column_headers.insert(0, "")

        self.beginResetModel()
        self.column_headers = new_column_headers
        self.endResetModel()

    def rowCount(self, parent=None):
        return len(self.table_data)

    def columnCount(self, parent=None):
        if self.expandable_rows:
            if self.table_data:
                columns = max([len(self.table_data[0])+1, len(self.column_headers)])
                return columns
            else:
                return len(self.column_headers)
        else:
            if self.table_data:
                columns = max([len(self.table_data[0]), len(self.column_headers)])
                return columns
            else:
                return len(self.column_headers)

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and index.column() >= 0 and self.checkbox_indexes and index.column() not in self.checkbox_indexes \
                or role == Qt.DisplayRole and index.column() >= 0 and not self.checkbox_indexes:
            # -1 on the column to account for the expansion column
            if self.expandable_rows:
                row_value = self.table_data[index.row()][index.column()-1]
            else:
                row_value = self.table_data[index.row()][index.column()]
            return row_value
        elif role == Qt.EditRole:
            return False
        return None

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.FontRole:
            return self.font

        if orientation == Qt.Vertical and role == Qt.DisplayRole:
            if section == self.row_clicked:
                return "\u27A1"
            else:
                return "   "

        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            try:
                return self.column_headers[section]
            except:
                return str(section)

        return None

    # update orws that have been extended
    def setVerticalHeader(self, row_clicked):
        self.row_clicked = row_clicked
        # Notify the view that header data has changed
        self.headerDataChanged.emit(Qt.Vertical, row_clicked, row_clicked)

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsEnabled

        return super().flags(index) | Qt.ItemIsEditable  # add editable flag.

    def setData(self, index, value, role):

        if role == Qt.EditRole:
            # -1 on the column to account for the expansion column, set new value if value changed in cell
            if self.expandable_rows:
                get_value = self.table_data[index.row()][index.column()-1]
            else:
                get_value = self.table_data[index.row()][index.column()]

            if value != get_value:
                if self.expandable_rows:
                    self.table_data[index.row()][index.column()-1] = value
                else:
                    self.table_data[index.row()][index.column()] = value
                self.dataChanged.emit(index, index)

                self.sql_value_change.emit(index.row(), index.column(), value)

                return True

            return False
        return False

    def insertRow(self, data):
        self.beginInsertRows(self.index(len(self.table_data), 0), len(self.table_data), len(self.table_data))
        self.table_data.append(data)
        self.endInsertRows()

    def removeRow(self, row, parent=QModelIndex()):
        self.beginRemoveRows(parent, row, row)
        del self.table_data[row]
        self.endRemoveRows()
        return True


class CustomTableView(QTableView):
    sql_add_row = pyqtSignal(list)
    sql_del_row = pyqtSignal(int)
    onsql_rowChange = pyqtSignal(int, int, str)
    sql_value_change = pyqtSignal(int, int, str)
    sql_addrow_subtable = pyqtSignal(int, list)
    sql_delrow_subtable = pyqtSignal(int, int)
    sql_update_subtable = pyqtSignal(int, int, list)

    def __init__(self, app: QApplication, model, columns_with_checkboxes: List[int] = None, checked_indexes_rows: Dict[int, List[int]] = None,
                 sub_table_data: List[List[str]] = None, editable_columns: List[int] = None, parent=None,
                 datetime_columns: List[int] = None, footer: bool = False, footer_values: dict = None,
                 subtable_col_checkboxes: List[int] = None, subtable_header_labels: List[str] = None, expandable_rows: bool = False,
                 add_mainrow_option: bool = False, del_mainrow_option: bool = False, add_subrow_option: bool = False,
                 del_subrow_option: bool = False, subtable_datetime_columns: List[int] = None, dblclick_edit_only: bool = False):

        super().__init__(parent)
        # parent being a qframe
        parent.resizeSignal.connect(self.handle_parent_resize)

        # move 1,1 position within qframe parent so that frame and widget dont' overlap
        self.move(1, 1)

        self.app = app

        self.sub_table_widgets = {}
        self.filter_dict = {}
        self.filter_checked_rows = {}
        self.editable_columns = editable_columns
        self.set_current_editor = None
        self.datetime_columns = datetime_columns
        self.subtable_col_checkboxes = subtable_col_checkboxes
        self.subtable_header_labels = subtable_header_labels
        self.expandable_rows = expandable_rows
        self.add_mainrow_option = add_mainrow_option
        self.del_mainrow_option = del_mainrow_option
        self.add_subrow_option = add_subrow_option
        self.del_subrow_option = del_subrow_option
        self.subtable_datetime_columns = subtable_datetime_columns
        self.dblclick_edit_only = dblclick_edit_only

        self.footer_show = footer
        self.footer_row_boxes = []
        self.footer_values = footer_values

        self.footer_height = 0
        if footer:
            self.footer_height = 25

        self.filter_footer_margin_height = 25
        self.viewport_bottom_margin = 0
        if self.footer_show:
            self.viewport_bottom_margin = self.viewport_bottom_margin + self.footer_height

        self.search_text = ""

        # lists for mapping which rows are extended and which rows are for tables for the abstractmodel and button delegate
        self.row_clicked = []

        self.model = model
        self.model.dataChanged.connect(self.model_data_changed)
        self.columns_with_checkboxes = columns_with_checkboxes

        self.checked_indexes_rows = checked_indexes_rows
        self.sub_table_data = sub_table_data

        # check to make sure these 3 arguments do not contain the same column numbers, print error if so, because
        # if they have the same columns, it causes crashes
        self.column_arguments_same()

        self.proxy_model = HiddenRowsProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.setModel(self.proxy_model)

        self.setDelegates()
        self.setEditTriggers(QAbstractItemView.CurrentChanged)
        if self.dblclick_edit_only:
            self.doubleClicked.connect(self.doubleclick_tableChange)
        self.vertical_header_setup()
        self.horizontal_header_setup()

        self.setMouseTracking(True)
        self.clicked.connect(self.on_cell_clicked)

        self.selection_model = self.selectionModel()
        self.selection_model.currentChanged.connect(self.handleCurrentChanged)

        self.verticalScrollBar().valueChanged.connect(self.update_sub_table_positions_timer)
        self.verticalScrollBar().rangeChanged.connect(self.update_sub_table_positions_timer)
        self.verticalHeader().sectionResized.connect(self.update_sub_table_positions_timer)
        self.horizontalScrollBar().valueChanged.connect(self.update_sub_table_positions_timer)
        self.horizontalScrollBar().rangeChanged.connect(self.update_sub_table_positions_timer)
        self.horizontalHeader().sectionResized.connect(self.update_sub_table_positions_timer)

        vheader = self.verticalHeader()
        vheader.setContextMenuPolicy(Qt.CustomContextMenu)
        vheader.customContextMenuRequested.connect(self.show_context_menu)

        hheader = self.horizontalHeader()
        hheader.setContextMenuPolicy(Qt.CustomContextMenu)
        hheader.customContextMenuRequested.connect(self.show_context_menu)

        # Apply styles directly to QTableView
        # Apply style to hide the frame
        self.setObjectName("tableview")
        self.setStyleSheet("QTableView#tableview {border: none;}")

        # viewport margin for footer if user selectes one
        self.setViewportMargins(self.verticalHeader().size().width(), self.horizontalHeader().size().height(), 0, self.viewport_bottom_margin)

        if self.footer_show:
            self.footer()

        self.display_filter_setup()

        self.setAlternatingRowColors(True)

        self.resizeColumnsToContents()
        if self.expandable_rows:
            self.setColumnWidth(0, 20)

    def doubleclick_tableChange(self, index, line_edit: QLineEdit = None):
        header_labels = []
        for i in range(self.model.columnCount()):
            header_labels.append(self.model.headerData(i, Qt.Horizontal, Qt.DisplayRole))

        if not line_edit:
            source_index = self.indexFromProxytoSource(index.row(), index.column())
        else:
            source_index = index

        row_data = self.model.table_data[source_index.row()]
        title = "Modify row data"

        checked_row_items = None
        if self.columns_with_checkboxes:
            checked_row_items = []
            delegate = self.itemDelegate()
            for key, value in delegate.checked_indexes_rows.items():
                if index.row() in value:
                    checked_row_items.append("TRUE")
                else:
                    checked_row_items.append("")

        self.row_dialog = addRowMaintable_window(self, self.model.columnCount(), self.columns_with_checkboxes,
                                                 self.datetime_columns, self.expandable_rows, header_labels, title,
                                                 row_data, checked_row_items, source_index.row())
        self.row_dialog.onexistingRowChanged.connect(self.addMainRowUpdate)
        self.row_dialog.exec()

    def show_context_menu(self, position):
        vertical_header = self.verticalHeader()
        index = vertical_header.logicalIndexAt(position)

        # update selected row on right click of header in table
        self.update_row_selection(index)

        menu = QMenu(self)

        # Add actions or other menu items as needed
        if self.del_mainrow_option:
            delete = QAction(f"Delete Current Row", self)
            delete.triggered.connect(lambda: self.delMainRowMsg(index))
            menu.addAction(delete)
        if self.add_mainrow_option:
            add = QAction(f"Add New Row", self)
            add.triggered.connect(lambda: self.addMainRowMsg(index))
            menu.addAction(add)

        if self.del_mainrow_option or self.add_mainrow_option:
            menu.addSeparator()

        export = QAction(f"Export", self)
        export.triggered.connect(self.export_table)
        menu.addAction(export)

        # Show the context menu at the specified position
        menu.exec_(self.mapToGlobal(position))

    # outputs transformed data table list for export
    def export_table_getCheckboxes(self, data: List[str]) -> List[str]:
        # checkbox data isn't saved to the main table data in the qabstracttablemodel in my program, so
        # i need to transfer that data into the main table data before exporting
        delegate = self.itemDelegate()
        checked_rows = delegate.checked_indexes_rows

        # take checked items and make the corresponding table data with "True" to represent they are checked
        if checked_rows != None:
            for key, values in checked_rows.items():
                for value in values:
                    data[value][key] = "True"

        return data

    def export_table_visible_only(self, data: List[str], headers: List[str]) -> [List[str], List[str]]:
        # Get visible rows
        visible_rows = [self.proxy_model.mapToSource(self.proxy_model.index(row, 0)).row() for row in
                        range(self.proxy_model.rowCount())]

        # Get visible columns
        visible_columns = [self.proxy_model.mapToSource(self.proxy_model.index(0, col)).column() for col in
                           range(self.proxy_model.columnCount())]

        if self.expandable_rows:
            visible_columns = visible_columns[1:]
            visible_columns = [x - 1 for x in visible_columns]

        visible_data_to_export = []

        for index, row in enumerate(data):
            # filter out rows
            if index in visible_rows:
                # removes the columns if any columns filtered out
                # this is for future functionality as my program can't filter rows at the moment
                visible_row_data = [row[i] for i in visible_columns]
                visible_data_to_export.append(visible_row_data)

        visible_headers = [headers[i] for i in visible_columns]

        return visible_data_to_export, visible_headers

    def export_table(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Excel File", "", "Excel Files (*.xlsx);;All Files (*)",
                                                   options=options)

        if file_name:
            try:
                if self.expandable_rows:
                    columns = self.model.column_headers[1:]
                else:
                    columns = self.model.column_headers

                data = self.model.table_data.copy()
                data = self.export_table_getCheckboxes(data)
                data, columns = self.export_table_visible_only(data, columns)

                df = pd.DataFrame(data, columns=columns)
                df.to_excel(file_name, index=False)

                self.error_message_table("File Saved!", "Saved")
            except:
                self.error_message_table("ERROR, Couldn't save file!", "ERROR")

    def error_message_table(self, msg, title):
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText(msg)
        msgBox.setWindowTitle(title)
        msgBox.setStandardButtons(QMessageBox.Ok)
        msgBox.exec_()

    # a print check to see whether columns integers picked for these arguments passed are the same, AS THIS WILL CAUSE A CRASH
    def column_arguments_same(self):
        # check to make sure these 3 arguments do not contain the same column numbers, print error if so, because
        # if they have the same columns, it causes crashes
        error = False
        if self.editable_columns and self.datetime_columns:
            common_elements_check1 = set(self.editable_columns) & set(self.datetime_columns)
            if common_elements_check1:
                error = True
        if self.editable_columns and self.columns_with_checkboxes:
            common_elements_check2 = set(self.editable_columns) & set(self.columns_with_checkboxes)
            if common_elements_check2:
                error = True
        if self.datetime_columns and self.columns_with_checkboxes:
            common_elements_check3 = set(self.datetime_columns) & set(self.columns_with_checkboxes)
            if common_elements_check3:
                error = True

        if error:
            print("ERROR, Cannot have same columns for editable columns, columns with checkboxes or datetime columns, THIS WILL CAUSE A CRASH")

    def footer(self):
        self.footer_widget = QWidget(self)
        stylesheet = "background-color: lightgrey;"
        self.footer_widget.setStyleSheet(stylesheet)

        if self.footer_values:
            # create footer lineedits
            self.footer_row_items()
            self.footer_item_update_positions()

            for i in self.footer_values:
                self.setFooterValue(i)

            self.footer_position()
            self.footer_widget.show()

    # for adding row data numbers if float value
    def try_float(self, s):
        integer = s.isdigit()
        if not integer:
            try:
                return float(s)
            except ValueError:
                pass

    def setFooterValue(self, column: int):
        footer_edit = self.footer_row_boxes[column]

        if self.columns_with_checkboxes and column in self.footer_values.keys() and column not in self.columns_with_checkboxes \
                or not self.columns_with_checkboxes and column in self.footer_values.keys():
            value = self.footer_values[column]
            if "total" in value.lower():
                footer_edit.setText(str(self.proxy_model.rowCount()))

            if "sum" in value.lower():
                # Get column data for visible rows

                visible_rows = [self.indexFromProxytoSource(row, column).row() for row in range(self.proxy_model.rowCount())]
                column_data = [self.model.data(self.model.index(row, column)) for row in visible_rows]

                # add up any integer or float values to get total for footer
                integer_total = sum(int(s) for s in column_data if s.isdigit())
                all_floats = sum(value for s in column_data if (value := self.try_float(s)) is not None)
                total = integer_total + all_floats

                footer_edit.setText(str(total))

        # total checked boxes, taking into account any removed via filters
        elif self.columns_with_checkboxes and column in self.columns_with_checkboxes:
            delegate = self.itemDelegate()

            all_checked_rows = delegate.checked_indexes_rows

            # check to make sure checked_indexes_rows dict has anything in it
            if all_checked_rows:
                checked_rows = delegate.checked_indexes_rows[column]

                visible_rows = [self.indexFromProxytoSource(row, column).row() for row in range(self.proxy_model.rowCount())]
                non_visible_checked_rows = set(checked_rows) - set(visible_rows)

                total = set(checked_rows) - non_visible_checked_rows

                footer_edit.setText(str(len(total)))
            else:
                footer_edit.setText("0")

    def footer_row_items(self):
        for i in range(self.proxy_model.columnCount()):
            line = QLineEdit(self.footer_widget)
            line.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            style_sheet = "QLineEdit {font-weight: bold; font-size: 9px;}"
            line.setStyleSheet(style_sheet)
            line.setReadOnly(True)
            self.footer_row_boxes.append(line)

            if i not in self.footer_values.keys():
                line.hide()

    def footer_item_update_positions(self):
        if self.footer_show:
            padding = 2
            x = self.verticalHeader().width()

            # get logical indexes of the headers to put footer row widgets in correct spot
            logical_indices = [self.header.logicalIndex(i) for i in range(self.header.count())]

            for i in range(self.proxy_model.columnCount()):
                try:
                    edit_box = self.footer_row_boxes[logical_indices[i]]
                    proxy_width = self.columnWidth(logical_indices[i])

                    edit_box.setGeometry(x+padding, padding, proxy_width-padding-padding,  self.footer_height-padding-padding)
                    x += proxy_width
                except:
                    print("ERROR index of proxy_model outside of footer_row_boxes variable")

    def footer_position(self):
        # take into account vertical header width, as i want footer to overlay on top of vertical header
        vertical_header_width = self.verticalHeader().width()

        view_size = self.viewport().size()
        view_position = self.viewport().mapToParent(QPoint(0, 0))

        combined_column_width = sum(self.columnWidth(col) for col in range(self.proxy_model.columnCount()))
        footer_width = min(combined_column_width, view_size.width())

        self.footer_widget.setFixedWidth(footer_width+vertical_header_width)
        self.footer_widget.setFixedHeight(self.footer_height)
        self.footer_widget.move(view_position.x()-vertical_header_width, view_position.y()+view_size.height())

    def display_filter_setup(self):
        padding = 4
        vertical_header_width = self.verticalHeader().width()

        self.filter_widget = QWidget(self)
        stylesheet = "background-color: darkgrey;"
        self.filter_widget.setStyleSheet(stylesheet)

        # create footer lineedits
        self.filter_widget_combo = QComboBox(self.filter_widget)
        self.filter_widget_combo.setFocusPolicy(Qt.NoFocus)

        self.filter_clear_button = QPushButton(self.filter_widget)
        self.filter_clear_button.setText("X")
        self.filter_clear_button.setMinimumWidth(0)
        self.filter_clear_button.setMinimumHeight(0)
        self.filter_clear_button.setFixedSize(13, 13)
        self.filter_clear_button.clicked.connect(self.display_filter_remove)

        self.filter_widget_label = QLabel(self.filter_widget)

        self.filter_widget_combo.setGeometry(vertical_header_width, padding, 19, 20)
        self.filter_clear_button.move(vertical_header_width*2 + 4, padding+3)
        self.filter_widget_label.move(vertical_header_width*3 + 10, padding+3)

        self.display_filter_position()
        self.filter_widget.hide()

    def display_filter_remove(self):
        # recheck all items in corresponding filter combobox if column in filter_dict
        for i in self.filter_dict:
            logicalindex = self.header.visualIndex(i)
            combobox = self.header.m_buttons[logicalindex]
            self.change_combo_box_checkstates(combobox, True)

        self.filter_dict.clear()

        # update filter model
        self.proxy_model.setFilterData(self.filter_dict)

        # update footer values again
        if self.footer_show:
            for i in self.footer_values:
                self.setFooterValue(i)

        self.display_filter_update()

    def display_filter_position(self):
        padding = 4
        # take into account vertical header width, as i want footer to overlay on top of vertical header
        vertical_header_width = self.verticalHeader().width()

        view_size = self.viewport().size()
        view_position = self.viewport().mapToParent(QPoint(0, 0))

        self.filter_widget.setFixedWidth(view_size.width()+vertical_header_width)
        self.filter_widget.setFixedHeight(self.filter_footer_margin_height)

        self.filter_widget_combo.setGeometry(vertical_header_width, padding, 19, 20)
        self.filter_clear_button.move(vertical_header_width * 2 + 4, padding + 3)
        self.filter_widget_label.move(vertical_header_width * 3 + 10, padding + 3)

        self.filter_widget.move(view_position.x()-vertical_header_width, view_position.y()+view_size.height()+self.footer_height)

    def display_filter_update(self):
        self.display_filter_position()

        # check if all filter items in filter_dict are empty
        count = 0
        for i in self.filter_dict:
            if len(self.filter_dict[i]) != 0:
                count +=1

        if count == 0:
            self.filter_widget_combo.clear()
            self.filter_widget_label.setText("")
            self.filter_widget_label.adjustSize()
            self.filter_widget.hide()
            self.viewport_bottom_margin = self.footer_height
            self.setViewportMargins(self.verticalHeader().size().width(), self.horizontalHeader().size().height(), 0, self.viewport_bottom_margin)
        else:
            label_text = ""
            self.filter_widget_combo.clear()

            for key, value in self.filter_dict.items():

                header_label = self.model.headerData(key, Qt.Horizontal, Qt.DisplayRole)

                if len(value) != 0:
                    text = ", ".join(str(x) for x in value)

                    if len(text) > 200:
                        text = "Many....."

                    combo_item = str(header_label) + " = " + text
                    self.filter_widget_combo.addItem(combo_item)

                    label = "(" + combo_item + ")  "
                    label_text += label

            # reset combobox max size width
            max_width = 0
            for i in range(self.filter_widget_combo.count()):
                width = self.filter_widget_combo.fontMetrics().width(self.filter_widget_combo.itemText(i))
                max_width = max(max_width, width)

            if max_width > 1000:
                max_width = 1000

            self.filter_widget_combo.view().setFixedWidth(max_width+20)

            self.filter_widget_label.setText(label_text)
            self.filter_widget_label.adjustSize()
            self.filter_widget.show()

            self.viewport_bottom_margin = self.footer_height + self.filter_footer_margin_height
            self.setViewportMargins(self.verticalHeader().size().width(), self.horizontalHeader().size().height(), 0, self.viewport_bottom_margin)

    # for resetting the in-column searching, should only reset when column changes
    def handleCurrentChanged(self, current, previous):
        if current.column() != previous.column():
            self.search_text = ""

    # to support in-column searching in qtableview
    def handleLineEditKeyPress(self, line_edit, event):
        current_index = self.currentIndex()
        model_index = self.indexFromProxytoSource(current_index.row(), current_index.column())

        # only non editable columns can be searched
        if event.text() and self.editable_columns and model_index.column() not in self.editable_columns:
            if event.key() == Qt.Key_Backspace:
                self.search_text = self.search_text[:-1]
                line_edit.setSelection(0, len(self.search_text))
            else:
                self.find_search_result(current_index, line_edit, event.text())

        # if all columns are editable
        elif event.text() and not self.editable_columns:
            if event.key() == Qt.Key_Backspace:
                self.search_text = self.search_text[:-1]
                line_edit.setSelection(0, len(self.search_text))
            else:
                self.find_search_result(current_index, line_edit, event.text())

    # find row for searches
    def find_search_result(self, view_index: QModelIndex, line_edit: QLineEdit, key_value: str):
        index = self.indexFromProxytoSource(view_index.row(), view_index.column())
        column = index.column()

        proxy_index_rows_found = []
        temp_search_value = self.search_text + key_value

        # iterate through model data to find matches
        for row in range(self.model.rowCount()):
            model_index = self.model.index(row, column)
            data = self.model.data(model_index, Qt.DisplayRole)

            # check for any matches from abstract model to search string
            if temp_search_value.upper() == data[:len(temp_search_value)].upper():

                # check if row is visible in the proxy model
                proxy_index = self.proxy_model.mapFromSource(model_index)

                if proxy_index.isValid():
                    proxy_index_rows_found.append(proxy_index.row())

        if len(proxy_index_rows_found) != 0:
            self.search_text += key_value
            update_index = self.proxy_model.index(proxy_index_rows_found[0], view_index.column())
            self.setCurrentIndex(update_index)
            self.on_cell_clicked(update_index)

            self.set_current_editor.setSelection(0, len(self.search_text))

    # update combobox filters on data changed and footer value
    def model_data_changed(self, index_top_left, index_bottom_right: QModelIndex = None, roles=None):

        # update footer value
        if self.footer_show:
            if index_top_left.column() in self.footer_values:
                self.setFooterValue(index_top_left.column())

        new_value = index_top_left.data(Qt.DisplayRole)

        # switch to visual column as my header combo buttons mapping are switched to visual indexes in the qheaderview
        # for when columsn are switched around
        visual = self.header.visualIndex(index_top_left.column())
        button = self.header.m_buttons[visual]
        self.header.set_combo_column_filter_items(visual, button, alter_already_set_filter=True, altered_value=new_value)

    # set text alignments and add columns with checkboxes
    def setDelegates(self):
        button_delegate = ButtonDelegate(self.checked_indexes_rows, self.columns_with_checkboxes, self.editable_columns,\
                                         self.datetime_columns, self.expandable_rows, self.dblclick_edit_only, self)
        button_delegate.onexpansionChange.connect(self.expansion_clicked)
        button_delegate.oncheckboxstateChange.connect(self.checkboxstateChange)
        button_delegate.oneditorStarted.connect(self.update_vertical_header_arrow_and_editor)
        button_delegate.keyPressed.connect(self.handleLineEditKeyPress)
        button_delegate.datekeyPressed.connect(self.handleDateeditKeyPress)
        button_delegate.cleardatekeyPressed.connect(self.handleDateeditKeyPress)

        self.setItemDelegate(button_delegate)

    def handleDateeditKeyPress(self, dateEdit):
        self.commitData(dateEdit)
        self.closeEditor(dateEdit, QAbstractItemDelegate.NoHint)

    # for updating what's filtered when checkbox state changes
    def checkboxstateChange(self, column: int, row: int, checkbox_state: str):
        #  update footer row data
        if self.footer_show:
            self.setFooterValue(column)

        # reset search text if checkbox column is clicked on.. this has to be done because selection model doesn't activate
        # due to overriding the cell paint with the styleditemddelegate
        self.search_text = ""

        delegate = self.itemDelegate()
        checked_rows = delegate.checked_indexes_rows
        # update filter model
        self.proxy_model.setFilterData(self.filter_dict, checked_rows)

        # update tables if row with table gets filtered
        self.onfilterChange_sub_tables()

        # update sql database if that option chosen
        self.sql_value_change.emit(row, column, checkbox_state)

    @pyqtSlot(QSize)
    def handle_parent_resize(self, size):
        self.resize(size)

    def resizeEvent(self, event):
        self.update_sub_table_positions()
        # viewport margins change needs to be in resize event or margin won't remain
        self.setViewportMargins(self.verticalHeader().size().width(), self.horizontalHeader().size().height(), 0, self.viewport_bottom_margin)
        super(CustomTableView, self).resizeEvent(event)

    def horizontal_header_setup(self):
        self.header = ButtonHeaderView(self, self.expandable_rows, self.app)
        self.setHorizontalHeader(self.header)

        self.header.combofilteritemClicked.connect(self.onfilterChange)
        self.header.onupdateFooter.connect(self.footer_item_update_positions)

        # Set your desired background color for vertical headers using a stylesheet
        stylesheet = "QHeaderView::section:horizontal {background-color: lightgray; border: 1px solid gray;},"
        self.horizontalHeader().setStyleSheet(stylesheet)

        self.horizontalHeader().setSortIndicatorShown(True)
        self.horizontalHeader().sortIndicatorChanged.connect(self.sortColumn)
        self.horizontalHeader().setSectionsMovable(True)
        self.horizontalHeader().setMaximumHeight(18)
        self.horizontalHeader().setSectionsClickable(True)
        self.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)

    def vertical_header_setup(self):
        self.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.verticalHeader().setMinimumSectionSize(5)
        self.verticalHeader().setMaximumWidth(18)
        self.verticalHeader().setDefaultSectionSize(20)
        self.verticalHeader().setTextElideMode(Qt.ElideNone)

        # Set your desired background color for vertical headers using a stylesheet
        stylesheet = """
            QHeaderView::section:vertical {
                background-color: lightgray;
                border: 1px solid gray; /* Adjust the border width and color as needed */
            }, 
        """
        self.verticalHeader().setStyleSheet(stylesheet)
        self.verticalHeader().sectionClicked.connect(self.update_row_selection)

    def mouseMoveEvent(self, event):

        # hide any header combobox buttons if the mouse is in the qtablewidget.  There's logic to hide comboboxes,
        # in the header class, however it only works for when mouse moves between headers, Need to have in here as well
        #, otherwise, if mouse hovering over a header to display the combobox, then moves down to the table, the combobox won't hide
        try:
            for button in self.header.m_buttons:
                button.hide()
        except:
            pass

        super().mouseMoveEvent(event)

    def sortColumn(self, column, order=Qt.AscendingOrder):
        # Sort the data based on the specified column and order
        delegate = self.itemDelegate()

        if self.columns_with_checkboxes and column in self.columns_with_checkboxes:
            checked_rows = delegate.checked_indexes_rows[column]
            checked_rows.sort()

            temp_copy = checked_rows.copy()

            for i in range(self.model.rowCount()):
                if i not in temp_copy:
                    temp_copy.append(i)

            sort_dict = {column: temp_copy}
            self.proxy_model.cust_sort_order = sort_dict

        self.proxy_model.sort(column, order)
        self.update_sub_table_positions_timer()

    # i should probably break up all these if statements into their own function and put the functions in a
    # dict and call the functions in the dict as needed.... but too lazy to do that at the moment...
    # and don't want more functions
    def onfilterChange(self, filter_value: str, combo_index: int, column_clicked: int, combobox: QComboBox):
        delegate = self.itemDelegate()
        checked_rows = delegate.checked_indexes_rows

        if combo_index == 0 and filter_value == "All":
            try:
                self.filter_dict[column_clicked].clear()
            except:
                pass
            self.change_combo_box_checkstates(combobox, True)

        elif combo_index == 1 and filter_value == "Clear":
            base_range = 4
            if self.columns_with_checkboxes and column_clicked in self.columns_with_checkboxes:
                base_range = 2

            self.filter_dict[column_clicked] = [combobox.itemText(i) for i in range(base_range, combobox.count())]
            self.change_combo_box_checkstates(combobox, False)

        elif combo_index == 2 and filter_value == "Show Blanks":
            try:
                self.filter_dict[column_clicked].remove("")
                self.filter_dict[column_clicked].remove(None)
            except:
                pass

        elif combo_index == 3 and filter_value == "Hide Blanks":
            if column_clicked in self.filter_dict:
                self.filter_dict[column_clicked].append("")
                self.filter_dict[column_clicked].append(None)
            else:
                self.filter_dict[column_clicked] = ["", None]

        elif column_clicked in self.filter_dict:
            if filter_value in self.filter_dict[column_clicked]:
                self.filter_dict[column_clicked].remove(filter_value)
            else:
                self.filter_dict[column_clicked].append(filter_value)
        else:
            self.filter_dict[column_clicked] = [filter_value]

        # update filter model
        self.proxy_model.setFilterData(self.filter_dict, checked_rows)

        # update footer row values when stuff gets filtered
        if self.footer_show:
            for i in self.footer_values:
                self.setFooterValue(i)

        # update filter footer on filter changes
        self.display_filter_update()

        # update tables if row with table gets filtered
        self.onfilterChange_sub_tables()

    # remove tables if the row it's on gets filtered
    def onfilterChange_sub_tables(self):
        rows_to_remove = []

        for row in self.sub_table_widgets:
            index = self.indexFromSourcetoProxy(row, 0)
            if not index.isValid():
                rows_to_remove.append(row)

        # remove widget and also update expanded_rows in the item delegate
        for row in rows_to_remove:
            delegate = self.itemDelegate()

            # remove row from expaned_rows in item delegate
            if row in delegate.expanded_rows:
                delegate.expanded_rows.remove(row)

            widget = self.sub_table_widgets[row]
            widget.deleteLater()
            del self.sub_table_widgets[row]

        # reupdate widget positions
        self.update_sub_table_positions_timer()

    # use combobox function to change the checkstates
    def change_combo_box_checkstates(self, combobox: QComboBox, check_all: bool):
        if check_all:
            combobox.check_uncheck_all_items(True)
        if not check_all:
            combobox.check_uncheck_all_items(False)

    # this is needed to due scroll bar changing before table changes so the widgets won't map to correct spots
    # introducing a timer delay fixes this
    def update_sub_table_positions_timer(self):
        # update filter combobox positions (this is mainly due to horizontal scrollbar)
        self.header.adjustPositions()

        sender = self.sender()
        if isinstance(sender, QHeaderView):
            self.footer_item_update_positions()

        # note have to check viewport margins here on scrollbar changes on loadup of window or it won't show at startup
        if self.viewportMargins().bottom() != self.viewport_bottom_margin:
            self.setViewportMargins(self.verticalHeader().size().width(), self.horizontalHeader().size().height(), 0, self.viewport_bottom_margin)

        QTimer.singleShot(10, self.update_sub_table_positions)

    # input from signal is source index
    def expansion_clicked(self, row: int, expand: bool):
        # reset search text if expansion column clicked
        self.search_text = ""

        if expand:
            self.show_sub_table_in_row(sub_table_index_row=row)
        if not expand:
            widget = self.sub_table_widgets[row]
            widget.deleteLater()
            del self.sub_table_widgets[row]

            # resetting row height needs to be based on proxy index
            index = self.indexFromSourcetoProxy(row, 0)
            self.setRowHeight(index.row(), 20)

    # for converting from source model to proxy model
    def indexFromSourcetoProxy(self, row: int, column: int) -> QModelIndex:
        index = self.model.index(row, column)
        proxy_index = self.proxy_model.mapFromSource(index)
        return proxy_index

    # for converting from proxy model to source model
    def indexFromProxytoSource(self, row: int, column: int) -> QModelIndex:
        index = self.proxy_model.index(row, column)
        model_index = self.proxy_model.mapToSource(index)
        return model_index

    # update row/header selection if you click on row (converted to source index)
    def update_row_selection(self, row: int):
        index = self.indexFromProxytoSource(row, 0)
        self.model.setVerticalHeader(index.row())

    # argument integer is source index
    def show_sub_table_in_row(self, sub_table_index_row: int):
        widget, sub_table = self.sub_table_create()
        self.sub_table_populate(sub_table_index_row, widget)

        # add widget to list of widgets currently open
        self.sub_table_widgets[sub_table_index_row] = widget
        widget.show()

        height = self.get_sub_table_Height(widget)

        # map to proxy index
        index = self.indexFromSourcetoProxy(sub_table_index_row, 0)
        self.setRowHeight(index.row(), height+15)

        self.update_sub_table_positions()

    def update_sub_table_positions(self):
        # need to map widget based on index 0 of header visual index in case user moves columns around
        # however, the row needs to be based on the proxy model index in case user sorts
        visualindex = self.header.logicalIndex(0)

        # rows based on source index
        for row, widget in self.sub_table_widgets.items():
            # row in sub_table dict is initially based off source model index, so if sort/filter needs to be
            # mapped to proxy model index for correct row to map widget to
            proxy_index = self.indexFromSourcetoProxy(row, 0)

            height = self.get_sub_table_Height(widget)
            y_position = self.verticalHeader().sectionViewportPosition(proxy_index.row())
            x_position = self.horizontalHeader().sectionViewportPosition(visualindex)

            mapped_position = self.viewport().mapToParent(QPoint(x_position-5, y_position+19))
            combined_column_width = sum(self.columnWidth(col) for col in range(self.proxy_model.columnCount()))

            widget.setFixedHeight(height+5)
            widget.setFixedWidth(combined_column_width)
            widget.move(mapped_position.x(), mapped_position.y())

        # make header on top over sub-table rows
        self.header.raise_()
        self.verticalHeader().raise_()

        # update footer position as well if footer
        if self.footer_show:
            self.footer_position()
            self.footer_widget.raise_()

        self.display_filter_position()
        self.filter_widget.raise_()

    def sub_table_create(self) -> Tuple[QWidget, QTableWidget]:
        upper_widget = mywidget(self)
        upper_widget.setContentsMargins(30, 0, 0, 0)
        upper_layout = QVBoxLayout()
        upper_layout.setContentsMargins(0, 0, 0, 10)
        sub_table = sub_TableWidget(self.add_subrow_option, self.del_subrow_option, self.subtable_datetime_columns)
        sub_table.rowdataChanged.connect(self.sub_table_items_changed)
        sub_table.onAddRowChanged.connect(self.addSubRow)
        sub_table.onDelRowChanged.connect(self.delSubRow)

        upper_layout.addWidget(sub_table)
        upper_widget.setLayout(upper_layout)
        return upper_widget, sub_table

    # update main sub table data var for qtableview when an item is changed
    def sub_table_items_changed(self, row: int, row_data: List[str], table: QTableWidget):

        # Find row index (based on key value in the dictionary that im storing the opened table widgets in)
        table_row = [key for key, value in self.sub_table_widgets.items() if value == table.parent()]

        # if row is last one in list (such as adding a row) then append, if modifying existing row then change
        # the list values
        if len(self.sub_table_data[table_row[0]]) <= row:
            # append if new row
            self.sub_table_data[table_row[0]].append(row_data)

            # update sql database if using sql for
            self.sql_addrow_subtable.emit(table_row[0], row_data)
        else:
            self.sub_table_data[table_row[0]][row] = row_data

            # update sql row if using sql
            self.sql_update_subtable.emit(table_row[0], row, row_data)

    def sub_table_populate(self, sub_table_index: int, widget: QWidget):
        table = None
        # get the qtablewidgetitem (which is in the Qwidget)
        for child_widget in widget.findChildren(QWidget):
            if isinstance(child_widget, QTableWidget):
                table = child_widget

        if len(self.model.table_data) == len(self.sub_table_data):
            if table is not None and self.sub_table_data[sub_table_index] is not None:
                try:
                    rows = len(self.sub_table_data[sub_table_index])
                    # columns = len(self.sub_table_data[sub_table_index][0])
                    columns = len(self.subtable_header_labels)
                except:
                    rows = 0
                    columns = 1

                table.setRowCount(rows)
                table.setColumnCount(columns)

                if self.subtable_header_labels:
                    try:
                        table.setHorizontalHeaderLabels(self.subtable_header_labels)
                    except:
                        table.setHorizontalHeaderLabels([""])

                 # Populate with self.sub_table_data variabled
                for row in range(rows):
                    table.setRowHeight(row, 18)
                    for col in range(columns):
                        if self.subtable_col_checkboxes and col in self.subtable_col_checkboxes:
                            widget = table.make_cell_checkbox()
                            check_value = self.sub_table_data[sub_table_index][row][col]
                            self.subtable_initial_checkbox_state(widget, check_value)
                            table.setCellWidget(row, col, widget)

                        else:
                            item = QTableWidgetItem(self.sub_table_data[sub_table_index][row][col])
                            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                            table.setItem(row, col, item)
        else:
            self.error_message_table("ERROR, sub table data does not match the number of rows of the main table data "
                                     "\n Cannot populate sub table!", "ERROR")

    def subtable_initial_checkbox_state(self, widget: QWidget, value: str):
        if widget:
            checkbox_widget = None
            # get the qtablewidgetitem (which is in the Qwidget)
            for child_widget in widget.findChildren(QWidget):
                if isinstance(child_widget, QCheckBox):
                    checkbox_widget = child_widget

            if checkbox_widget is not None:
                if value.upper() == "TRUE" or value.upper() == "T":
                    checkbox_widget.setCheckState(Qt.Checked)
                else:
                    checkbox_widget.setCheckState(Qt.Unchecked)

    def get_sub_table_Height(self, widget: QWidget) -> int:
        table = None
        # get the qtablewidgetitem (which is in the Qwidget)
        for child_widget in widget.findChildren(QWidget):
            if isinstance(child_widget, QTableWidget):
                table = child_widget

        total_height = table.horizontalHeader().height() + 25  # +25 to account for padding
        for row in range(table.rowCount()):
            total_height += table.rowHeight(row)
        return total_height

    def update_vertical_header_arrow_and_editor(self, index: QModelIndex, editor: QLineEdit = None):
        self.update_row_selection(index.row())

        if editor:
            self.set_current_editor = editor

    def on_cell_clicked(self, index: QModelIndex):
        self.update_vertical_header_arrow_and_editor(index)

        if not self.expandable_rows:
            if self.columns_with_checkboxes and index.column() not in self.columns_with_checkboxes:
                self.edit(index)
            elif not self.columns_with_checkboxes:
                self.edit(index)

        elif self.columns_with_checkboxes and index.column() not in self.columns_with_checkboxes and index.column() != 0:
            self.edit(index)

        elif not self.columns_with_checkboxes and index.column() != 0:
            self.edit(index)

        # FIX THIS BECAUSE THE 1st COLUMN CAN"T BE EDITED


        # activate editor on cell click
      #  if self.columns_with_checkboxes and index.column() not in self.columns_with_checkboxes and index.column() != 0 \
      #          or not self.columns_with_checkboxes and index.column() != 0:
      #      self.edit(index)

        # this is to support the header repaint/sort not being run on the first click out of qcombox popups
        if self.header.sectionsClickable() == True:
            self.header.outof_combo_popup += 1
        # Handle cell clicked event here
       # print("Cell clicked at row:", index.row(), "column:", index.column())

    def delMainRowMsg(self, row: int):
        if row != -1:
            reply = QMessageBox.question(self, 'Delete Row', 'Delete current row selected?',
                                         QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Cancel)

            if reply == QMessageBox.Ok:
                self.delMainRow(row)
            else:
                pass

    def delMainRow(self, row: int):
        index = self.indexFromProxytoSource(row, 0)

        self.model.removeRow(index.row())

        # update checkbox rows when 1 is deleted for the delegate and updated expanded_rows columns if any rows are expanded
        if self.columns_with_checkboxes:
            delegate = self.itemDelegate()

            # update check_indexes var in delegate
            for col, rows in delegate.checked_indexes_rows.items():
                if index.row() in rows:
                    rows.remove(index.row())

                # update row indexes
                updated_rows = [x-1 if x > index.row() else x for x in rows]
                delegate.checked_indexes_rows[col] = updated_rows

            # update expanded_row var in delegate
            if index.row() in delegate.expanded_rows:
                delegate.expanded_rows.remove(index.row())

            updated_rows = [x-1 if x > index.row() else x for x in delegate.expanded_rows]
            delegate.expanded_rows = updated_rows

        # reset footer values
        columns = self.model.columnCount()
        if self.footer_show:
            for col in range(columns):
                self.setFooterValue(col)

        # repopulate filter dropdowns
        self.header.populate_filter_dropdown()

        # delete the corresponding sub-table data that is no longer needed for the main table row
        del self.sub_table_data[row]

        # update any sub table widgets on screen
        if self.expandable_rows:
            if index.row() in self.sub_table_widgets:
                widget = self.sub_table_widgets[index.row()]
                widget.deleteLater()
                del self.sub_table_widgets[index.row()]

            keys_to_update = [key for key in self.sub_table_widgets.keys() if key > index.row()]
            # sort first otherwise the following for loop wont' work correctly
            keys_to_update.sort()

            for key in keys_to_update:
                new_key = key - 1
                self.sub_table_widgets[new_key] = self.sub_table_widgets[key]
                del self.sub_table_widgets[key]

        # update table positions if any on screen
        self.update_sub_table_positions_timer()

        self.sql_del_row.emit(index.row())

    def addMainRowMsg(self, row: int):
        reply = QMessageBox.question(self, 'Add Row', 'Add new row to end of table?',
                                     QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Cancel)

        if reply == QMessageBox.Ok:
            self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
            self.addMainRow()
        else:
            pass

    def addMainRow(self):
        header_labels = []
        for i in range(self.model.columnCount()):
            header_labels.append(self.model.headerData(i, Qt.Horizontal, Qt.DisplayRole))

        title = "Enter row data to add"

        self.row_dialog = addRowMaintable_window(self, self.model.columnCount(), self.columns_with_checkboxes,
                                                 self.datetime_columns, self.expandable_rows, header_labels, title)
        self.row_dialog.onaddRowChanged.connect(self.addMainRowUpdate)
        self.row_dialog.exec()

    def addMainRowUpdate(self, values: list, existing_row_change: int = None):

        if existing_row_change == None:
            self.model.insertRow(values)

            # add row to end of table
            row = self.model.rowCount()-1

        if existing_row_change != None:
            row = existing_row_change
            self.model.table_data[row] = values

            # for updating all values of sql row if sql being used
            for index, value in enumerate(values):
                self.onsql_rowChange.emit(row, index, value)

        # if there's checkboxes in table set checkstates for new row
        if self.columns_with_checkboxes:
            # get checkboxed rows from the delegate as i will need to add to this the new checkboxes that are checked
            delegate = self.itemDelegate()
            for col, rows in delegate.checked_indexes_rows.items():
                if self.expandable_rows and "TRUE" in values[col-1].upper():
                    if row not in rows:
                        delegate.checked_indexes_rows[col].append(row)

                elif self.expandable_rows and "FALSE" in values[col-1].upper():
                    if row in rows:
                        delegate.checked_indexes_rows[col].remove(row)

                elif not self.expandable_rows and "TRUE" in values[col].upper():
                    if row not in rows:
                        delegate.checked_indexes_rows[col].append(row)

                elif not self.expandable_rows and "FALSE" in values[col].upper():
                    if row in rows:
                        delegate.checked_indexes_rows[col].remove(row)

        # update footer and filter comboboxes
        columns = self.model.columnCount()
        for col in range(columns):
            index = self.model.index(row, col)
            self.model_data_changed(index)

        if existing_row_change == None:
            # add to sub_table_data
            if self.expandable_rows:
                self.sub_table_data.append([])

            # update positions of tables if any on screen
            self.update_sub_table_positions_timer()

            self.sql_add_row.emit(values)

    def addSubRow(self, table: QTableWidget = None):
        # get row with the subtable widget
        row_selected = -1
        widget = table.parent()
        for key, value in self.sub_table_widgets.items():
            if value == widget:
                row_selected = key

        if table:
            header_labels = [table.horizontalHeaderItem(col).text() for col in range(table.columnCount())]
            checkbox_columns = self.subtable_col_checkboxes
            row_data = []
            index = table.rowCount()

            for col in range(table.columnCount()):
                row_data.append("")

            table.insertRow(index)
            table.setRowHeight(index, 18)

            # add new row to subtable data
            # self.sub_table_items_changed(index, row_data, table)

            table.sub_table_adjust(table, index, row_data)

            # below code will update the new row
            # add checkboxes to new row
            if self.subtable_col_checkboxes:
                for i in self.subtable_col_checkboxes:
                    checkbox = table.make_cell_checkbox()
                    table.setCellWidget(index, i, checkbox)

            self.dlg = sub_table_window(self, table, index, row_data, checkbox_columns, header_labels, self.subtable_datetime_columns)
            self.dlg.onsubtableChange.connect(table.sub_table_adjust)
            self.dlg.exec()

            # fix row height in main table
            height = self.get_sub_table_Height(table.parent())

            # map to proxy index
            index = self.indexFromSourcetoProxy(row_selected, 0)
            self.setRowHeight(index.row(), height+15)

    def delSubRow(self, table: QTableWidget, row: int):
        table.removeRow(row)

        # get row with the subtable widget
        row_selected = -1
        widget = table.parent()
        for key, value in self.sub_table_widgets.items():
            if value == widget:
                row_selected = key

        # remove row from sub_table data
        del self.sub_table_data[row_selected][row]

        # fix row height in main table
        height = self.get_sub_table_Height(table.parent())

        # map to proxy index and set row height
        index = self.indexFromSourcetoProxy(row_selected, 0)
        self.setRowHeight(index.row(), height+15)

        self.sql_delrow_subtable.emit(row_selected, row)

    def reset_table(self, keep_filter=False):
        self.model.table_data = []
        self.model.removeRows(0, self.model.rowCount())

        self.proxy_model.invalidate()
        # Reset the proxy model
        self.proxy_model.setSourceModel(self.model)

        # clear out delegate variables
        delegate = self.itemDelegate()

        if delegate.checked_indexes_rows:
            for key, values in delegate.checked_indexes_rows.items():
                delegate.checked_indexes_rows[key] = []
            delegate.expanded_rows.clear()

        if not keep_filter:
            self.proxy_model.filter_dict.clear()
            self.proxy_model.filter_checked_rows.clear()
            self.proxy_model.cust_sort_order.clear()
            self.filter_dict = {}
            self.filter_checked_rows = {}

        # empty out combobox filter dropdowns
        self.header.populate_filter_dropdown()

        # reset footer values
        if self.footer_show and self.footer_values:
            for i in self.footer_values:
                self.setFooterValue(i)

        # clear out any subtable data
        if self.sub_table_data:
            self.sub_table_data.clear()
            self.sub_table_widgets.clear()

        self.reset()


# for sub_table widget
class mywidget(QWidget):
    def __init__(self, table_view):
        super(mywidget, self).__init__(parent=table_view)
        self.table_view = table_view

    def wheelEvent(self, event):
        scrollbar = self.table_view.verticalScrollBar()
        if scrollbar.isVisible():
            modifiers = event.modifiers()
            # don't ask me how qwheelevent works... i used AI to construct this for me lol... in order
            # to pass wheel event in the qwidget to the table view so that scrolling in the widget actually scrolls
            # the table
            new_event = QWheelEvent(event.pos(), event.globalPos(), event.pixelDelta(), event.angleDelta(), event.buttons(),
                                    modifiers, event.phase(), event.inverted())
            QCoreApplication.sendEvent(scrollbar, new_event)


# custom delegate for combo box items just to change the spacing in the combobox
class ComboCustomDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        size.setHeight(20)  # Adjust the height as needed
        return size


class ComboBox(QComboBox):
    # emit a signal whenever qcombobox popup is open/closed, this is so that i can set a value in parent header class
    # that will prevent the sort & repaint of the arrow being drawn for the sort on the first mouse click in the header
    # while a qcombobox is open
    popupOpened = pyqtSignal()
    itemClicked = pyqtSignal(str, int, int, object)

    def __init__(self, parent, app: QApplication):
        super().__init__(parent=parent)
        self.view().pressed.connect(self.handleItemPressed)
        self.setModel(QStandardItemModel(self))

        self.app = app

        # Set a custom delegate for the view, just using it for spacing in the combobox at the moment
        delegate = ComboCustomDelegate(self)
        self.view().setItemDelegate(delegate)

        # value for keeping combo dropdown open until clicked outside of it
        self._changed = False

        self.setMouseTracking(True)

        self.view().viewport().installEventFilter(self)

    # event filter for viewport (which is the individual items in the qcombobox popup)
    # this is purely to prevent the qcomobobox from closing on doubleclicks
    def eventFilter(self, widget, event):
        if widget == self.view().viewport() and event.type() == QEvent.MouseButtonDblClick:
            self._changed = True
        return super().eventFilter(widget, event)

    def handleItemPressed(self, index):
        # dont' really like this but is the only way i can think of at the moment... get the button index
        # that was clicked on (which is dynamically altered when sections move in the parent), with that index get the logical
        # index and see if it's one of the column_checkbox indexes.  I can either do it this way or dynamically
        # update column_checkbox variable from the parent... chose this way
        # this is all to determine if the qcomobobox associated with the column is a checkbox column or not
        # doing this makes it work with section moves

        logical_index = self.parent().logicalIndex(self.parent().m_buttons.index(self))
        base_row = 4
        if self.parent().parent().columns_with_checkboxes and logical_index in self.parent().parent().columns_with_checkboxes:
            base_row = 2

        item = self.model().itemFromIndex(index)

        # send signal to qheaderview -> qtablewidget to filter table
        if item is not None:
            text = item.data(Qt.DisplayRole)
            self.itemClicked.emit(text, index.row(), logical_index, self)

        # greater than 3 as i don't want to add check marks to first 2 items in the dropdown of combobox
        if item is not None and index.row() >= base_row:
            if item.checkState() == Qt.Checked:
                item.setCheckState(Qt.Unchecked)
            else:
                item.setCheckState(Qt.Checked)

        self._changed = True

    # set combo popup max height based on how many items (max 15)
    def combo_dropdown_height(self, total_items):
        # set max to 15
        if total_items > 17:
            total_items = 17
        self.setMaxVisibleItems(total_items)

    def hidePopup(self):
        if not self._changed:
            super(ComboBox, self).hidePopup()
        self._changed = False

    def showPopup(self):
        # get animation status for combobox, then set it to false
        # this must be done, otherwise the combobox will appear in 1 location and then snap to the custom placement
        # afterwards because of the animation effect
        oldanimation = self.app.isEffectEnabled(Qt.UI_AnimateCombo)
        self.app.setEffectEnabled(Qt.UI_AnimateCombo, False)
        super().showPopup()
        self.app.setEffectEnabled(Qt.UI_AnimateCombo, oldanimation)

        pos = QPoint()
        # drop down frame of combobox
        frame = self.findChild(QFrame)

        # get parent location as starting location for where to change drop down to
        parent_location = frame.parent().mapToGlobal(pos)

        # set custom combobox dropdown location
        frame.move(parent_location.x() - frame.width() + self.width(), parent_location.y() + self.height())

        self.popupOpened.emit()

    # for combobox all or clear filter options
    def check_uncheck_all_items(self, check_all: bool):
        logical_index = self.parent().logicalIndex(self.parent().m_buttons.index(self))
        base_row = 4
        if self.parent().parent().columns_with_checkboxes and logical_index in self.parent().parent().columns_with_checkboxes:
            base_row = 2

        if check_all:
            for i in range(base_row, self.count()):
                index = self.model().index(i, 0)
                item = self.model().itemFromIndex(index)

                if item is not None:
                    item.setCheckState(Qt.Checked)

        if not check_all:
            for i in range(base_row, self.count()):
                index = self.model().index(i, 0)
                item = self.model().itemFromIndex(index)

                if item is not None:
                    item.setCheckState(Qt.Unchecked)


class ButtonHeaderView(QHeaderView):
    combofilteritemClicked = pyqtSignal(str, int, int, object)
    onupdateFooter = pyqtSignal()

    def __init__(self, parent, expandable_rows, app: QApplication):
        super().__init__(Qt.Horizontal, parent=parent)  # Adjust orientation to Horizontal

        self.app = app

        self.m_buttons = []
        # this dict is to attach an index value to each button for when sections are moved around by user
        # in order to properly rearrange the comboboxes... only way i could figure out how to do this, all other methods failed
        self.m_buttons_index_attachments = {}

        self.expandable_rows = expandable_rows

        self.sectionResized.connect(self.adjustPositions)
        self.sectionMoved.connect(self.onSectionMovedChanged)
        self.sectionCountChanged.connect(self.onSectionCountChanged)

        # var so that the first click out of combobox on the table headers won't trigger resorting of table
        self.outof_combo_popup = 0

    # this will prevent the sort & repaint of the arrow being drawn for the sort on the first mouse click in the header
    # while a qcombobox is open
    def first_mouse_click_outof_combo_popup(self):
        self.outof_combo_popup = 0
        self.setSectionsClickable(False)

    def mouseReleaseEvent(self, event):
        # this will prevent the sort & repaint of the arrow being drawn for the sort on the first mouse click in the header
        # while a qcombobox is open
        if not self.sectionsClickable():
            self.outof_combo_popup += 1
            if self.outof_combo_popup > 1:
                self.outof_combo_popup = 0
                self.setSectionsClickable(True)

        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        logical_index = self.logicalIndexAt(event.pos())
        visual_index = self.visualIndex(logical_index)

        expansions = False
        if logical_index == 0 and self.expandable_rows:
            expansions = True

        # hide combo buttons if they aren't being hovered over or show if being hovered over (NOTE THIS IS FOR THE
        # COMBO ARROW not for the combobox popup
        for button in self.m_buttons:
            if self.m_buttons.index(button) == visual_index:
                if not expansions:
                    button.show()
            else:
                button.hide()

        # must keep super to inherit mousemoveevent functionality in order to keep functionality for user moving columns
        super().mouseMoveEvent(event)

    # reset values when sections moved
    def onSectionMovedChanged(self):

        # use this code to match m_buttons with logicalindexes, this for when user moves columns around
        # get all logical indexes as a list
        logical_indices = [self.logicalIndex(i) for i in range(self.count())]

        # reset m_button order based on logical indices
        self.m_buttons.clear()
        self.m_buttons.extend(self.m_buttons_index_attachments[i] for i in logical_indices)

        self.adjustPositions()
        self.onupdateFooter.emit()

    @pyqtSlot()
    # reset comboboxes when table columns change
    def onSectionCountChanged(self):
        self.m_buttons_index_attachments.clear()

        while self.m_buttons:
            button = self.m_buttons.pop()
            button.deleteLater()

        for i in range(self.count()):
            # Draw button in header
            button = ComboBox(self, self.app)
            button.popupOpened.connect(self.first_mouse_click_outof_combo_popup)
            button.itemClicked.connect(self.filter_item_clicked)

            # focus policy removes the box that shows current selection
            button.setFocusPolicy(Qt.NoFocus)
            button.setStyleSheet("background-color: lightgrey;")
            button.hide()

      #      self.adjustDropdownWidth(button)
            self.m_buttons.append(button)
            self.m_buttons_index_attachments[i] = button
            self.update_data()
            self.adjustPositions()

        self.populate_filter_dropdown()

    # pass values to qtableview to enter into dict and change qproxyfilter
    def filter_item_clicked(self, value: str, combo_index: int, column_clicked: int, combobox: QComboBox):
        self.combofilteritemClicked.emit(value, combo_index, column_clicked, combobox)

    @pyqtSlot()
    # adjust positions for qcomboboxes due to resizing/section moves
    def adjustPositions(self):
        # adjust drop down menu location in header for when resized/column changed
        for index, button in enumerate(self.m_buttons):
            # note must use logical index for sectionviewposition, otherwise the qcomboboxes will NOT change position
            # when the sections are moved by the user
            logical_index = self.logicalIndex(index)
            combo_width = 19
            combo_x = self.sectionViewportPosition(logical_index) + self.sectionSize(logical_index) - combo_width - 4
            geom = QRect(
                combo_x,
                0,
                combo_width,
                20,  # Adjust width drown down arrow
            )
            button.setGeometry(geom)

    # when headers change
    def update_data(self):
        for i, button in enumerate(self.m_buttons):
            text = self.model().headerData(i, self.orientation(), Qt.DisplayRole)

    # this is for finding which index to start off for sorting/add items to the qcomboboxes, due to the filter combos
    # boxes have different base filtering options
    def combo_base_index(self, column: int) -> int:
        base_index = 4

        if self.parent().columns_with_checkboxes and column in self.parent().columns_with_checkboxes:
            base_index = 2

        return base_index

    def set_combo_column_filter_items(self, column: int, button: QComboBox, alter_already_set_filter: bool = False, altered_value: str = None):
        visual_column = self.logicalIndex(column)
        base_index = self.combo_base_index(visual_column)

        if not alter_already_set_filter:
            if base_index == 4:

                # this complicated list comprehensions gets all item values from given column
                # column_values = [(str(self.model().data(self.model().index(row, visual_column), Qt.DisplayRole)))
                #                 for row in range(self.model().rowCount())]

                # remove_blanks = [item for item in column_values if item != ""]

                source_model = self.model().sourceModel()

                column_values = None
                if self.expandable_rows:
                    if visual_column != 0:
                        table_column = visual_column-1
                        column_values = [row[table_column] for row in source_model.table_data]
                else:
                    column_values = [row[visual_column] for row in source_model.table_data]

                if column_values:
                    remove_blanks = [item for item in column_values if item != ""]

                    # change to set to remove duplicates
                    items = set(remove_blanks)

                    item_to_list = list(items)
                    item_to_list.sort()

                    button.addItem("All")
                    button.addItem("Clear")
                    button.addItem("Show Blanks")
                    button.addItem("Hide Blanks")

                    button.addItems(item_to_list)
                    [button.setItemData(index, Qt.Checked, Qt.CheckStateRole) for index in range(base_index, button.count())]
                    button.combo_dropdown_height(len(item_to_list) + base_index)

                    self.set_filteritems_checkstates(visual_column, button)

            else:
                item_to_list = ["All", "Clear", "False", "True"]
                button.addItems(item_to_list)
                [button.setItemData(index, Qt.Checked, Qt.CheckStateRole) for index in range(base_index, button.count())]
                button.combo_dropdown_height(len(item_to_list) + base_index)

                self.set_filteritems_checkstates(visual_column, button)

            self.adjustDropdownWidth(button)

        # if values in cell altered update filter combobox
        if alter_already_set_filter and altered_value:
            # Get the items as a list
            items_list = [button.itemText(i) for i in range(button.count())]

            if altered_value not in items_list:
                # get index of where the new value would be inserted into a sorted list (this is what bisect does)
                index = bisect.bisect_left(items_list[base_index:], altered_value)

                # insert at the index into the combobox and make it checked
                button.insertItem(index+base_index, altered_value)
                button.setItemData(index+base_index, Qt.Checked, Qt.CheckStateRole)

                button.combo_dropdown_height(len(items_list) + base_index)
                self.adjustDropdownWidth(button)

    def populate_filter_dropdown(self):
        for column, button in enumerate(self.m_buttons):
            button.clear()
            self.set_combo_column_filter_items(column, button)

    # change comboxw idth based on text of the items in it
    def adjustDropdownWidth(self, combo_box):
        max_width = 0
        scrollbar_width = combo_box.view().verticalScrollBar().sizeHint().width()
        frame_width = combo_box.view().frameWidth()

        for i in range(combo_box.count()):
            width = combo_box.fontMetrics().width(combo_box.itemText(i))
            max_width = max(max_width, width)

        # set 250 for maximum width drop down
        max_dropdown_width = 250
        # padding to account for checkbox size and scrollbar
        padding = 40
        combo_box.view().setFixedWidth(min(max_width + scrollbar_width + frame_width + padding, max_dropdown_width))

    def set_filteritems_checkstates(self, column: int, button: QComboBox):
        items_list = [button.itemText(i) for i in range(button.count())]

        # this checks filter_dict in qtableview to see if there are any filter items that should be unchecked in the filter
        # drop down when changes to the state of the table happen, such as deleted a row or loading a new table
        for key, values in self.parent().filter_dict.items():
            if key == column:
                for value in values:
                    if value in items_list:
                        index = items_list.index(value)
                        button.setItemData(index, Qt.Unchecked, Qt.CheckStateRole)


# custom qframe for tableview due to bug with widgets overlapping frame of tableview
class myframe(QFrame):
    resizeSignal = pyqtSignal(QSize)

    def __init__(self):
        super(myframe, self).__init__()

        self.setObjectName("myframe")
        self.setFrameStyle(QFrame.Box | QFrame.Plain)
        self.setStyleSheet("QFrame#myframe {border: 1px solid black};")
        self.setContentsMargins(1, 1, 0, 0)

    def resizeEvent(self, event):
        # Handle the resize event of the QFrame
        super().resizeEvent(event)

        # Adjust the size of the QTableView when the QFrame is resized
        table_view_size = self.size()
        new_size = QSize(table_view_size.width()-2, table_view_size.height()-2)
        self.resizeSignal.emit(new_size)


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

        self.clear_button = QPushButton("clear")
        self.clear_button.clicked.connect(self.clear_out)

        self.main_horizontal.addStretch()
        self.main_horizontal.addWidget(self.sql_combo)
        self.main_horizontal.addWidget(self.clear_button)
        self.main_horizontal.addStretch()

        self.main_layout.addLayout(self.main_horizontal)
        self.main_widget.setLayout(self.main_layout)


        """
        start = time.time()

        # index of editable columns
      #  editable_columns = [6]

        # main table data
        rows = 20
        columns = 8

        data = []
        for row in range(rows):
            row_data = []
            for col in range(columns):
                if col == 5:
                    if row % 2 == 1:
                        row_data.append("")
                    else:
                        row_data.append(f"{row}")
                elif col == 6:
                    row_data.append("01/11/2024")

                else:
                    row_data.append(f"Row {row}, Column {col}")
            data.append(row_data)

        # which columsn to have checkboxes in instead of text
        columns_with_checkboxes = [2, 3, 4, 5]
        sub_table_columns_with_checkboxes = [3]
        self.expandable_rows = False

        # checkbox data for the columns with checkboxes (this would be replaced by grabbing data from say a sql table)
        # this is just a setup for grabbing "data" for testing purposes
        checked_indexes_rows = {}
        for i in range(len(columns_with_checkboxes)):
            checked_ones = random_indexes_for_testing(rows)
            checked_indexes_rows[columns_with_checkboxes[i]] = checked_ones

        # populate all the sub table data into a list for qtableview to access when rows are expanded
        sub_table_data = []
        for main_table_rows in range(rows):
            table_data = []
            for row in range(3):
                row_data = []
                for col in range(5):
                    if col < 2:
                        row_data.append(f'sub Row {row}, sub Col {col}')
                    if col == 2:
                        row_data.append("01/11/2024")
                    if col == 3:
                        row_data.append("True")
                    if col == 4:
                        row_data.append(f'sub Row {row}, sub Col {col}')
                table_data.append(row_data)
            sub_table_data.append(table_data)

        column_headers = []
        for i in range(columns):
            column_headers.append(f"Column {i}")

        self.columns_headers = column_headers

        sub_table_headers_labels = ["NCR No.", "Disposition", "Date", "Extra", "Completed"]

        footer_values = {1: "total", 4: "total", 6: "sum"}

      #  datetime_columns = [7]

        # custom qframe for tableview due to bug with widgets overlapping frame of tableview

        #### NOTE DATETIME COLUMNS CANNOT ALSO BE IN EDITABLE COLUMNS ARGUMENT OR CAUSES CRASH #####
        ### possible add a check to make sure editable columns, columns with checkboxes and datetime columns do not overlap
        ### with same integer numbers
        self.frame = myframe()
        self.model = LazyDataModel(data, columns_with_checkboxes, column_headers, self.expandable_rows)
        self.table_view = CustomTableView(self.app, self.model, columns_with_checkboxes, checked_indexes_rows, sub_table_data,
                                          editable_columns=None, parent=self.frame, datetime_columns=[7],
                                          footer=True, footer_values=footer_values, subtable_col_checkboxes=sub_table_columns_with_checkboxes,
                                          subtable_header_labels=sub_table_headers_labels, expandable_rows=self.expandable_rows,
                                          add_mainrow_option=True, del_mainrow_option=True, add_subrow_option=True, del_subrow_option=True,
                                          subtable_datetime_columns=[2], dblclick_edit_only=False)

        self.main_layout.addWidget(self.frame)

        self.setCentralWidget(self.main_widget)  # Set the QTableView as the central widget

        end = time.time()
        print(end-start)
        """

        self.no_data_table_test()
        self.table_test_column_headers()
        self.table_test_new_data()


    def no_data_table_test(self):
        self.frame = myframe()
        self.model = LazyDataModel()
        self.table_view = CustomTableView(self.app, self.model, parent=self.frame)
        self.main_layout.addWidget(self.frame)
        self.setCentralWidget(self.main_widget)

    def table_test_column_headers(self):
        self.table_view.reset_table()
        self.table_view.model.update_headers(["Column 1", "Column 2"])

    def table_test_new_data(self):
        test_data = [["a", "b"], ["c", "d"]]
        self.table_view.model.beginResetModel()
        self.table_view.model.table_data = test_data


        print(self.table_view.model.table_data)

        self.table_view.model.endResetModel()
        self.table_view.header.populate_filter_dropdown()
        self.table_view.resizeColumnsToContents()

    def clear_out(self):
        self.table_view.reset_table()


class sub_TableWidget(QTableWidget):
    rowdataChanged = pyqtSignal(int, list, object)
    onAddRowChanged = pyqtSignal(object)
    onDelRowChanged = pyqtSignal(object, int)

    def __init__(self, add_subrow_option, del_subrow_option, subtable_datetime_columns):
        super(sub_TableWidget, self).__init__()

        self.add_subrow_option = add_subrow_option
        self.del_subrow_option = del_subrow_option
        self.subtable_datetime_columns = subtable_datetime_columns

      #  self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setAlternatingRowColors(True)
        self.horizontalHeader().setMaximumHeight(18)

        self.verticalHeader().sectionClicked.connect(self.sub_table_clicked)

        stylesheet = "QHeaderView::section {background-color: lightgray;} QTableWidget {alternate-background-color: lightgrey;}"
        self.setStyleSheet(stylesheet)

        self.horizontalHeader().setSectionsClickable(False)

        if self.add_subrow_option or self.del_subrow_option:
            vheader = self.verticalHeader()
            vheader.setContextMenuPolicy(Qt.CustomContextMenu)
            vheader.customContextMenuRequested.connect(self.show_context_menu)

            hheader = self.horizontalHeader()
            hheader.setContextMenuPolicy(Qt.CustomContextMenu)
            hheader.customContextMenuRequested.connect(self.show_context_menu)

       # new_table.horizontalHeader().setVisible(False)
       # new_table.verticalHeader().setVisible(False)

    def show_context_menu(self, position):
        vertical_header = self.verticalHeader()
        index = vertical_header.logicalIndexAt(position)

        self.clearSelection()
        self.selectRow(index)

        menu = QMenu(self)

        # Add actions or other menu items as needed
        if self.del_subrow_option:
            delete = QAction(f"Delete Current SubTable Row", self)
            delete.triggered.connect(lambda: self.subDelRow(index))
            menu.addAction(delete)
        if self.add_subrow_option:
            add = QAction(f"Add New SubTable Row", self)
            add.triggered.connect(self.subAddRow)
            menu.addAction(add)

        # Show the context menu at the specified position
        menu.exec_(self.mapToGlobal(position))

    def sub_table_clicked(self, index):
        sender = self.sender()

        header_labels = [sender.parent().horizontalHeaderItem(col).text() for col in range(sender.parent().columnCount())]
        checkbox_columns = []
        row_data = []

        for col in range(sender.parent().columnCount()):
            # check if cell widget
            widget = self.cellWidget(index, col)
            if not widget:
                item = sender.parent().item(index, col).text()
                row_data.append(str(item))
            else:
                if widget:
                    checkbox_widget = None
                    for child_widget in widget.findChildren(QWidget):
                        if isinstance(child_widget, QCheckBox):
                            checkbox_widget = child_widget

                    if checkbox_widget:
                        checkbox_columns.append(col)
                        row_data.append(str(checkbox_widget.isChecked()))

        self.dlg = sub_table_window(self, sender.parent(), index, row_data, checkbox_columns, header_labels, self.subtable_datetime_columns)
        self.dlg.onsubtableChange.connect(self.sub_table_adjust)
        self.dlg.exec()

    def sub_table_adjust(self, table: QTableWidget, row: int, row_data: List[str]):
        for col in range(table.columnCount()):
            # check if cell widget
            widget = self.cellWidget(row, col)
            if not widget:
                item = QTableWidgetItem(row_data[col])
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                table.setItem(row, col, item)
            else:
                if widget:
                    checkbox_widget = None
                    for child_widget in widget.findChildren(QWidget):
                        if isinstance(child_widget, QCheckBox):
                            checkbox_widget = child_widget

                    if checkbox_widget:
                        if row_data[col].upper() == "TRUE" or row_data[col].upper() == "T":
                            checkbox_widget.setCheckState(Qt.Checked)
                        else:
                            checkbox_widget.setCheckState(Qt.Unchecked)

        # send to parent to change the subtable data variable
        self.rowdataChanged.emit(row, row_data, self)

    def make_cell_checkbox(self) -> QWidget:
        upper_widget = QWidget()
        upper_widget.setContentsMargins(0, 0, 0, 0)
        upper_layout = QVBoxLayout()
        upper_layout.setContentsMargins(0, 0, 0, 0)
        upper_layout.setAlignment(Qt.AlignCenter)
        checkbox = QCheckBox("")

        # make checkbox readonly essentially
        checkbox.setAttribute(Qt.WA_TransparentForMouseEvents)
        checkbox.setFocusPolicy(Qt.NoFocus)

        checkbox.stateChanged.connect(lambda state, checkbox=checkbox: self.checkbox_value_changed(state))
        upper_layout.addWidget(checkbox)
        upper_widget.setLayout(upper_layout)
        return upper_widget

    # not used for anything at the moment, will be used when this is connected with a SQL database to update dateabase
    @pyqtSlot()
    def checkbox_value_changed(self, state: int):
        # get to the Qwidget item (which is the parent), as this is what i need to figure out what row it's in
        widget = self.sender().parent()
        row = self.indexAt(widget.pos()).row()
        col = self.indexAt(widget.pos()).column()

        #  print(widget)
        #  print(row, col)

    def subAddRow(self):
        reply = QMessageBox.question(self, 'Add Row', 'Add new row to end of sub-table?',
                                     QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Cancel)

        if reply == QMessageBox.Ok:
            self.onAddRowChanged.emit(self)
        else:
            pass

    def subDelRow(self, index: int):
        if index != -1:
            reply = QMessageBox.question(self, 'Delete Row', 'Delete current row selected in sub-table?',
                                         QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Cancel)

            if reply == QMessageBox.Ok:
                self.onDelRowChanged.emit(self, index)
            else:
                pass


# for changes values in the sub_table
class sub_table_window(QDialog):
    onsubtableChange = pyqtSignal(object, int, list)

    def __init__(self, parent, table, row, row_data, checkbox_columns, header_labels, subtable_datetime_columns: List[int] = None):
        super(QDialog, self).__init__(parent)
        self.table = table
        self.row_data = row_data
        self.row = row
        self.checkbox_columns = checkbox_columns
        self.header_labels = header_labels
        self.subtable_datetime_columns = subtable_datetime_columns

        self.initUI()

    def initUI(self):

        self.setWindowTitle("Change sub-table data?")
        self.setStyleSheet("QDialog {background-color: lightgrey;}")

        self.widgets = []

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)

        self.buttonBox.accepted.connect(self.accept_changes)
        self.buttonBox.rejected.connect(self.reject)
        self.layout = QVBoxLayout()
        self.layout.addSpacing(20)

        for index, value in enumerate(self.row_data):
            myfont = QFont()
            myfont.setBold(True)

            if self.checkbox_columns and index in self.checkbox_columns:
                check = QCheckBox(self.header_labels[index])
                self.widgets.append(check)

                if value.upper() == "TRUE" or value.upper() == "T":
                    check.setCheckState(Qt.Checked)
                else:
                    check.setCheckState(Qt.Unchecked)

                self.layout.addWidget(check, alignment=Qt.AlignHCenter)

            elif self.subtable_datetime_columns and index in self.subtable_datetime_columns:
                edit_layout = QHBoxLayout()
                label = QLabel(self.header_labels[index])
                label.setFont(myfont)
                label.setAlignment(Qt.AlignHCenter)

                date = CustomDateEdit()
                self.widgets.append(date)

                # set date on calendar popup if valid date in cell, else set todays date
                date_value = QDate.fromString(value, "MM/dd/yyyy")
                if date_value.isValid():
                    date.calendarWidget().setSelectedDate(date_value)
                else:
                    today = QDate.currentDate()
                    date.calendarWidget().setSelectedDate(today)

                date.setFocusPolicy(Qt.NoFocus)
                date.setCalendarPopup(True)

                edit_layout.addWidget(label)
                edit_layout.addWidget(date)
                edit_layout.addStretch()
                self.layout.addLayout(edit_layout)

            else:
                edit_layout = QHBoxLayout()
                label = QLabel(self.header_labels[index])
                label.setFont(myfont)
                label.setAlignment(Qt.AlignHCenter)

                line_edit = QLineEdit()
                line_edit.setText(value)

                self.widgets.append(line_edit)
                edit_layout.addWidget(label)
                edit_layout.addWidget(line_edit)

                self.layout.addLayout(edit_layout)

        self.layout.addWidget(self.buttonBox, alignment=Qt.AlignHCenter)
        self.setLayout(self.layout)

    def accept_changes(self):
        row_values = self.find_layout_children()

        self.onsubtableChange.emit(self.table, self.row, row_values)

        self.accept()

    def find_layout_children(self) -> List[str]:
        row_data = []

        for widget in self.widgets:
            if isinstance(widget, QCheckBox):
                row_data.append(str(widget.isChecked()))
            elif isinstance(widget, QLineEdit):
                    row_data.append(widget.text())
            elif isinstance(widget, QDateEdit):
                date = widget.date()
                row_data.append(date.toString("MM/dd/yyyy"))

        return row_data


# create a Qdialog for the user to insert data for the new row to be added
class addRowMaintable_window(QDialog):
    onaddRowChanged = pyqtSignal(list)
    onexistingRowChanged = pyqtSignal(list, int)

    def __init__(self, parent, total_columns, columns_with_checkboxes, datetime_columns, expandable_rows, header_labels, title,
                 row_data: List[str] = None, checked_row_items: List[int] = None, row: int = None):
        super(QDialog, self).__init__(parent)

        self.columns = total_columns
        self.checkbox_columns = columns_with_checkboxes
        self.datetime_columns = datetime_columns
        self.expandable_rows = expandable_rows
        self.header_labels = header_labels
        self.title = title
        self.row_data = row_data
        self.checked_row_items = checked_row_items
        self.row = row

        self.initUI()

    def initUI(self):
        self.widgets = []

        self.setWindowTitle("Add Row")
        self.setStyleSheet("QDialog {background-color: lightgrey;}")

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)

        self.buttonBox.accepted.connect(self.accept_changes)
        self.buttonBox.rejected.connect(self.reject)

        upper_layout = QVBoxLayout()

        upper_label = QLabel(f"<b>{self.title}</b>")
        upper_label.setAlignment(Qt.AlignHCenter)

        upper_layout.addWidget(upper_label)
        upper_layout.addSpacing(30)

        for col in range(self.columns):
            if self.expandable_rows and col == 0:
                pass
            else:
                if self.datetime_columns and col in self.datetime_columns:
                    layout = QHBoxLayout()
                    label = QLabel(self.header_labels[col])

                    date = QDateEdit()
                    date.setCalendarPopup(True)
                    date.setDate(QDate.currentDate())
                    self.widgets.append(date)

                    layout.addStretch()
                    layout.addWidget(label)
                    layout.addWidget(date)
                    layout.addStretch()

                    upper_layout.addLayout(layout)

                elif self.checkbox_columns and col in self.checkbox_columns:
                    checkbox = QCheckBox(self.header_labels[col])
                    self.widgets.append(checkbox)

                    upper_layout.addWidget(checkbox, alignment=Qt.AlignHCenter)

                else:
                    layout = QHBoxLayout()
                    label = QLabel(self.header_labels[col])
                    edit = QLineEdit()
                    self.widgets.append(edit)

                    layout.addWidget(label)
                    layout.addWidget(edit)

                    upper_layout.addLayout(layout)

        upper_layout.addStretch()
        upper_layout.addWidget(self.buttonBox, alignment=Qt.AlignHCenter)
        self.setLayout(upper_layout)

        # if row_data supplied, populate the widgets
        if self.row_data:
            self.populate_widgets(self.row_data)

    def populate_widgets(self, row_data):

        for index, widget in enumerate(self.widgets):
            if isinstance(widget, QDateEdit):
                date_string = row_data[index]
                date = QDate.fromString(date_string, "MM/dd/yyyy")
                widget.setDate(date)

            elif isinstance(widget, QCheckBox):
                col_index = None
                if self.expandable_rows and index+1 in self.checkbox_columns:
                    col_index = self.checkbox_columns.index(index+1)
                if not self.expandable_rows and index in self.checkbox_columns:
                    col_index = self.checkbox_columns.index(index)

                if col_index or col_index == 0:
                    value = self.checked_row_items[col_index]
                    if value.upper() == "TRUE" or value.upper() == "T":
                        widget.setChecked(True)
                    else:
                        widget.setChecked(False)

            else:
                if isinstance(widget, QLineEdit):
                    value = row_data[index]
                    widget.setText(value)

    def accept_changes(self):
        if not self.row_data:
            row_values = self.find_layout_children()
            self.onaddRowChanged.emit(row_values)
            self.close()

        if self.row_data:
            row_values = self.find_layout_children()
            self.onexistingRowChanged.emit(row_values, self.row)
            self.close()

    def find_layout_children(self) -> List[str]:
        row_data = []

        for widget in self.widgets:
            if isinstance(widget, QDateEdit):
                selected_date = widget.date()
                date_string = selected_date.toString("MM/dd/yyyy")
                row_data.append(date_string)

            elif isinstance(widget, QCheckBox):
                row_data.append(str(widget.isChecked()))

            else:
                if isinstance(widget, QLineEdit):
                    row_data.append(widget.text())

        return row_data










# custom qframe for tableview due to bug with widgets overlapping frame of tableview
class setup_table(QFrame):
    resizeSignal = pyqtSignal(QSize)

    def __init__(self, app: QApplication, maintable_data: List[str] = None, maintable_headers: List[str] = None, columns_with_checkboxes: List[int] = None,
                 checked_indexes_rows: Dict[int, List[int]] = None, sub_table_data: List[List[str]] = None, editable_columns: List[int] = None,
                 parent=None, datetime_columns: List[int] = None, footer: bool = False, footer_values: dict = None,
                 subtable_col_checkboxes: List[int] = None, sub_table_headers_labels: List[str] = None, expandable_rows: bool = False,
                 add_mainrow_option: bool = False, del_mainrow_option: bool = False, add_subrow_option: bool = False,
                 del_subrow_option: bool = False, subtable_datetime_columns: List[int] = None, dblclick_edit_only: bool = False,
                 use_sql: bool = False, sql_maintable_path: str = None, sql_maintable_name: str = None, sql_maintable_query: str = None,
                 sql_subtable_path: str = None, sql_subtable_name: str = None, sql_subtable_query: str = None):

        super(setup_table, self).__init__()

        self.app = app
        self.setObjectName("myframe")
        self.setFrameStyle(QFrame.Box | QFrame.Plain)
        self.setStyleSheet("QFrame#myframe {border: 1px solid black};")
        self.setContentsMargins(1, 1, 0, 0)

        self.table_view = None
        self.model = None
        self.maintable_data = maintable_data
        self.maintable_headers = maintable_headers
        self.expandable_rows = expandable_rows
        self.sub_table_headers_labels = sub_table_headers_labels
        self.sub_table_data = sub_table_data

        self.columns_with_checkboxes = columns_with_checkboxes
        self.datetime_columns = datetime_columns
        self.checked_indexes_rows = checked_indexes_rows
        self.editable_columns = editable_columns
        self.footer = footer
        self.footer_value = footer_values
        self.subtable_col_checkboxes = subtable_col_checkboxes
        self.add_mainrow_option = add_mainrow_option
        self.del_mainrow_option = del_mainrow_option
        self.add_subrow_option = add_subrow_option
        self.del_subrow_option = del_subrow_option
        self.subtable_datetime_columns = subtable_datetime_columns
        self.dblclick_edit_only = dblclick_edit_only

        self.use_sql = use_sql
        self.sql_maintable_path = sql_maintable_path
        self.sql_maintable_name = sql_maintable_name
        self.sql_maintable_query = sql_maintable_query
        self.sql_subtable_path = sql_subtable_path
        self.sql_subtable_name = sql_subtable_name
        self.sql_subtable_query = sql_subtable_query

        self.maintable_rowids = []

        self.maintable_df = None
        self.indexes_adjusted = False

        # if using sql try to get the main table data from the SQL data base & sub table as a list of lists
        if self.use_sql:
            sql_no_error = self.sql_check_error()
            if sql_no_error:
                self.returnSQL_maintable_data()
                self.returnSQL_subtable_data()

        data_provided_check = self.table_check_for_errors()

        if data_provided_check and self.maintable_data:
            if self.expandable_rows:
                self.adjust_indexes_if_expandable_rows()
            self.activate_table()

    def returnSQL_subtable_data(self):
        allsub_tables = SQL_table.sql_tables(self.sql_subtable_path)
        sub_df = SQL_table.sql_subtable_to_dataframe(self.sql_subtable_path, allsub_tables, self.sql_subtable_name,
                                                     self.sub_table_headers_labels, self.sql_subtable_query)

        if not isinstance(sub_df, pd.DataFrame):
            print("ERROR, Couldn't read SQL sub table!")
        else:
            if isinstance(self.maintable_df, pd.DataFrame):
                subtable_data = SQL_table.subtable_df_to_list(sub_df, self.maintable_df)
                self.sub_table_data = subtable_data
            else:
                print("ERROR, Main table Dataframe needs to be provided")

    def returnSQL_maintable_data(self):
        # get main talbe Data
        df = SQL_table.sql_maintable_to_dataframe(self.sql_maintable_path, self.sql_maintable_name,
                                                  self.sql_maintable_query)

        # retrieve rowid's corresponding to each row of the self.maintable_data, this will be used
        # for updating sql table
        main_rowids = SQL_table.sql_get_all_rowids(self.sql_maintable_path, self.sql_maintable_name)
        self.maintable_rowids = main_rowids

        if not isinstance(df, pd.DataFrame):
            self.maintable_df = None
            print("ERROR, Couldn't read SQL main table!")
        else:
            self.maintable_df = df
            column_names = df.columns.to_list()
            self.maintable_headers = column_names

            # if columns with checkboxes integers provided, get the associated column names
            maintable_checkbox_columnnames = []
            if self.columns_with_checkboxes:
                for index, value in enumerate(column_names):
                    if index in self.columns_with_checkboxes:
                        maintable_checkbox_columnnames.append(value)

            # if date time columns integers provided, get the associated column name(s)
            maintable_datetime_columnname = []
            if self.datetime_columns:
                for index, value in enumerate(column_names):
                    if index in self.datetime_columns:
                        maintable_datetime_columnname.append(value)

            maintable_data, checked_rows = \
                SQL_table.collect_maintabledata_fromSQL_databases(df, maintable_datetime_columnname,
                                                                  maintable_checkbox_columnnames)

            self.maintable_data = maintable_data
            self.checked_indexes_rows = checked_rows

    def adjust_indexes_if_expandable_rows(self):
        # adjust index values before passing to table_view to account for additional
        # expansion column for table with expansion option chosen
        if self.columns_with_checkboxes:
            self.columns_with_checkboxes = [x + 1 for x in self.columns_with_checkboxes]
        if self.checked_indexes_rows:
            modified_dict = {key + 1: value for key, value in self.checked_indexes_rows.items()}
            self.checked_indexes_rows = modified_dict
        if self.editable_columns:
            self.editable_columns = [x + 1 for x in self.editable_columns]
        if self.datetime_columns:
            self.datetime_columns = [x + 1 for x in self.datetime_columns]

        if self.footer and self.footer_value:
            modified_dict = {key + 1: value for key, value in self.footer_value.items()}
            self.footer_value = modified_dict

        self.indexes_adjusted = True

    def adjust_indexes_back_if_expandable_rows(self):
        # adjust index back to indexes provided if expandable rows, this is for if modifying an existing table
        if self.columns_with_checkboxes:
            self.columns_with_checkboxes = [x - 1 for x in self.columns_with_checkboxes]
        if self.checked_indexes_rows:
            modified_dict = {key - 1: value for key, value in self.checked_indexes_rows.items()}
            self.checked_indexes_rows = modified_dict
        if self.editable_columns:
            self.editable_columns = [x - 1 for x in self.editable_columns]
        if self.datetime_columns:
            self.datetime_columns = [x - 1 for x in self.datetime_columns]

        if self.footer and self.footer_value:
            modified_dict = {key - 1: value for key, value in self.footer_value.items()}
            self.footer_value = modified_dict

        self.indexes_adjusted = False

    def activate_table(self):
        # note have to send copy to lazydatamodel of the main table data, otherwise changes for the main table data
        # will affect the variable in this class
        self.model_data = self.maintable_data.copy()

        self.model = LazyDataModel(self.model_data, self.columns_with_checkboxes, self.maintable_headers, self.expandable_rows)
        self.model.sql_value_change.connect(self.sql_maintable_value_change)
        self.table_view = CustomTableView(self.app, self.model, self.columns_with_checkboxes, self.checked_indexes_rows, self.sub_table_data,
                                          editable_columns=self.editable_columns, parent=self, datetime_columns=self.datetime_columns,
                                          footer=self.footer, footer_values=self.footer_value, subtable_col_checkboxes=self.subtable_col_checkboxes,
                                          subtable_header_labels=self.sub_table_headers_labels, expandable_rows=self.expandable_rows,
                                          add_mainrow_option=self.add_mainrow_option, del_mainrow_option=self.del_mainrow_option,
                                          add_subrow_option=self.add_subrow_option, del_subrow_option=self.del_subrow_option,
                                          subtable_datetime_columns=self.subtable_datetime_columns, dblclick_edit_only=self.dblclick_edit_only)
        self.table_view.sql_add_row.connect(self.sql_maintable_addrow)
        self.table_view.sql_del_row.connect(self.sql_maintable_delrow)
        self.table_view.onsql_rowChange.connect(self.sql_maintable_entire_rowChange)
        self.table_view.sql_value_change.connect(self.sql_maintable_value_change)
        self.table_view.sql_addrow_subtable.connect(self.sql_subtable_addrow)
        self.table_view.sql_delrow_subtable.connect(self.sql_subtable_delrow)
        self.table_view.sql_update_subtable.connect(self.sql_subtable_updaterow)

    def resizeEvent(self, event):
        # Handle the resize event of the QFrame
        super().resizeEvent(event)

        # Adjust the size of the QTableView when the QFrame is resized
        table_view_size = self.size()
        new_size = QSize(table_view_size.width()-2, table_view_size.height()-2)
        self.resizeSignal.emit(new_size)

    def sql_subtable_updaterow(self, maintable_index: int, subrow_index: int, subtable_values: List[str]):
        # append maintable row Index to the subtable_values, this is so that the program knows
        # which subtables rows below to which maintable row
        subtable_values.insert(0, maintable_index)

        if self.use_sql:
            table_name = self.sql_subtable_name

            # column from subtable database that references the maintable rows
            column_to_search = "maintable_index"
            query = f'SELECT rowid, * FROM "{table_name}" WHERE "{column_to_search}" = {maintable_index}'

            # return row data for all rows with that maintable_index
            result = SQL_table.sql_query_table(self.sql_subtable_path, self.sql_subtable_name, query)

            if result != None:
                try:
                    # first one of tuple is row id in database
                    row_id_to_update = result[subrow_index][0]

                    for index, value in enumerate(subtable_values):
                        SQL_table.update_sql_table_cell(self.sql_subtable_path, table_name, row_id_to_update, value,
                                                    column_index=index)
                except:
                    self.error_message("ERROR, index out of range, mismatch between sub-table and database OR \n"
                                       "someone may have already removed this row, refresh table if needed", "ERROR")

    def sql_subtable_addrow(self, maintable_index: int, subtable_values: List[str]):
        # append maintable row Index to the subtable_values, this is so that the program knows
        # which subtables rows below to which maintable row
        subtable_values.insert(0, maintable_index)

        if self.use_sql:
            SQL_table.add_sql_row(self.sql_subtable_path, self.sql_subtable_name, subtable_values)


            # code for testing
            #allsub_tables = SQL_table.sql_tables(self.sql_subtable_path)
            #sub_df = SQL_table.sql_subtable_to_dataframe(self.sql_subtable_path, allsub_tables, self.sql_subtable_name,
            #                                           self.sub_table_headers_labels, self.sql_subtable_query)
            #print(sub_df)

    def sql_subtable_delrow(self, maintable_index: int, subtable_index: int):
        if self.use_sql:
            table_name = self.sql_subtable_name

            # column from subtable database that references the maintable rows
            column_to_search = "maintable_index"
            query = f'SELECT rowid, * FROM "{table_name}" WHERE "{column_to_search}" = {maintable_index}'

            # return row data for all rows with that maintable_index
            result = SQL_table.sql_query_table(self.sql_subtable_path, self.sql_subtable_name, query)

            if result != None:
                # first one of tuple is row id in database
                try:
                    row_id_to_remove = result[subtable_index][0]

                    # remove row from database
                    SQL_table.del_sql_row(self.sql_subtable_path, self.sql_subtable_name, row_id_to_remove)
                except:
                    self.error_message("ERROR, index out of range, mismatch between sub-table and database OR \n"
                                       "someone may have already removed this row, refresh table if needed", "ERROR")

    def sql_maintable_delrow(self, row: int):
        rowid = self.maintable_rowids[row]

        if self.use_sql:
            SQL_table.del_sql_row(self.sql_maintable_path, self.sql_maintable_name, rowid)
            self.maintable_rowids.remove(rowid)
            del self.maintable_data[row]

            # delete corresponding rows in the sql sub-table
            if self.sql_subtable_path:
                # return any rowid's if any for maintable row index
                table_name = self.sql_subtable_name

                # column from subtable database that references the maintable rows
                column_to_search = "maintable_index"
                query = f'SELECT rowid, * FROM "{table_name}" WHERE "{column_to_search}" = {row}'

                # return row data for all rows with that maintable_index
                result = SQL_table.sql_query_table(self.sql_subtable_path, self.sql_subtable_name, query)

                try:
                    rowids = [row[0] for row in result]
                    for rowid in rowids:
                        # remove row from database
                        SQL_table.del_sql_row(self.sql_subtable_path, self.sql_subtable_name, rowid)
                except:
                    self.error_message("ERROR, index out of range, mismatch between sub-table and database OR \n"
                                       "someone may have already removed this row, refresh table if needed", "ERROR")

    def sql_maintable_addrow(self, values: list):
        # convert any datetimes to datetime object if option chosen
        if self.datetime_columns:

            # -1 because list starts at index 0 and if self.expandable_rows, +1 was added to the datetime_columns list
            col_mod = 0
            if self.expandable_rows:
                col_mod = 1

            for date_col in self.datetime_columns:
                values[date_col - col_mod] = datetime.strptime(values[date_col - col_mod], "%m/%d/%Y")

        if self.use_sql:
            rowid = SQL_table.add_sql_row(self.sql_maintable_path, self.sql_maintable_name, values)
            self.maintable_rowids.append(rowid)
            self.maintable_data.append(values)

    def sql_maintable_entire_rowChange(self, row, column, value):
        # convert date time back to it's original indexes values if self.expandable_rows
        if self.expandable_rows and self.datetime_columns:
            date_columns = [x - 1 for x in self.datetime_columns]
            if column in date_columns:
                value = datetime.strptime(value, "%m/%d/%Y")

        elif self.datetime_columns and column in self.datetime_columns:
            value = datetime.strptime(value, "%m/%d/%Y")

        if self.use_sql:
            rowid = self.maintable_rowids[row]
            SQL_table.update_sql_table_cell(self.sql_maintable_path, self.sql_maintable_name, rowid, value,
                                            column_index=column)

    def sql_maintable_value_change(self, row, column, value):
        if self.datetime_columns and column in self.datetime_columns:
            value = datetime.strptime(value, "%m/%d/%Y")

        if self.use_sql:
            # account for expandable_rows
            if self.expandable_rows:
                column = column - 1

            rowid = self.maintable_rowids[row]
            SQL_table.update_sql_table_cell(self.sql_maintable_path, self.sql_maintable_name, rowid, value, column_index=column)

    def sql_check_error(self):
        if self.use_sql:
            if not self.sql_maintable_path:
                print("ERROR, Must provide SQL Main table path for .db file when using SQL")
                return False

            if not self.sql_maintable_name:
                print("ERROR, Must provide main table name when using SQL!")
                return False

            if self.expandable_rows:
                if not self.sql_subtable_path:
                    print("ERROR, Must provide sub-table SQL .db path if using SQL and expandable rows")
                    return False

                if not self.sub_table_headers_labels:
                    print("ERROR, Must provide sub-table column headers if using SQL and expandable rows")
                    return False

                if not self.sql_subtable_name:
                    print("ERROR, Must provide sub table name if using SQL and expandable rows")
                    return False

        return True

    def table_check_for_errors(self):
        if not self.maintable_data and not self.use_sql:
            print("ERROR, must provide table data as a list of rows OR use SQL and provide the SQL information!")
            return False

        if not self.maintable_headers:
            print("ERROR, Must provide Main table Headers!")
            return False

        if self.expandable_rows and not self.sub_table_headers_labels:
            print("ERROR, Must provide sub-table Headers if using expandable rows!")
            return False

        if self.expandable_rows and not self.sub_table_data:
            print("ERROR, Must provide sub-table data if using expandable rows!")
            return False

        # check to make sub table data, even if blank, is available for all rows of main table
        if self.expandable_rows:
            if len(self.sub_table_data) != len(self.maintable_data):
                print("ERROR, Mismatch between main table data and it's sub-row data counterparts\n"
                      "Must be sub-row data for every row in main table, even if blank.")
                return False

        if self.use_sql:
            if len(self.maintable_data) != len(self.maintable_rowids):
                print("ERROR, Mismatch between main table rows and SQL rows", "ERROR")
                return False

        return True

    def error_message(self, msg, title):
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText(msg)
        msgBox.setWindowTitle(title)
        msgBox.setStandardButtons(QMessageBox.Ok)
        msgBox.exec_()

    def clear_table(self, keep_filter=False):
        if self.table_view is not None:
            self.table_view.reset_table(keep_filter)

    def loadnew_maintable_sql(self, maintable_name: str, maintable_sql_path: str, maintable_query: str = None,
                              subtable_sql_name: str = None, subtable_sql_path: str = None, subtable_headers: List[str] = None,
                              subtable_query: str = None, keep_existing_filter=False):

        # adjust indexes back if using expandable rows for the returnSQL_maintable_data function
        if self.indexes_adjusted:
            self.adjust_indexes_back_if_expandable_rows()

        # reset table in case user didn't reset it
        self.clear_table(keep_filter=keep_existing_filter)

        self.sql_maintable_name = maintable_name
        self.sql_maintable_path = maintable_sql_path
        self.sql_maintable_query = maintable_query

        self.returnSQL_maintable_data()

        # adjust indexes back if using expandable rows
        if not self.indexes_adjusted and self.expandable_rows:
            self.adjust_indexes_if_expandable_rows()

        self.loadnew_checkboxed_rows(self.checked_indexes_rows)

        # only load new headers if a new table was able to be loaded... if not then resetting headers would be a problem
        if self.maintable_df is not None:
            self.loadnew_headers(self.maintable_headers)

        self.update_table()

        # load new subtable if the option is chosen
        if self.use_sql and self.expandable_rows:
            if not subtable_sql_name or not subtable_sql_path or not subtable_headers:
                print("ERROR, Must provide sub table information as 'Use SQL' is set to TRUE!")
            else:
                self.loadnew_subtable_sql(subtable_sql_name, subtable_sql_path, subtable_headers, subtable_query)

    def loadnew_maintable_list(self, maintable_data: List[str], keep_existing_filter=False):
        self.clear_table(keep_filter=keep_existing_filter)
        self.maintable_data = maintable_data
        self.update_table()

    def loadnew_subtable_list(self, subtable_data: List[str]):
        if subtable_data and self.table_view is not None:
            self.sub_table_data = subtable_data
            self.table_view.sub_table_data = subtable_data

    def loadnew_subtable_sql(self, subtable_sql_name: str, subtable_sql_path: str, subtable_headers: List[str],
                             subtable_query: str = None):

        self.sql_subtable_name = subtable_sql_name
        self.sql_subtable_path = subtable_sql_path
        self.sub_table_headers_labels = subtable_headers
        self.sql_subtable_query = subtable_query

        if self.use_sql:
            self.returnSQL_subtable_data()
            self.table_view.sub_table_data = self.sub_table_data

    def loadnew_checkboxed_rows(self, checked_rows: Union[Dict[int, int], None]):
        if checked_rows and self.table_view is not None:
            # clear out delegate variables
            delegate = self.table_view.itemDelegate()
            delegate.checked_indexes_rows = checked_rows

    def loadnew_headers(self, headers: List[str]):
        if self.model is not None:
            self.model.update_headers(headers)

    def update_table(self):
        if self.table_view is not None:
            self.table_view.model.beginResetModel()
            self.table_view.model.table_data = self.maintable_data
            self.table_view.model.endResetModel()
            self.table_view.header.populate_filter_dropdown()

            # reset/clear the subtable_data variable in the table_view when changing the table maintable_data
            # so that the number of indexes matches the new rows
            if self.expandable_rows:
                subtable_list = []
                for row in self.maintable_data:
                    subtable_list.append([])
                self.table_view.sub_table_data = subtable_list

            if self.footer and self.footer_value:
                for i in self.footer_value:
                    self.table_view.setFooterValue(i)

    def update_using_sql(self, value: bool):
        self.use_sql = value

    def use_expandable_rows(self, value: bool):
        if self.model:
            self.table_view.model.beginResetModel()

            # reset all the expandable_row values in each class.... really should have made a class to handle these variables
            # used across multiple classes and have them all pull from it.......
            self.expandable_rows = value
            if value == False:
                if self.sub_table_data:
                    self.sub_table_data.clear()

                if self.indexes_adjusted:
                    self.adjust_indexes_back_if_expandable_rows()

            if value == True:
                if not self.indexes_adjusted:
                    self.adjust_indexes_if_expandable_rows()

            # adjust the variables in the table_view and its associated classes
            if self.table_view is not None:
                self.table_view.header.expandable_rows = value
                self.table_view.expandable_rows = value
                self.table_view.model.expandable_rows = value

                delegate = self.table_view.itemDelegate()
                delegate.expandable_rows = value

                if value == False:
                    if self.table_view.sub_table_data:
                        self.table_view.sub_table_data.clear()
                        self.table_view.sub_table_widgets.clear()

                    if self.columns_with_checkboxes:
                        self.table_view.columns_with_checkboxes = self.columns_with_checkboxes
                        self.model.checkbox_indexes = self.columns_with_checkboxes
                        delegate.checked_indexed_columns = self.columns_with_checkboxes

                    if self.checked_indexes_rows:
                        self.table_view.checked_indexes_rows = self.checked_indexes_rows
                        delegate.checked_indexes_rows = self.checked_indexes_rows

                    if self.editable_columns:
                        self.table_view.editable_columns = self.editable_columns
                        delegate.editable_columns = self.editable_columns

                    if self.datetime_columns:
                        self.table_view.datetime_columns = self.datetime_columns
                        delegate.datetime_columns = self.datetime_columns

                    # remake footers to update their positions
                    if self.footer_value:
                        self.table_view.footer_values = self.footer_value
                        self.table_view.footer_row_boxes.clear()
                        self.table_view.footer()

                    # delete the "" that was inserted into column headers to account for expanded rows
                    try:
                        if self.indexes_adjusted:
                            headers = self.model.column_headers[1:]
                            self.loadnew_headers(headers)
                    except:
                        pass

                if value == True:
                    if self.table_view.sub_table_data == None or len(self.table_view.sub_table_data) == 0:
                        sub_data = []
                        if self.maintable_data:
                            for i in self.maintable_data:
                                sub_data.append([])
                            self.table_view.sub_table_data = sub_data
                    else:
                        self.table_view.sub_table_data = self.sub_table_data

                    if self.columns_with_checkboxes:
                        self.table_view.columns_with_checkboxes = self.columns_with_checkboxes
                        self.model.checkbox_indexes = self.columns_with_checkboxes
                        delegate.checked_indexed_columns = self.columns_with_checkboxes

                    if self.checked_indexes_rows:
                        self.table_view.checked_indexes_rows = self.checked_indexes_rows
                        delegate.checked_indexes_rows = self.checked_indexes_rows

                    if self.editable_columns:
                        self.table_view.editable_columns = self.editable_columns
                        delegate.editable_columns = self.editable_columns

                    if self.datetime_columns:
                        self.table_view.datetime_columns = self.datetime_columns
                        delegate.datetime_columns = self.datetime_columns

                    # remake footers to update their positions
                    if self.footer_value:
                        self.table_view.footer_values = self.footer_value
                        self.table_view.footer_row_boxes.clear()
                        self.table_view.footer()

                    try:
                        # loadnew_headers calls the update_headers function in the qabstracttablemodel which
                        # automatically makes adjustements for the column headers if expandable_rows is set to True
                        if not self.indexes_adjusted:
                            headers = self.model.column_headers
                            self.loadnew_headers(headers)
                    except:
                        pass

            self.table_view.model.endResetModel()



if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = LazyDataViewer(app)
    viewer.show()

    sys.exit(app.exec_())
   # pass
