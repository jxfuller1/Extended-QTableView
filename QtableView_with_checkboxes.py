import sys
import time

import random   #this is for testing purposes
from typing import List

from PyQt5.QtGui import QColor, QPen
from PyQt5.QtWidgets import QApplication, QTableView, QVBoxLayout, QMainWindow, QAbstractItemView, \
    QAbstractItemDelegate, QStyledItemDelegate, QPushButton, QWidget, QItemDelegate, QStyleOptionButton, QStyle
from PyQt5.QtCore import Qt, QAbstractTableModel, QEvent, QVariant, QSize, QRect, QModelIndex

from typing import List

"""
class rowDelegate(QStyledItemDelegate):
    def __init__(self):
        super(rowDelegate, self).__init__()

    def paint(self, painter, option, index):
        # Custom painting logic for additional lines
        rect = option.rect
        pen = QPen(QColor(0, 0, 255))  # Blue color for lines
        painter.setPen(pen)

        # Draw additional lines under the text
        for i in range(1, 5):  # Draw 5 lines
            y = rect.bottom() - i * 5  # Adjust the spacing between lines
            painter.drawLine(rect.left(), y, rect.right(), y)

        # Call the base paint method to paint the default content
        super().paint(painter, option, index)

        self.sizeHint(option, index)
"""

# function purely for testing performance
def random_indexes_for_testing(total_rows: int) -> List:
    random_indexes = []

    for i in range(total_rows):
        if i % 2 == 0:
            a = random.randint(0, total_rows)
            if a not in random_indexes:
                random_indexes.append(a)

    return random_indexes


class ButtonDelegate(QStyledItemDelegate):
    def __init__(self, checked_indexes_column, column, parent=None):
        super(ButtonDelegate, self).__init__(parent)

        self.last_press_index = QModelIndex()
        self.last_release_index = QModelIndex()
        self.column = column
        self.checked_indexes_rows = checked_indexes_column


    def paint(self, painter, option, index):
        if index.column() == self.column:  # Adjust the column index as needed

            button = QStyleOptionButton()

            new_x = option.rect.x() + int(option.rect.width()/2) - 5
            new_rect = QRect(new_x, option.rect.y(), option.rect.width(), option.rect.height())
            button.rect = new_rect

         #  button.text = "Click me"
            button.state |= QStyle.State_Enabled

            if index.row() in self.checked_indexes_rows:
                button.state |= QStyle.State_On
            else:
                button.state |= QStyle.State_Off

            QApplication.style().drawControl(QStyle.CE_CheckBox, button, painter)

    def editorEvent(self, event, model, option, index):
        if index.column() == self.column:
            button_rect = option.rect

            if event.type() == QEvent.MouseButtonPress:
                if button_rect.contains(event.pos()):
                    self.last_press_index = index
                    self.change_button_state(index.row())
                return True

            elif event.type() == QEvent.MouseButtonRelease:
                if button_rect.contains(event.pos()):
                    self.last_release_index = index
                    self.change_button_state(index.row())
                return True

            else:
                return True

      #  return super(ButtonDelegate, self).editorEvent(event, model, option, index)

    def change_button_state(self, row: int):

        if self.last_press_index == self.last_release_index:
            if row in self.checked_indexes_rows:
                self.checked_indexes_rows.remove(row)
            else:
                self.checked_indexes_rows.append(row)

            self.last_press_index = QModelIndex()
            self.last_release_index = QModelIndex()

            self.pressed_checkbox(row, self.column)

    # return pressed checkbox and it's state:
    def pressed_checkbox(self, row: int, column: int):
        if row not in self.checked_indexes_rows:
            print(f"Removed; Row {row}, Column {column}")
        elif row in self.checked_indexes_rows:
            print(f"Added; Row {row}, Column {column}")


    # for if using a pushbutton
  #  def handle_button_click(self, index):
   # #    print(f"Button Clicked in row {index.row()}, column {index.column()}")




class LazyDataModel(QAbstractTableModel):
    def __init__(self, rows, columns, columns_with_checkboxes):
        super().__init__()

        self.rows = rows
        self.columns = columns
        self.checkbox_indexes = columns_with_checkboxes


    def rowCount(self, parent=None):
        return self.rows

    def columnCount(self, parent=None):
        return self.columns

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and index.column() not in self.checkbox_indexes:
            row_value = f"Row {index.row()}, Col {index.column()}"
            return row_value
        elif role == Qt.EditRole:
            return False
        return None

   # def flags(self, index):
    #    flags = Qt.ItemIsEnabled | Qt.ItemIsEditable
    #    if index.column() != 1:
    #        flags |= Qt.ItemIsEditable
    #    return flags



    def get_column_values(self, column):
        return [self.data(self.index(row, column)) for row in range(self.rowCount())]

class CustomTableView(QTableView):
    def __init__(self, model, parent=None):
        super().__init__(parent)

        self.model = model
        self.setModel(self.model)


     #   print(self.model.get_column_values(0))


class LazyDataViewer(QMainWindow):
    def __init__(self):
        super().__init__()

        start = time.time()

        rows = 10000
        columns = 20
        columns_with_checkboxes = [1, 2, 3, 4]

        self.model = LazyDataModel(rows, columns, columns_with_checkboxes)
        self.table_view = CustomTableView(self.model)

        for i in columns_with_checkboxes:
            checked_indexes_column = random_indexes_for_testing(rows)
            button_delegate = ButtonDelegate(checked_indexes_column, i, self.table_view)
            self.table_view.setItemDelegateForColumn(i, button_delegate)

        self.setCentralWidget(self.table_view)  # Set the QTableView as the central widget


        end = time.time()
        print(end-start)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = LazyDataViewer()
    viewer.show()

    sys.exit(app.exec_())
