import sys
import time
import bisect

import random   #this is for testing purposes
from typing import List, Union, Tuple, Dict

from PyQt5.QtGui import QColor, QPen, QFont, QStandardItemModel, QWheelEvent, QMouseEvent, QKeyEvent, QPalette, \
    QStandardItem
from PyQt5.QtWidgets import QApplication, QTableView, QVBoxLayout, QMainWindow, QAbstractItemView, \
    QAbstractItemDelegate, QStyledItemDelegate, QPushButton, QWidget, QItemDelegate, QStyleOptionButton, QStyle, \
    QTableWidget, QHeaderView, QLabel, QLineEdit, QDialogButtonBox, QDialog, QTableWidgetItem, QComboBox, QFrame, \
    QCheckBox, QStyleOptionViewItem, QScrollBar, QHBoxLayout, QSizePolicy, QSpacerItem, QCalendarWidget, QDateEdit, \
    QMenu, QAction, QMessageBox
from PyQt5.QtCore import Qt, QAbstractTableModel, QEvent, QVariant, QSize, QRect, QModelIndex, pyqtSignal, \
    QSortFilterProxyModel, QPoint, pyqtSlot, QCoreApplication, QTimer, QLocale, QItemSelectionModel, QDate


# function purely for testing performance
def random_indexes_for_testing(total_rows: int) -> List:
    random_indexes = []

    for i in range(total_rows-1):
        a = random.randint(0, total_rows-1)
        if a not in random_indexes:
            random_indexes.append(a)

    return random_indexes

class LineEdit(QLineEdit):

    def __init__(self, parent=None):
        super().__init__(parent)

    def focusInEvent(self, event):
        super().focusInEvent(event)


class CustomDateEdit(QDateEdit):
    onDateChanged = pyqtSignal(object)

    def __init__(self, parent=None):
        super(CustomDateEdit, self).__init__(parent)

        self.setCalendarPopup(True)
        self.popup_installed = False

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


