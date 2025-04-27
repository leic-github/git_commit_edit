from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit, QPushButton,
    QListWidget, QHBoxLayout, QInputDialog, QMessageBox, QLabel
)
import json
import os


class AuthorInputDialog(QDialog):
    def __init__(self, parent=None, existing_text=""):
        super().__init__(parent)
        self.setWindowTitle("输入作者信息")
        self.resize(400, 200)

        self.layout = QVBoxLayout(self)

        self.instruction_label = QLabel("请输入作者信息（格式：名字 <邮箱>）:")
        self.layout.addWidget(self.instruction_label)

        self.author_input = QTextEdit(self)
        self.author_input.setText(existing_text)
        self.layout.addWidget(self.author_input)

        self.buttons_layout = QHBoxLayout()

        self.save_btn = QPushButton("保存")
        self.cancel_btn = QPushButton("取消")

        self.buttons_layout.addWidget(self.save_btn)
        self.buttons_layout.addWidget(self.cancel_btn)

        self.layout.addLayout(self.buttons_layout)

        self.save_btn.clicked.connect(self.save_input)
        self.cancel_btn.clicked.connect(self.reject)

    def save_input(self):
        input_text = self.author_input.toPlainText().strip()
        if input_text:
            self.accept()
            return input_text
        else:
            QMessageBox.warning(self, "错误", "输入不能为空，请输入有效的作者信息！")
            return None


class ManageAuthorsDialog(QDialog):
    def __init__(self, config_path, parent=None):
        super().__init__(parent)
        self.config_path = config_path
        self.setWindowTitle("管理作者信息")
        self.resize(400, 300)

        self.layout = QVBoxLayout(self)

        self.author_list = QListWidget()
        self.layout.addWidget(self.author_list)

        btn_layout = QHBoxLayout()

        self.add_btn = QPushButton("添加")
        self.edit_btn = QPushButton("编辑")
        self.delete_btn = QPushButton("删除")

        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)

        self.layout.addLayout(btn_layout)

        self.add_btn.clicked.connect(self.add_author)
        self.edit_btn.clicked.connect(self.edit_author)
        self.delete_btn.clicked.connect(self.delete_author)

        self.load_authors()

    def load_authors(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                authors = data.get('authors', [])
                self.author_list.clear()
                self.author_list.addItems(authors)

    def save_authors(self):
        authors = [self.author_list.item(i).text() for i in range(self.author_list.count())]
        data = {}
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        data['authors'] = authors
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add_author(self):
        dialog = AuthorInputDialog(self)
        if dialog.exec_():
            author_info = dialog.author_input.toPlainText().strip()
            if author_info:
                self.author_list.addItem(author_info)
                self.save_authors()

    def edit_author(self):
        current_item = self.author_list.currentItem()
        if current_item:
            dialog = AuthorInputDialog(self, current_item.text())
            if dialog.exec_():
                edited_author = dialog.author_input.toPlainText().strip()
                if edited_author:
                    current_item.setText(edited_author)
                    self.save_authors()
        else:
            QMessageBox.warning(self, "提示", "请先选择一个要编辑的作者。")

    def delete_author(self):
        current_row = self.author_list.currentRow()
        if current_row >= 0:
            reply = QMessageBox.question(self, "确认删除", "确定要删除选中的作者吗？",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.author_list.takeItem(current_row)
                self.save_authors()
        else:
            QMessageBox.warning(self, "提示", "请先选择一个要删除的作者。")
    def get_authors(self):
        return [self.author_list.item(i).text() for i in range(self.author_list.count())]


