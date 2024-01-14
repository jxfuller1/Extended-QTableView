import sys
import time
import bisect

import random   #this is for testing purposes
from typing import List, Union, Tuple, Dict

from PyQt5.QtGui import QColor, QPen, QFont, QStandardItemModel, QWheelEvent, QMouseEvent, QKeyEvent
from PyQt5.QtWidgets import QApplication, QTableView, QVBoxLayout, QMainWindow, QAbstractItemView, \
    QAbstractItemDelegate, QStyledItemDelegate, QPushButton, QWidget, QItemDelegate, QStyleOptionButton, QStyle, \
    QTableWidget, QHeaderView, QLabel, QLineEdit, QDialogButtonBox, QDialog, QTableWidgetItem, QComboBox, QFrame, \
    QCheckBox, QStyleOptionViewItem
from PyQt5.QtCore import Qt, QAbstractTableModel, QEvent, QVariant, QSize, QRect, QModelIndex, pyqtSignal, \
    QSortFilterProxyModel, QPoint, pyqtSlot, QCoreApplication, QTimer, QLocale, QItemSelectionModel


# function purely for testing performance
def random_indexes_for_testing(total_rows: int) -> List:
    random_indexes = []

    for i in range(total_rows):
        a = random.randint(0, total_rows)
        if a not in random_indexes:
            random_indexes.append(a)

    return random_indexes

class LineEdit(QLineEdit):

    def __init__(self, parent=None):
        super().__init__(parent)

    def focusInEvent(self, event):
        self.setCursorPosition(0)
        super().focusInEvent(event)

# delegate for entire qtableview
class ButtonDelegate(QStyledItemDelegate):
    onexpansionChange = pyqtSignal(int, bool)
    oncheckboxstateChange = pyqtSignal()
    # this signal is for updating the vertical header when editor is opened on cell for the arrow
    oneditorStarted = pyqtSignal(object)

    # passing keypresses from line edit to tableview to support in-column searching
    keyPressed = pyqtSignal(QLineEdit, QKeyEvent)

    def __init__(self, checked_indexes_rows, checked_indexed_columns, editable_columns, parent=None):
        super(ButtonDelegate, self).__init__(parent)

        self.last_press_index = QModelIndex()
        self.last_release_index = QModelIndex()
        self.checked_indexes_rows = checked_indexes_rows
        self.checked_indexed_columns = checked_indexed_columns
        self.editable_columns = editable_columns
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

         #  button.text = "Click me"
            button.state |= QStyle.State_Enabled

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

        if index.column() == 0:
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

    def editorEvent(self, event, model, option, index):
        # map clicked row to source model index (needs to be done if user sorts/filters)
        index = index.model().mapToSource(index)

      #  view=option.widget
      #  view.edit(index)

        if index.column() in self.checked_indexed_columns or index.column() == 0:
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

            else:
                return True

        return super(ButtonDelegate, self).editorEvent(event, model, option, index)

    def change_button_state(self, row: int, column: int):
        if column == 0:
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

                    # emit to update proxy filter that checkbox states changed
                    self.oncheckboxstateChange.emit()
                else:
                    self.checked_indexes_rows[column].append(row)
                    self.oncheckboxstateChange.emit()

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

        if index.column() not in self.checked_indexed_columns and index.column() != 0 and index.column() not in self.editable_columns:
            editor = LineEdit(parent)
            editor.setReadOnly(True)
            self.oneditorStarted.emit(index)
            editor.installEventFilter(self)
            return editor

        elif index.column() in self.editable_columns:
            editor = LineEdit(parent)
            editor.setReadOnly(False)
            self.oneditorStarted.emit(index)
            editor.installEventFilter(self)
            return editor

    def setEditorData(self, editor, index):
        # Set the initial content of the editor here
        editor.setText(index.data(Qt.DisplayRole))

    def updateEditorGeometry(self, editor, option, index):
        # Set the geometry of the editor within the cell
        cell_rect = option.rect
        editor.setGeometry(cell_rect.x(), cell_rect.y(), cell_rect.width(), 20)

    def setModelData(self, editor, model, index):
        value = editor.text()
        source_index = model.mapToSource(index)  # Map to the source index
        source_model = model.sourceModel()  # Get the source model from the proxy model
        source_model.setData(source_index, value, Qt.EditRole)


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
    def __init__(self, data, columns_with_checkboxes, column_headers):
        super().__init__()

        self.table_data = data
        self.column_headers = column_headers
        self.checkbox_indexes = columns_with_checkboxes
        self.row_clicked = -1

        self.font = QFont()
        self.font.setBold(True)
        self.font.setPointSize(8)  # Set the desired font size

     #   self.search_text = None

    def rowCount(self, parent=None):
        return len(self.table_data)

    def columnCount(self, parent=None):
        return len(self.table_data[0])

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and index.column() >= 0 and index.column() not in self.checkbox_indexes:
            # -1 on the column to account for the expansion column
            row_value = self.table_data[index.row()][index.column()-1]
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
      # if role == Qt.EditRole and not self.search_text:
        if role == Qt.EditRole:

            # -1 on the column to account for the expansion column, set new value if value changed in cell
            self.table_data[index.row()][index.column()-1] = value
            self.dataChanged.emit(index, index)

            return True

        """
        elif role == Qt.EditRole and self.search_text:
            current_row, current_col = index.row(), index.column()
            for row in range(self.rowCount()):
                if row != current_row and self.table_data[row][index.column()-1][:len(self.search_text)].upper() == self.search_text.upper():

                    print(self.table_data[row][index.column()-1][:len(self.search_text)].upper())
                    target_index = self.index(row, current_col)
                    self.dataChanged.emit(target_index, target_index)
                 return True
        """
        return False

    """
    def change_current_index(self, index, value, role):
        current_row, current_col = index.row(), index.column()
        for row in range(self.rowCount()):
            if row != current_row and self.table_data[row][index.column()-1][:len(self.search_text)].upper() == self.search_text.upper():
                print(self.search_text.upper())
                print(self.table_data[row][index.column()-1][:len(self.search_text)].upper())

                target_index = self.index(row, current_col)
                self.dataChanged.emit(target_index, target_index)
    """