# delegate for entire qtableview
class ButtonDelegate(QStyledItemDelegate):
    onexpansionChange = pyqtSignal(int, bool)
    oncheckboxstateChange = pyqtSignal(int)
    # this signal is for updating the vertical header when editor is opened on cell for the arrow
    oneditorStarted = pyqtSignal(object, object)

    # passing keypresses from line edit to tableview to support in-column searching
    keyPressed = pyqtSignal(QLineEdit, QKeyEvent)

    datekeyPressed = pyqtSignal(QDateEdit)

    def __init__(self, checked_indexes_rows, checked_indexed_columns, editable_columns, datetime_columns, expandable_rows, parent=None):
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

        self.expanded_rows = []

    def eventFilter(self, obj, event):
        if isinstance(obj, QLineEdit) and event.type() == QKeyEvent.KeyPress:
            # Emit the signal when a key is pressed in the QLineEdit
            self.keyPressed.emit(obj, event)

        return super().eventFilter(obj, event)

    def paint(self, painter, option, index):
        # map clicked row to source model index  (this needs to be done if user sorts/filters)
        index = index.model().mapToSource(index)

        if index.column() in self.checked_indexed_columns:
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
        if index.column() != 0 and index.column() not in self.checked_indexed_columns:
            text = index.data(Qt.DisplayRole)
            text_rect = option.rect.adjusted(3, 3, -3, -3)
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
            text_rect = option.rect.adjusted(3, 3, -3, -3)
            painter.drawText(text_rect, Qt.AlignTop | Qt.AlignLeft, text)

        self.highlighted_index = QModelIndex()

    def editorEvent(self, event, model, option, index):
        # map clicked row to source model index (needs to be done if user sorts/filters)
        index = index.model().mapToSource(index)

        expansion_rows = False
        if index.column() == 0 and self.expandable_rows:
            expansion_rows = True

        if index.column() in self.checked_indexed_columns or expansion_rows:
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

        elif column in self.checked_indexed_columns:
            if self.last_press_index == self.last_release_index:
                if row in self.checked_indexes_rows.get(column):
                    self.checked_indexes_rows[column].remove(row)

                    # emit to update proxy filter that checkbox states changed and update footer number
                    self.oncheckboxstateChange.emit(column)
                else:
                    self.checked_indexes_rows[column].append(row)
                    self.oncheckboxstateChange.emit(column)

                self.last_press_index = QModelIndex()
                self.last_release_index = QModelIndex()

                self.pressed_checkbox(row, column)

    def pressed_expansion(self, row: int, expand: bool):
        self.onexpansionChange.emit(row, expand)

    # return pressed checkbox and it's state:
    def pressed_checkbox(self, row: int, column: int):
        if row not in self.checked_indexes_rows.get(column):
            print(f"Removed; Row index {row}, Column index {column}")
        elif row in self.checked_indexes_rows.get(column):
            print(f"Added; Row index {row}, Column index {column}")

    def createEditor(self, parent, option, index):
        expansion_rows = False
        if index.column() == 0 and self.expandable_rows:
            expansion_rows = True

        if index.column() not in self.checked_indexed_columns and not expansion_rows and \
                index.column() not in self.editable_columns and index.column() not in self.datetime_columns:
            editor = LineEdit(parent)
            editor.setReadOnly(True)
            self.oneditorStarted.emit(index, editor)
            editor.installEventFilter(self)
            return editor

        elif index.column() in self.editable_columns:
            editor = LineEdit(parent)
            editor.setReadOnly(False)
            self.oneditorStarted.emit(index, editor)
            editor.installEventFilter(self)
            return editor

        elif index.column() in self.datetime_columns:
            editor = CustomDateEdit(parent)
            editor.onDateChanged.connect(self.on_date_editor_changed)
            editor.setMaximumWidth(18)
            editor.setFocusPolicy(Qt.NoFocus)
            editor.setCalendarPopup(True)
            return editor

    def setEditorData(self, editor, index):
        # Set the initial content of the editor here
        if index.column() not in self.datetime_columns:
            editor.setText(index.data(Qt.DisplayRole))

        if index.column() in self.datetime_columns:
            cell_value = index.data(Qt.DisplayRole)

            # find matching date format being used
            matching_format = self.find_matching_format(cell_value, self.valid_date_formats)

            # set date on calendar popup if valid date in cell, else set todays date
            date = QDate.fromString(cell_value, matching_format)
            if date.isValid():
                editor.calendarWidget().setSelectedDate(date)
            else:
                today = QDate.currentDate()
                editor.calendarWidget().setSelectedDate(today)

    def updateEditorGeometry(self, editor, option, index):
        # Set the geometry of the editor within the cell
        if index.column() not in self.datetime_columns:
            cell_rect = option.rect
            editor.setGeometry(cell_rect.x(), cell_rect.y(), cell_rect.width(), 20)

        elif index.column() in self.datetime_columns:
            cell_rect = option.rect
            editor.setGeometry(cell_rect.x() + cell_rect.width()-18, cell_rect.y(), 18, 19)

    def setModelData(self, editor, model, index):
        if index.column() not in self.datetime_columns:
            value = editor.text()
            source_index = model.mapToSource(index)  # Map to the source index
            source_model = model.sourceModel()  # Get the source model from the proxy model
            source_model.setData(source_index, value, Qt.EditRole)

        elif index.column() in self.datetime_columns:
            date = editor.date()
            date_string = date.toString(self.matching_date_format)
            source_index = model.mapToSource(index)  # Map to the source index
            source_model = model.sourceModel()  # Get the source model from the proxy model
            source_model.setData(source_index, date_string, Qt.EditRole)

    def on_date_editor_changed(self, dateclicked):
        self.datekeyPressed.emit(dateclicked)

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
    def __init__(self, data, columns_with_checkboxes, column_headers, expandable_rows):
        super().__init__()

        self.table_data = data
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

    def rowCount(self, parent=None):
        return len(self.table_data)

    def columnCount(self, parent=None):
        if self.expandable_rows:
            total = len(self.table_data[0])+1
            return total
        else:
            return len(self.table_data[0])

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and index.column() >= 0 and index.column() not in self.checkbox_indexes:
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
            return self.column_headers[section]

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
                return True
            return False
        return False

    def insertRow(self, data):
        self.beginInsertRows(self.index(len(self.table_data), 0), len(self.table_data), len(self.table_data))
        self.table_data.append(data)
        self.endInsertRows()


