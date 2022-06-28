# -*- coding:Utf-8 -*-

import sys
from PyQt5 import uic
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QPushButton, QListWidget, QListWidgetItem, QDialog,
                             QFileDialog, QMessageBox, QTreeWidget, QTreeWidgetItem,
                             QTextEdit, QDockWidget, QMenu, QAction, QPlainTextEdit)
from PyQt5.QtCore import pyqtSlot, Qt, QPoint
from PyQt5.QtGui import QTextCursor
import os
import sys
import prefix_tree
from macro_compiler import run_macro, compile_macro
import re
import json

dir_path = '\\'.join(__file__.split('\\')[:-1])



class Window(QMainWindow):
    def __init__(self, path=''):
        super().__init__()
        uic.loadUi(os.path.join(dir_path, 'main_window.ui'), self)
        self.show()
        
        self.word_list = WordList(self)
        self.word_list.hide()
        self._word_list_position = 0, 0

        self.macro_dock = QDockWidget('Macro', parent=self)
        self.macro_editor = MacroEditor(self.macro_dock)
        self.macro_dock.setWidget(self.macro_editor)
        self.macro_dock.setFloating(True)

        self.load_macro_menu = QMenu(self.macro_editor.pushButtonLoad)
        self.macro_editor.pushButtonLoad.setMenu(self.load_macro_menu)
        self.update_macro_menu()
        
        self._current_row = 0
        self._list_length = 0
        self._prefix = ''
        self._is_word_list_visible = False

        self.line_counter_vscrollbar = self.lineCounter.verticalScrollBar()
        self.text_edit_vscrollbar = self.textEdit.verticalScrollBar()
        self._is_updating = False
        self.line_counter_vscrollbar.valueChanged.connect(self.update_text_edit_scroll_bar)
        self.text_edit_vscrollbar.valueChanged.connect(self.update_line_counter_scroll_bar)
        
        self.textEdit.textChanged.connect(self.update_word_list)
        self.textEdit.keyPressEvent = self.modify_keypress_behaviour(self.textEdit.keyPressEvent, self.text_edit_key_press)

        self.max_line = 10000                
        self.lineCounter.insertPlainText('\n'.join([str(n) for n in range(1, self.max_line)]))
        
        self._tree = prefix_tree.get_tree(os.path.join(dir_path, 'liste_francais.txt'))

        self._filepath = ''
        self._has_unsaved_changes = False
        
        self.actionNew.triggered.connect(self.new)
        self.actionSave.triggered.connect(self.save)
        self.actionSaveAs.triggered.connect(self.save_as)
        self.actionOpen.triggered.connect(self.open)
        self.actionAutoReturn.triggered.connect(self.change_line_wrap_mode)
        self.actionCreateMacro.triggered.connect(self.open_macro_editor)
        self.macro_editor.pushButtonSave.clicked.connect(self.save_macro)

        self.macro_editor.pushButtonRun.clicked.connect(self.run_macro)
        
        self.update_title()

        if path != '':
            self._open(path)
        
    def update_title(self):
        if self._filepath:
            fn = os.path.basename(self._filepath)
        else:
            fn = 'sans titre'
        self.setWindowTitle(f'{fn}{"*" * self._has_unsaved_changes}')
    
    def update_line_counter_scroll_bar(self, value):
        if self._is_updating:
            self.is_updating = False
        else:
            self.is_updating = True
            if value >= self.line_counter_vscrollbar.maximum():
                self.lineCounter.insertPlainText('\n' + '\n'.join([str(n) for n in range(self.max_line, self.max_line * 2)]))
                self.max_line *= 2

                self.text_edit_vscrollbar.setValue(self.line_counter_vscrollbar.maximum())
            else:
                self.line_counter_vscrollbar.setValue(value)

    def update_text_edit_scroll_bar(self, value):
        if self._is_updating:
            self.is_updating = False
        else:
            self.is_updating = True
            if value >= self.text_edit_vscrollbar.maximum():
                self.line_counter_vscrollbar.setValue(self.text_edit_vscrollbar.maximum())
            else:
                self.text_edit_vscrollbar.setValue(value)
    
    def show_word_list(self):
        self.word_list.show()
        self._is_word_list_visible = True

    def hide_word_list(self):
        self.word_list.hide()
        self._is_word_list_visible = False
    
    def text_edit_key_press(self, event):
        if self._is_word_list_visible:
            key = event.key()
            if key == Qt.Key_Down:
                if self.set_selected_item(self._current_row, self._current_row + 1):
                    self._current_row += 1
                else:
                    self.word_list.listWidget.item(0).setSelected(True)
                    self._current_row = 0
                self.word_list.listWidget.scrollToItem(self.word_list.listWidget.item(self._current_row))
                return False
            elif key == Qt.Key_Up:
                if self.set_selected_item(self._current_row, self._current_row - 1):
                    self._current_row -= 1
                else:
                    self.word_list.listWidget.item(self._list_length - 1).setSelected(True)
                    self._current_row = self._list_length - 1
                self.word_list.listWidget.scrollToItem(self.word_list.listWidget.item(self._current_row))
                return False
            elif key == Qt.Key_Tab:
                word = self.word_list.listWidget.item(self._current_row).text()
                self.insert_text_at_cursor(word[len(self._prefix):])
                return False
            elif key == Qt.Key_Escape:
                self.hide_word_list()
                return True
        return True

    def insert_text_at_cursor(self, text):
        self.textEdit.insertPlainText(text)
    
    def set_selected_item(self, current, new):
        self.word_list.listWidget.item(current).setSelected(False)
        item = self.word_list.listWidget.item(new)
        if item is not None:
            item.setSelected(True)
            return True
        return False
    
    def modify_keypress_behaviour(self, func, additional_behaviour):
        def keyPressEvent(event):
            if additional_behaviour(event):
                return func(event)
        return keyPressEvent
    
    @property
    def word_list_position(self):
        return self._word_list_position

    @word_list_position.setter
    def word_list_position(self, position):
        size = self.word_list.size()
        x = position[0]
        y = position[1]
        self.word_list.move(x, y)
        self._word_list_position = position
    
    def update_word_list(self):
        self._has_unsaved_changes = True
        self.update_title()
        
        cursor = self.textEdit.textCursor()
        char_index = cursor.position() - 1
        text = self.textEdit.toPlainText()

        if text:
            char = text[char_index]
            while char in 'azertyuiopqsdfghjklmwxcvbnAZERTYUIOPQSDFGHJKLMWXCVBNéëèàçùêâôï' and char_index > 0:
                char_index -= 1
                char = text[char_index]
            if char_index > 0:
                char_index += 1
            if char_index == cursor.position():
                self.hide_word_list()
            else:
                prefix = text[char_index:cursor.position()]
                self._prefix = prefix
                words = prefix_tree.keys_with_prefix(self._tree, prefix.lower(), 20)
                if len(words) == 0:
                    self.hide_word_list()
                else:
                    self.word_list.listWidget.clear()
                    self.word_list.listWidget.addItems(words)
                    self._current_row = 0
                    self._list_length = len(words)
                    self.word_list.listWidget.item(0).setSelected(True)
                    self.show_word_list()
                    cursor.setPosition(char_index, QTextCursor.KeepAnchor)
        
                    cursor_rect = self.textEdit.cursorRect(cursor)
                    self.word_list_position = cursor_rect.x() + 62, cursor_rect.y() + 37 + cursor_rect.height()
        else:
            self.hide_word_list()

    def _save(self, path):
        with open(path, 'w', encoding='utf8') as file:
            file.write(self.textEdit.toPlainText())
        self._filepath = path
        self._has_unsaved_changes = False
        self.update_title()

    def save(self):
        if self._filepath:
            self._save(self._filepath)
        else:
            self.save_as()

    def save_as(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Sauvegarder', '', "Fichier texte (*.txt);;Tous les fichiers (*)")
        self._save(path)

    def open(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Ouvrir', '', "Fichier texte (*.txt);;Tous les fichiers (*)")
        self._open(path)

    def _open(self, path):
        self.new()
        with open(path, 'r', encoding='utf8') as file:
            self.textEdit.setPlainText(file.read())
        self._has_unsaved_changes = False
        self._filepath = path
        self.update_title()
        self.hide_word_list()
        
    def new(self):
        reply = QMessageBox.Yes
        if self._has_unsaved_changes:
            reply = QMessageBox.question(self, 'Nouveau', 'Les modifications actuelles seront perdues, confirmez ?', QMessageBox.Yes | QMessageBox.Cancel, QMessageBox.Yes)
        if reply == QMessageBox.Yes:
            self._filepath = ''
            self.textEdit.setPlainText('')
            self._has_unsaved_changes = False
            self.update_title()

    def change_line_wrap_mode(self, v):
        if v:
            self.textEdit.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        else:
            self.textEdit.setLineWrapMode(QPlainTextEdit.NoWrap)

    def open_macro_editor(self):
        self.update_macro_menu()
        self.macro_dock.show()
        self.macro_editor.show()

    def run_macro(self):
        selection_only = self.macro_editor.checkBoxSelection.isChecked()

        macro = self.macro_editor.textEditIn.toPlainText()
        if macro:
            compiled_macro = compile_macro(macro, {})
            new_text = ''
            txt = self.textEdit.toPlainText()
            if not selection_only:
                range_ = 0, len(txt)
            else:
                cursor = self.textEdit.textCursor()
                range_ = cursor.selectionStart(), cursor.selectionEnd()
                if range_[0] > range_[1]:
                    range_ = range_[::-1]
            
            stopped = False
            out_of_range = False
            vars_={'_txt': txt, '_stop': StopLoop}
            for i, char in enumerate(txt):
                out_of_range = not (range_[0] <= i < range_[1])
                
                if not stopped and not out_of_range:
                    txt_char = TextChar(txt, char, i, self.textEdit, range_)
                    try:
                        vars_['_c'] = txt_char
                        v = run_macro(compiled_macro, vars_=vars_)
                    except Exception as e:
                        QMessageBox.critical(self, 'Erreur', str(e), QMessageBox.Ok)
                        return
                    else:
                        if v == StopLoop:
                            stopped = True
                            new_text += char
                        elif v is not None:
                            new_text += str(v)
                        else:
                            new_text += char
                else:
                    new_text += char
            self.textEdit.setPlainText(new_text)
            self.hide_word_list()

    def update_macro_menu(self):
        with open(os.path.join(dir_path, 'macro.json')) as datafile:
            data = json.load(datafile)
        self.load_macro_menu.clear()
        for macro_name, macro in data.items():
            action = QAction(self)
            action.setText(macro_name)
            self.load_macro_menu.addAction(action)
            action.triggered.connect(self.get_macro_loader(macro))
        return data

    def get_macro_loader(self, macro):
        def loader():
            self.macro_editor.textEditIn.setPlainText(macro)
        return loader

    def save_macro(self):
        dialog = LineEditDialog("Entrez le nom de la macro", self._save_macro)
        dialog.exec_()

    def _save_macro(self, name):
        data = self.update_macro_menu()
        macro = self.macro_editor.textEditIn.toPlainText()
        data[name] = macro
        with open(os.path.join(dir_path, 'macro.json'), 'w') as datafile:
            json.dump(data, datafile)
            
        self.update_macro_menu()
        
    def closeEvent(self, event):
        if self._has_unsaved_changes:
            
            quit_msg = "Les modifications non sauvegardées seront perdues. Confirmez ?"
            reply = QMessageBox.question(self, 'Quitter', 
                             quit_msg, QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Ok)

            if reply == QMessageBox.Ok:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

class StopLoop:
    pass

class TextChar:
    def __init__(self, text, symbol, position, text_edit, range_):
        self._symbol = symbol
        self._position = position
        self._text = text
        self.pos = position
        self._text_edit = text_edit
        self._cursor = None
        self._range = range_

    def with_cursor(self):
        self._cursor = text_edit.textCursor()
        self._cursor.setPosition(position)
        return self
    
    def __add__(self, value):
        if isinstance(value, int):
            new_pos = (self._position + value) % len(self._text)
            symbol = self._text[new_pos]
            return TextChar(self._text, symbol, new_pos, self._text_edit, self._range)
        elif isinstance(value, (str, TextChar)):
            return str(self) + str(value)
        return NotImplemented

    def __radd__(self, value):
        return self + value
    
    def __sub__(self, value):
        if isinstance(value, int):
            return self + (-value)
        return NotImplemented

    def mul(self, value):
        if isinstance(value, int):
            return self._symbol * value
        return NotImplemented
    
    def __str__(self):
        return self._symbol

    def sor(self):
        return self._range[0] == self._position

    def eor(self):
        return self._range[1] - 1 == self._position
    
    def eof(self):
        return self._position == len(self._text) - 1

    def sof(self):
        return self._position == 0

    def lower(self):
        return self._symbol.lower()

    def upper(self):
        return self._symbol.upper()

    def match(self, regex):
        return re.match(regex, self._text[self.pos:]) is not None
    
    def __eq__(self, value):
        return str(self) == str(value)
    
    
class WordList(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi(os.path.join(dir_path, 'word_list.ui'), self)


class MacroEditor(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi(os.path.join(dir_path, 'macro_editor.ui'), self)

class LineEditDialog(QDialog):
    def __init__(self, title, action):
        super().__init__()
        uic.loadUi(os.path.join(dir_path, 'line_edit_dialog.ui'), self)
        self.show()
        self.setWindowTitle(title)
        self.buttonBox.accepted.connect(self._accept)
        self._action = action

    @pyqtSlot()
    def _accept(self):
        name = self.lineEdit.text()
        self._action(name)

def main():
    if len(sys.argv) == 2:
        path = sys.argv[1]
    else:
        path = ''
    app = QApplication([])
    window = Window(path)
    app.exec_()

if __name__ == '__main__':
    main()