class CustomTableView(QTableView):
    def __init__(self, model, columns_with_checkboxes: List[int], checked_indexes_rows: Dict[int, List[int]],
                 sub_table_data: List[List[str]], editable_columns: List[int], parent=None):
        super().__init__(parent)
        parent.resizeSignal.connect(self.handle_parent_resize)

        # move 1,1 position within qframe parent so that frame and widget dont' overlap
        self.move(1, 1)

        self.sub_table_widgets = {}
        self.filter_dict = {}
        self.filter_checked_rows = {}
        self.editable_columns = editable_columns

        self.search_text = ""

        # lists for mapping which rows are extended and which rows are for tables for the abstractmodel and button delegate
        self.row_clicked = []

        self.model = model
        self.model.dataChanged.connect(self.model_data_changed)

        self.columns_with_checkboxes = columns_with_checkboxes
        self.checked_indexes_rows = checked_indexes_rows
        self.sub_table_data = sub_table_data

        self.proxy_model = HiddenRowsProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.setModel(self.proxy_model)

        self.setDelegates()
        self.setEditTriggers(QAbstractItemView.CurrentChanged)
        self.vertical_header_setup()
        self.horizontal_header_setup()

        self.setMouseTracking(True)
        self.clicked.connect(self.on_cell_clicked)

    #    self.selection_model = self.selectionModel()
     #   self.selection_model.currentChanged.connect(self.handleCurrentChanged)

        self.verticalScrollBar().valueChanged.connect(self.update_sub_table_positions_timer)
        self.verticalScrollBar().rangeChanged.connect(self.update_sub_table_positions_timer)
        self.verticalHeader().sectionResized.connect(self.update_sub_table_positions_timer)
        self.horizontalScrollBar().valueChanged.connect(self.update_sub_table_positions_timer)
        self.horizontalScrollBar().rangeChanged.connect(self.update_sub_table_positions_timer)
        self.horizontalHeader().sectionResized.connect(self.update_sub_table_positions_timer)

        # Apply styles directly to QTableView
        # Apply style to hide the frame
        self.setObjectName("tableview")
        self.setStyleSheet(
            "QTableView#tableview {"
            "   border: none;"
            "}"
        )

    def handleCurrentChanged(self, current, previous):
        # Emit your custom signal when the current cell changes
        self.currentCellChanged.emit(current.row(), current.column())

    # to support in-column searching in qtableview
    def handleLineEditKeyPress(self, line_edit, event):
        current_index = self.currentIndex()
        model_index = self.indexFromProxytoSource(current_index.row(), current_index.column())

        # only non editable columns can be searched
        if event.text() and model_index.column() not in self.editable_columns:
            if event.key() == Qt.Key_Backspace:
                self.search_text = self.search_text[:-1]
            else:
                self.search_text += event.text()
            self.find_search_result(current_index)

    # find row for searches
    def find_search_result(self, view_index: QModelIndex):
        index = self.indexFromProxytoSource(view_index.row(), view_index.column())
        column = index.column()

        proxy_index_rows_found = []

        # iterate through model data to find matches
        for row in range(self.model.rowCount()):
            model_index = self.model.index(row, column)
            data = self.model.data(model_index, Qt.DisplayRole)

            # check for any matches from abstract model to search string
            if self.search_text.upper() == data[:len(self.search_text)].upper():

                # check if row is visible in the proxy model
                proxy_index = self.proxy_model.mapFromSource(model_index)

                if proxy_index.isValid():
                    proxy_index_rows_found.append(proxy_index.row())

        if len(proxy_index_rows_found) != 0:
            update_index = self.indexFromSourcetoProxy(proxy_index_rows_found[0], view_index.column())
            self.setCurrentIndex(update_index)
            self.on_cell_clicked(update_index)


    # update combobox filters on data changed
    def model_data_changed(self, index_top_left, index_bottom_right, roles):
        new_value = index_top_left.data(Qt.DisplayRole)

        # switch to visual column as my header combo buttons mapping are switched to visual indexes in the qheaderview
        # for when columsn are switched around
        visual = self.header.visualIndex(index_top_left.column())
        button = self.header.m_buttons[visual]
        self.header.set_combo_column_filter_items(visual, button, alter_already_set_filter=True, altered_value=new_value)

    # set text alignments and add columns with checkboxes
    def setDelegates(self):
        button_delegate = ButtonDelegate(self.checked_indexes_rows, self.columns_with_checkboxes, self.editable_columns, self)
        button_delegate.onexpansionChange.connect(self.expansion_clicked)
        button_delegate.oncheckboxstateChange.connect(self.checkboxstateChange)
        button_delegate.oneditorStarted.connect(self.update_vertical_header_arrow)
        button_delegate.keyPressed.connect(self.handleLineEditKeyPress)
        self.setItemDelegate(button_delegate)

    # for updating what's filtered when checkbox state changes
    def checkboxstateChange(self):
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
        super(CustomTableView, self).resizeEvent(event)

    def horizontal_header_setup(self):
        self.header = ButtonHeaderView(self)
        self.setHorizontalHeader(self.header)

        self.header.combofilteritemClicked.connect(self.onfilterChange)

        # Set your desired background color for vertical headers using a stylesheet
        stylesheet = "QHeaderView::section:horizontal {background-color: lightgray; border: 1px solid gray;},"
        self.horizontalHeader().setStyleSheet(stylesheet)

        self.horizontalHeader().setSortIndicatorShown(True)
        self.horizontalHeader().sortIndicatorChanged.connect(self.sortColumn)
        self.horizontalHeader().setSectionsMovable(True)
        self.horizontalHeader().setMaximumHeight(18)
        self.horizontalHeader().setSectionsClickable(True)
        self.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)

        self.resizeColumnsToContents()
        self.setColumnWidth(0, 20)

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

        """
        # if one of the filters is from a column with checkboxes, filtering needs to be handled differently
        if column_clicked in self.columns_with_checkboxes:
            self.oncheckboxfilterChange(filter_value, combo_index, column_clicked, combobox)
            return
        """

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

        # update tables if row with table gets filtered
        self.onfilterChange_sub_tables()

    """
    def oncheckboxfilterChange(self, filter_value: str, combo_index: int, column_clicked: int, combobox: QComboBox):
        delegate = self.itemDelegate()
        checked_rows = delegate.checked_indexes_rows

        if combo_index == 0 and filter_value == "All":
            try:
                self.filter_dict[column_clicked].clear()
                self.filter_checked_rows[column_clicked].clear()
            except:
                pass
            self.change_combo_box_checkstates(combobox, True)
        
        elif combo_index == 1 and filter_value == "Clear":
            if column_clicked not in self.columns_with_checkboxes:
                base_range = 4
            else:
                base_range = 2

            self.filter_dict[column_clicked] = [combobox.itemText(i) for i in range(base_range, combobox.count())]
            self.filter_checked_rows[column_clicked] = checked_rows
            self.change_combo_box_checkstates(combobox, False)
        
        elif column_clicked in self.filter_dict:
            if filter_value in self.filter_dict[column_clicked]:
                self.filter_dict[column_clicked].remove(filter_value)
            else:
                self.filter_dict[column_clicked].append(filter_value)
        else:
            self.filter_dict[column_clicked] = [filter_value]


        self.proxy_model.setFilterData(self.filter_dict, self.filter_checked_rows)
    """

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
        QTimer.singleShot(10, self.update_sub_table_positions)

    # input from signal is source index
    def expansion_clicked(self, row: int, expand: bool):
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
        sub_table.itemChanged.connect(self.sub_table_item_changed)

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

    def sub_table_create(self) -> Tuple[QWidget, QTableWidget]:
        upper_widget = mywidget(self)
        upper_widget.setContentsMargins(30, 0, 0, 0)
        upper_layout = QVBoxLayout()
        upper_layout.setContentsMargins(0, 0, 0, 10)
        sub_table = sub_TableWidget()
        upper_layout.addWidget(sub_table)
        upper_widget.setLayout(upper_layout)
        return upper_widget, sub_table

    # update main sub table data var for qtableview when an item is changed
    def sub_table_item_changed(self, item):

        # return the widget for the cell that was changed
        widget = item.tableWidget().parent()

        # Find row index (based on key value in the dictionary that im storing the opened table widgets in)
        table_row = [key for key, value in self.sub_table_widgets.items() if value == widget]

        if item:
            self.sub_table_data[table_row[0]][item.row()][item.column()] = item.text()

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

            table.setHorizontalHeaderLabels(["NCR No.", "Disposition", "Extra"])

             # Populate the table with random data
            for row in range(rows):
                table.setRowHeight(row, 18)
                for col in range(columns):
                    item = QTableWidgetItem(self.sub_table_data[sub_table_index][row][col])
                    table.setItem(row, col, item)

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

    def update_vertical_header_arrow(self, index: QModelIndex):
        self.update_row_selection(index.row())

    def on_cell_clicked(self, index: QModelIndex):
        self.update_vertical_header_arrow(index)

        # activate editor on cell click
        if index.column() not in self.columns_with_checkboxes and index.column() != 0:
            self.edit(index)

        # this is to support the header repaint/sort not being run on the first click out of qcombox popups
        if self.header.sectionsClickable() == True:
            self.header.outof_combo_popup += 1
        # Handle cell clicked event here
       # print("Cell clicked at row:", index.row(), "column:", index.column())


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

    def __init__(self, parent):
        super().__init__(Qt.Horizontal, parent)  # Adjust orientation to Horizontal

        self.m_buttons = []
        # this dict is to attach an index value to each button for when sections are moved around by user
        # in order to properly rearrange the comboboxes... only way i could figure out how to do this, all other methods failed
        self.m_buttons_index_attachments = {}

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

        # hide combo buttons if they aren't being hovered over or show if being hovered over (NOTE THIS IS FOR THE
        # COMBO ARROW not for the combobox popup
        for button in self.m_buttons:
            if self.m_buttons.index(button) == visual_index:
                if logical_index != 0:
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

        self.main_widget = QWidget()
        self.main_layout = QVBoxLayout()
        self.mainbutton = QPushButton("test")
        self.main_layout.addWidget(self.mainbutton)
        self.main_widget.setLayout(self.main_layout)

        start = time.time()

        # index of editable columns
        editable_columns = [6]

        # main table data
        rows = 10
        columns = 7

        data = []
        for row in range(rows):
            row_data = []
            for col in range(columns):
                if col == 5:
                    if row % 2 == 1:
                        row_data.append("")
                    else:
                        row_data.append(f"Row {row}, Column {col}")
                else:
                    row_data.append(f"Row {row}, Column {col}")
            data.append(row_data)

        # which columsn to have checkboxes in instead of text
        columns_with_checkboxes = [2, 3, 4, 5]

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
                for col in range(3):
                    row_data.append(f'sub Row {row}, sub Col {col}')
                table_data.append(row_data)
            sub_table_data.append(table_data)


        column_headers = []
        for i in range(columns):
            column_headers.append(f"Column {i}")

        # custom qframe for tableview due to bug with widgets overlapping frame of tableview
        self.frame = myframe()
        self.model = LazyDataModel(data, columns_with_checkboxes, column_headers)
        self.table_view = CustomTableView(self.model, columns_with_checkboxes, checked_indexes_rows, sub_table_data, editable_columns, self.frame)
        self.main_layout.addWidget(self.frame)

        self.setCentralWidget(self.main_widget)  # Set the QTableView as the central widget

        end = time.time()
        print(end-start)