class CustomTableView(QTableView):
    def __init__(self, model, columns_with_checkboxes: List[int] = None, checked_indexes_rows: Dict[int, List[int]] = None,
                 sub_table_data: List[List[str]] = None, editable_columns: List[int] = None, parent=None,
                 datetime_columns: List[int] = None, footer: bool = False, footer_values: dict = None,
                 subtable_col_checkboxes: List[int] = None, subtable_header_labels: List[str] = None, expandable_rows: bool = True):

        super().__init__(parent)
        # parent being a qframe
        parent.resizeSignal.connect(self.handle_parent_resize)

        # move 1,1 position within qframe parent so that frame and widget dont' overlap
        self.move(1, 1)

        self.sub_table_widgets = {}
        self.filter_dict = {}
        self.filter_checked_rows = {}
        self.editable_columns = editable_columns
        self.set_current_editor = None
        self.datetime_columns = datetime_columns
        self.subtable_col_checkboxes = subtable_col_checkboxes
        self.subtable_header_labels = subtable_header_labels
        self.expandable_rows = expandable_rows

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

    def show_context_menu(self, position):
        vertical_header = self.verticalHeader()
        index = vertical_header.logicalIndexAt(position)

        # update selected row on right click of header in table
        self.update_row_selection(index)

        if index != -1:
            menu = QMenu(self)

            # Add actions or other menu items as needed
            delete = QAction(f"Delete Current Row", self)
            delete.triggered.connect(lambda: self.delMainRowMsg(index))
            add = QAction(f"Add New Row", self)
            add.triggered.connect(lambda: self.addMainRowMsg(index))
            menu.addAction(delete)
            menu.addAction(add)

            # Show the context menu at the specified position
            menu.exec_(self.mapToGlobal(position))

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

        if column in self.footer_values.keys() and column not in self.columns_with_checkboxes:
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
        elif column in self.columns_with_checkboxes:
            delegate = self.itemDelegate()
            checked_rows = delegate.checked_indexes_rows[column]

            visible_rows = [self.indexFromProxytoSource(row, column).row() for row in range(self.proxy_model.rowCount())]
            non_visible_checked_rows = set(checked_rows) - set(visible_rows)

            total = set(checked_rows) - non_visible_checked_rows

            footer_edit.setText(str(len(total)))

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
                edit_box = self.footer_row_boxes[logical_indices[i]]
                proxy_width = self.columnWidth(logical_indices[i])

                edit_box.setGeometry(x+padding, padding, proxy_width-padding-padding,  self.footer_height-padding-padding)
                x += proxy_width

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
        # take into account vertical header width, as i want footer to overlay on top of vertical header
        vertical_header_width = self.verticalHeader().width()

        view_size = self.viewport().size()
        view_position = self.viewport().mapToParent(QPoint(0, 0))

        self.filter_widget.setFixedWidth(view_size.width()+vertical_header_width)
        self.filter_widget.setFixedHeight(self.filter_footer_margin_height)

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
                    combo_item = str(header_label) + " = " + text
                    self.filter_widget_combo.addItem(combo_item)

                    label = "(" + combo_item + ")  "
                    label_text += label

            # reset combobox max size width
            max_width = 0
            for i in range(self.filter_widget_combo.count()):
                width = self.filter_widget_combo.fontMetrics().width(self.filter_widget_combo.itemText(i))
                max_width = max(max_width, width)

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
        if event.text() and model_index.column() not in self.editable_columns:
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
    def model_data_changed(self, index_top_left, index_bottom_right, roles):

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
                                         self.datetime_columns, self.expandable_rows, self)
        button_delegate.onexpansionChange.connect(self.expansion_clicked)
        button_delegate.oncheckboxstateChange.connect(self.checkboxstateChange)
        button_delegate.oneditorStarted.connect(self.update_vertical_header_arrow_and_editor)
        button_delegate.keyPressed.connect(self.handleLineEditKeyPress)
        button_delegate.datekeyPressed.connect(self.handleDateeditKeyPress)

        self.setItemDelegate(button_delegate)

    def handleDateeditKeyPress(self, dateEdit):
        self.commitData(dateEdit)
        self.closeEditor(dateEdit, QAbstractItemDelegate.NoHint)

    # for updating what's filtered when checkbox state changes
    def checkboxstateChange(self, column: int):
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

    @pyqtSlot(QSize)
    def handle_parent_resize(self, size):
        self.resize(size)

    def resizeEvent(self, event):
        self.update_sub_table_positions()
        # viewport margins change needs to be in resize event or margin won't remain
        self.setViewportMargins(self.verticalHeader().size().width(), self.horizontalHeader().size().height(), 0, self.viewport_bottom_margin)
        super(CustomTableView, self).resizeEvent(event)

    def horizontal_header_setup(self):
        self.header = ButtonHeaderView(self, self.expandable_rows)
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

        if column in self.columns_with_checkboxes:
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
            if column_clicked not in self.columns_with_checkboxes:
                base_range = 4
            else:
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
        sub_table = sub_TableWidget()
        sub_table.rowdataChanged.connect(self.sub_table_items_changed)

        upper_layout.addWidget(sub_table)
        upper_widget.setLayout(upper_layout)
        return upper_widget, sub_table

    # update main sub table data var for qtableview when an item is changed
    def sub_table_items_changed(self, row: int, row_data: List[str], table: QTableWidget):

        # Find row index (based on key value in the dictionary that im storing the opened table widgets in)
        table_row = [key for key, value in self.sub_table_widgets.items() if value == table.parent()]

        if len(self.sub_table_data[table_row[0]]) <= row:
            # append if new row
            self.sub_table_data[table_row[0]].append(row_data)
        else:
            self.sub_table_data[table_row[0]][row] = row_data

    def sub_table_populate(self, sub_table_index: int, widget: QWidget):
        table = None
        # get the qtablewidgetitem (which is in the Qwidget)
        for child_widget in widget.findChildren(QWidget):
            if isinstance(child_widget, QTableWidget):
                table = child_widget

        if table is not None and self.sub_table_data[sub_table_index] is not None:
            rows = len(self.sub_table_data[sub_table_index])
            columns = len(self.sub_table_data[sub_table_index][0])

            table.setRowCount(rows)
            table.setColumnCount(columns)

            if self.subtable_header_labels:
                table.setHorizontalHeaderLabels(self.subtable_header_labels)

             # Populate with self.sub_table_data variabled
            for row in range(rows):
                table.setRowHeight(row, 18)
                for col in range(columns):
                    if col not in self.subtable_col_checkboxes:
                        item = QTableWidgetItem(self.sub_table_data[sub_table_index][row][col])
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                        table.setItem(row, col, item)

                    elif col in self.subtable_col_checkboxes:
                        widget = table.make_cell_checkbox()
                        check_value = self.sub_table_data[sub_table_index][row][col]
                        self.subtable_initial_checkbox_state(widget, check_value)
                        table.setCellWidget(row, col, widget)

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

        # activate editor on cell click
        if index.column() not in self.columns_with_checkboxes and index.column() != 0:
            self.edit(index)

        # this is to support the header repaint/sort not being run on the first click out of qcombox popups
        if self.header.sectionsClickable() == True:
            self.header.outof_combo_popup += 1
        # Handle cell clicked event here
       # print("Cell clicked at row:", index.row(), "column:", index.column())

    def delMainRowMsg(self, row: int):
        reply = QMessageBox.question(self, 'Delete Row', 'Delete current row selected?',
                                     QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Cancel)

        if reply == QMessageBox.Ok:
            self.delMainRow(row)
        else:
            pass

    def delMainRow(self, row: int):
        print(row)
        # things to modify on row deletion
        # will need to activate to function in abstract table model to delete the row data
        # will need to update remove row checkmarks from the delegate if any
        # update filter comboboxes?


        # EDIT NEED TO UPDATE FILTER COMBOBOXES WHEN ADDING ROW TOO
        # UPDATE FOOTER ROW AS WELL WHEN ADDING ROW

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

        self.row_dialog = addRowMaintable_window(self, self.model.columnCount(), self.columns_with_checkboxes, self.datetime_columns, self.expandable_rows, header_labels)
        self.row_dialog.onaddRowChanged.connect(self.addMainRowUpdate)
        self.row_dialog.exec()

    def addMainRowUpdate(self, values: list):
        self.model.insertRow(values)

        # add row to end of table
        row = self.model.rowCount()-1

        # if there's checkboxes in table set checkstates for new row
        if self.columns_with_checkboxes:
            # get checkboxed rows from the delegate as i will need to add to this the new checkboxes that are checked
            delegate = self.itemDelegate()
            for col, rows in delegate.checked_indexes_rows.items():
                if self.expandable_rows and "TRUE" in values[col-1].upper():
                    if row not in rows:
                        delegate.checked_indexes_rows[col].append(row)

                elif not self.expandable_rows and "TRUE" in values[col].upper():
                    if row not in rows:
                        delegate.checked_indexes_rows[col].append(row)

    def addSubRow(self):

        # get row with the arrow in the vertical header to indicated which row is selected
        row_selected = -1
        for i in range(self.model.rowCount()):
            if "\u27A1" in self.model.headerData(i, Qt.Vertical, Qt.DisplayRole):
                row_selected = i

        # get table
        table = None
        if row_selected in self.sub_table_widgets:
            widget = self.sub_table_widgets[row_selected]
            for child_widget in widget.findChildren(QWidget):
                if isinstance(child_widget, QTableWidget):
                    table = child_widget

        if table:
            header_labels = [table.horizontalHeaderItem(col).text() for col in range(table.columnCount())]
            checkbox_columns = self.subtable_col_checkboxes
            row_data = []
            index = table.rowCount()

            for col in range(table.columnCount()):
                row_data.append("")

            table.insertRow(index)
            table.setRowHeight(index, 18)

            # add checkboxes to new row
            if self.subtable_col_checkboxes:
                for i in self.subtable_col_checkboxes:
                    checkbox = table.make_cell_checkbox()
                    table.setCellWidget(index, i, checkbox)

            self.dlg = sub_table_window(self, table, index, row_data, checkbox_columns, header_labels)
            self.dlg.onsubtableChange.connect(table.sub_table_adjust)
            self.dlg.exec()

            # fix row height in main table
            height = self.get_sub_table_Height(table.parent())

            # map to proxy index
            index = self.indexFromSourcetoProxy(row_selected, 0)
            self.setRowHeight(index.row(), height+15)


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

    def __init__(self, parent):
        super().__init__(parent=parent)
        self.view().pressed.connect(self.handleItemPressed)
        self.setModel(QStandardItemModel(self))

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
        if logical_index in self.parent().parent().columns_with_checkboxes:
            base_row = 2
        else:
            base_row = 4

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
        oldanimation = app.isEffectEnabled(Qt.UI_AnimateCombo)
        app.setEffectEnabled(Qt.UI_AnimateCombo, False)
        super().showPopup()
        app.setEffectEnabled(Qt.UI_AnimateCombo, oldanimation)

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
        if logical_index in self.parent().parent().columns_with_checkboxes:
            base_row = 2
        else:
            base_row = 4

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

    def __init__(self, parent, expandable_rows):
        super().__init__(Qt.Horizontal, parent=parent)  # Adjust orientation to Horizontal

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
            button = ComboBox(self)
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
        if column not in self.parent().columns_with_checkboxes:
            base_index = 4
        else:
            base_index = 2

        return base_index

    def set_combo_column_filter_items(self, column: int, button: QComboBox, alter_already_set_filter: bool = False, altered_value: str = None):

        base_index = self.combo_base_index(column)

        if not alter_already_set_filter:
            if base_index == 4:
                visual_column = self.logicalIndex(column)

                # this complicated list comprehensions gets all item values from given column
                column_values = [(str(self.model().data(self.model().index(row, visual_column), Qt.DisplayRole))).strip()
                                 for row in range(self.model().rowCount())]

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

            else:
                item_to_list = ["All", "Clear", "False", "True"]
                button.addItems(item_to_list)
                [button.setItemData(index, Qt.Checked, Qt.CheckStateRole) for index in range(base_index, button.count())]
                button.combo_dropdown_height(len(item_to_list) + base_index)

            button.combo_dropdown_height(len(item_to_list) + base_index)
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
    def __init__(self):
        super().__init__()

        self.setGeometry(200, 200, 600, 400)

        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout()

        self.main_horizontal = QHBoxLayout()
        self.sql_combo = QComboBox()
        self.sql_combo.addItem("For SQL tables to be added")
        self.mainbutton = QPushButton("Add Row Main Table")
        self.subbutton = QPushButton("Add Row Sub Table")

        self.main_horizontal.addWidget(self.sql_combo)
        self.main_horizontal.addWidget(self.mainbutton)
        self.main_horizontal.addWidget(self.subbutton)

        self.main_layout.addLayout(self.main_horizontal)
        self.main_widget.setLayout(self.main_layout)

        start = time.time()

        # index of editable columns
        editable_columns = [6]

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
        expandable_rows = True

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
                for col in range(4):
                    if col < 3:
                        row_data.append(f'sub Row {row}, sub Col {col}')
                    if col == 3:
                        row_data.append("True")
                table_data.append(row_data)
            sub_table_data.append(table_data)

        column_headers = []
        for i in range(columns):
            column_headers.append(f"Column {i}")

        sub_table_headers_labels = ["NCR No.", "Disposition", "Extra", "Completed"]

        footer_values = {1: "total", 4: "total", 6: "sum"}

        datetime_columns = [7]

        # custom qframe for tableview due to bug with widgets overlapping frame of tableview

        #### NOTE DATETIME COLUMNS CANNOT ALSO BE IN EDITABLE COLUMNS ARGUMENT OR CAUSES CRASH #####
        ### possible add a check to make sure editable columns, columns with checkboxes and datetime columns do not overlap
        ### with same integer numbers
        self.frame = myframe()
        self.model = LazyDataModel(data, columns_with_checkboxes, column_headers, expandable_rows)
        self.table_view = CustomTableView(self.model, columns_with_checkboxes, checked_indexes_rows, sub_table_data,
                                          editable_columns=editable_columns, parent=self.frame, datetime_columns=datetime_columns,
                                          footer=True, footer_values=footer_values, subtable_col_checkboxes=sub_table_columns_with_checkboxes,
                                          subtable_header_labels=sub_table_headers_labels, expandable_rows=expandable_rows)

        self.mainbutton.clicked.connect(self.table_view.addMainRow)
        self.subbutton.clicked.connect(self.table_view.addSubRow)

        self.main_layout.addWidget(self.frame)

        self.setCentralWidget(self.main_widget)  # Set the QTableView as the central widget

        end = time.time()
        print(end-start)


class sub_TableWidget(QTableWidget):
    rowdataChanged = pyqtSignal(int, list, object)

    def __init__(self):
        super(sub_TableWidget, self).__init__()

      #  self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setAlternatingRowColors(True)
        self.horizontalHeader().setMaximumHeight(18)

        self.verticalHeader().sectionClicked.connect(self.sub_table_clicked)

        stylesheet = "QHeaderView::section {background-color: lightgray;} QTableWidget {alternate-background-color: lightgrey;}"
        self.setStyleSheet(stylesheet)

        self.horizontalHeader().setSectionsClickable(False)

       # new_table.horizontalHeader().setVisible(False)
       # new_table.verticalHeader().setVisible(False)

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

        self.dlg = sub_table_window(self, sender.parent(), index, row_data, checkbox_columns, header_labels)
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


# for changes values in the sub_table
class sub_table_window(QDialog):
    onsubtableChange = pyqtSignal(object, int, list)

    def __init__(self, parent, table, row, row_data, checkbox_columns, header_labels):
        super(QDialog, self).__init__(parent)
        self.table = table
        self.row_data = row_data
        self.row = row
        self.checkbox_columns = checkbox_columns
        self.header_labels = header_labels

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

            if index not in self.checkbox_columns:
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

              #  self.layout.addWidget(label)
             #   self.layout.addWidget(line_edit)
               # self.layout.addSpacing(20)
            elif index in self.checkbox_columns:
                check = QCheckBox(self.header_labels[index])
                self.widgets.append(check)

                if value.upper() == "TRUE" or value.upper() == "T":
                    check.setCheckState(Qt.Checked)
                else:
                    check.setCheckState(Qt.Unchecked)

                self.layout.addWidget(check, alignment=Qt.AlignHCenter)
               # self.layout.addSpacing(20)

        self.layout.addWidget(self.buttonBox, alignment=Qt.AlignHCenter)
        self.setLayout(self.layout)

    def accept_changes(self):
        row_values = self.find_layout_children()

        self.onsubtableChange.emit(self.table, self.row, row_values)

        self.close()

    def find_layout_children(self) -> List[str]:
        row_data = []

        for widget in self.widgets:
            if isinstance(widget, QCheckBox):
                row_data.append(str(widget.isChecked()))
            else:
                if isinstance(widget, QLineEdit):
                    row_data.append(widget.text())

        return row_data


# create a Qdialog for the user to insert data for the new row to be added
class addRowMaintable_window(QDialog):
    onaddRowChanged = pyqtSignal(list)

    def __init__(self, parent, total_columns, columns_with_checkboxes, datetime_columns, expandable_rows, header_labels):
        super(QDialog, self).__init__(parent)

        self.columns = total_columns
        self.checkbox_columns = columns_with_checkboxes
        self.datetime_columns = datetime_columns
        self.expandable_rows = expandable_rows
        self.header_labels = header_labels

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

        upper_label = QLabel("<b>Enter row data to add</b>")
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

    def accept_changes(self):
        row_values = self.find_layout_children()

        self.onaddRowChanged.emit(row_values)

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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = LazyDataViewer()
    viewer.show()

    sys.exit(app.exec_())