class sub_TableWidget(QTableWidget):
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

        # Retrieve data from the clicked row
        row_data = [sender.parent().item(index, j).text() for j in range(sender.parent().columnCount())]

        self.dlg = sub_table_window(self, sender.parent(), index, row_data)
        self.dlg.onsubtableChange.connect(self.sub_table_adjust)
        self.dlg.exec()

    def sub_table_adjust(self, table: QTableWidget, row: int, row_data: List[str]):
        for i in range(table.columnCount()):
            item = QTableWidgetItem(row_data[i])
            table.setItem(row, i, item)

# for changes values in the sub_table
class sub_table_window(QDialog):
    onsubtableChange = pyqtSignal(object, int, list)

    def __init__(self, parent, table, row, row_data):
        super(QDialog, self).__init__(parent)
        self.table = table
        self.row_data = row_data
        self.row = row

        self.initUI()

    def initUI(self):

        self.setWindowTitle("Change sub-table data?")
        self.setStyleSheet("QDialog {background-color: lightgrey;}")

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonBox = QDialogButtonBox(QBtn)

        self.buttonBox.accepted.connect(self.accept_changes)
        self.buttonBox.rejected.connect(self.reject)
        self.layout = QVBoxLayout()
        self.layout.addSpacing(20)

        labels = ["NCR No.", "Disposition", "Extra"]

        for index, value in enumerate(self.row_data):
            myfont = QFont()
            myfont.setBold(True)
            label = QLabel(labels[index])
            label.setFont(myfont)
            label.setAlignment(Qt.AlignHCenter)

            line_edit = QLineEdit()
            line_edit.setText(value)

            self.layout.addWidget(label)
            self.layout.addWidget(line_edit)
            self.layout.addSpacing(20)

        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

    def accept_changes(self):
        all_line_edits_values = self.find_layout_children(QLineEdit)

        self.onsubtableChange.emit(self.table, self.row, all_line_edits_values)

        self.close()


    def find_layout_children(self, widget: QWidget) -> List[str]:
        widget_text = []

        for i in range(self.layout.count()):
            item = self.layout.itemAt(i)

            # Check if the item is a widget and is of the specified type
            if item and item.widget() and isinstance(item.widget(), widget):
                widget_text.append(item.widget().text())

        return widget_text


if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = LazyDataViewer()
    viewer.show()

    sys.exit(app.exec_())
