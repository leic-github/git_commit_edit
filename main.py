import json
import logging
import os
import random
import subprocess
import sys
import tempfile
from datetime import timedelta, datetime

from PyQt5.QtCore import QDateTime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QFileDialog, QListWidget, QMessageBox, QComboBox, QDialog,
    QFormLayout, QDateTimeEdit, QDialogButtonBox, QListWidgetItem, QTextEdit
)

CONFIG_PATH = "config.json"


# ---------------------- 配置函数 ----------------------
def save_config(data):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"配置保存失败: {e}")


def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_last_repo_path(path):
    config = load_config()
    config["last_path"] = path
    save_config(config)


def load_last_repo_path():
    return load_config().get("last_path", "")


def load_authors():
    config = load_config()
    if "authors" in config:
        return config["authors"]
    return []


# ---------------------- Git 工具函数 ----------------------
def run_git_command(cmd_list, cwd=None, env=None):
    try:
        # Windows下隐藏黑窗口
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        result = subprocess.run(
            cmd_list,
            cwd=cwd,
            capture_output=True,
            text=True,
            env=env,
            encoding='utf-8',
            errors='replace',
            startupinfo=startupinfo  # 添加这个
        )
        return result.stdout.strip()
    except Exception as e:
        return str(e)


def generate_rebase_editor_script(path):
    with open(path, "w", encoding="utf-8") as f:
        f.write(
            """import sys\nwith open(sys.argv[1], 'r+', encoding='utf-8') as f:\n    lines = f.readlines()\n    for i, line in enumerate(lines):\n        if line.startswith('pick '):\n            lines[i] = line.replace('pick', 'edit', 1)\n            break\n    f.seek(0)\n    f.writelines(lines)\n    f.truncate()\n""")


def generate_random_author_date(author_list, start_dt, end_dt):
    rand_author = random.choice(author_list)
    rand_time = start_dt + timedelta(seconds=random.randint(0, int((end_dt - start_dt).total_seconds())))
    formatted_date = rand_time.strftime("%Y-%m-%dT%H:%M:%S")

    author_name = rand_author.split("<")[0].strip()
    author_email = rand_author.split("<")[1].strip(" >")
    return author_name, author_email, formatted_date


def build_env(author_name, author_email, date, editor_script):
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = author_name
    env["GIT_AUTHOR_EMAIL"] = author_email
    env["GIT_COMMITTER_DATE"] = date
    env["GIT_AUTHOR_DATE"] = date
    python_path = "python" if hasattr(sys, "_MEIPASS") else sys.executable
    env["GIT_SEQUENCE_EDITOR"] = f'"{python_path}" "{editor_script}"'
    return env


def amend_commit(repo_path, env, message):
    subprocess.run([
        "git", "commit", "--amend",
        "--author", f"{env['GIT_AUTHOR_NAME']} <{env['GIT_AUTHOR_EMAIL']}>",
        "--date", env["GIT_AUTHOR_DATE"],
        "-m", message
    ], cwd=repo_path, env=env)


def rebase_continue(repo_path, env):
    subprocess.run(["git", "rebase", "--continue"], cwd=repo_path, env=env)


def rebase_interactive(repo_path, start_commit, env, is_root=False):
    if is_root:
        subprocess.run(["git", "rebase", "-i", "--root"], cwd=repo_path, env=env)
    else:
        subprocess.run(["git", "rebase", "-i", f"{start_commit}^"], cwd=repo_path, env=env)


def delete_temp_file(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


# ---------------------- 批量重写对话框 ----------------------
class BulkRewriteDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("批量重写提交作者与时间")

        self.authors_list = QListWidget()
        self.authors_list.setSelectionMode(QListWidget.MultiSelection)
        for author in load_authors():
            item = QListWidgetItem(author)
            self.authors_list.addItem(item)

        self.base_commit = QLineEdit()
        self.base_commit.setPlaceholderText("commit hash的前7位")
        self.base_commit.setMaxLength(7)

        self.start_time = QDateTimeEdit()
        self.start_time.setCalendarPopup(True)
        self.start_time.setDateTime(QDateTime.currentDateTime().addDays(-7))
        self.start_time.setDisplayFormat("yyyy-MM-dd HH:mm:ss")

        self.end_time = QDateTimeEdit()
        self.end_time.setCalendarPopup(True)
        self.end_time.setDateTime(QDateTime.currentDateTime())
        self.end_time.setDisplayFormat("yyyy-MM-dd HH:mm:ss")

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QFormLayout()
        layout.addRow("选择作者:", self.authors_list)
        layout.addRow("commit hash值:", self.base_commit)
        layout.addRow("开始时间:", self.start_time)
        layout.addRow("结束时间:", self.end_time)
        layout.addRow(buttons)

        self.setLayout(layout)

    def get_values(self):
        authors = [item.text() for item in self.authors_list.selectedItems()]
        start = self.start_time.dateTime().toPyDateTime()
        end = self.end_time.dateTime().toPyDateTime()
        base_commit = self.base_commit.text()
        return authors, start, end, base_commit


# ---------------------- 编辑对话框 ----------------------
class EditDialog(QDialog):
    def __init__(self, authors, author='', message='', datetime_str=''):
        super().__init__()
        self.setWindowTitle("编辑提交信息")
        self.author_input = QComboBox()
        self.author_input.setEditable(True)
        self.author_input.addItems(authors)
        self.author_input.setCurrentText(author)

        self.message_input = QTextEdit()
        self.message_input.setPlainText(message)

        self.date_input = QDateTimeEdit()
        self.date_input.setCalendarPopup(True)
        dt_py = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S %z")
        dt = QDateTime(dt_py)
        self.date_input.setDateTime(dt if dt.isValid() else QDateTime.currentDateTime())
        self.date_input.setDisplayFormat("yyyy-MM-dd HH:mm:ss")

        self.ok_button = QPushButton("确定")
        self.ok_button.clicked.connect(self.accept)

        layout = QFormLayout()
        layout.addRow("作者（如 user <user@example.com>）:", self.author_input)
        layout.addRow("提交信息:", self.message_input)
        layout.addRow("提交时间:", self.date_input)
        layout.addRow(self.ok_button)

        self.setLayout(layout)

    def get_values(self):
        return (
            self.author_input.currentText(),
            self.message_input.toPlainText(),
            self.date_input.dateTime().toString("yyyy-MM-ddTHH:mm:ss")
        )


# ---------------------- 主窗口 ----------------------
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMenu


class GitCommitEditor(QWidget):
    AUTHORS = load_authors()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Git Commit Editor (全功能整合版)")

        self.repo_path = QLineEdit()
        self.repo_path.setText(load_last_repo_path())

        browse_button = QPushButton("浏览")
        browse_button.clicked.connect(self.browse_repo)

        # load_button = QPushButton("加载提交记录")
        # load_button.clicked.connect(self.load_commits)

        self.branch_selector = QComboBox()
        self.branch_selector.currentIndexChanged.connect(self.load_commits)

        self.commit_listbox = QListWidget()
        self.commit_listbox.setContextMenuPolicy(Qt.CustomContextMenu)
        self.commit_listbox.customContextMenuRequested.connect(self.show_commit_context_menu)
        self.commit_listbox.itemDoubleClicked.connect(self.edit_commit)

        self.push_button = QPushButton("强推到远程")
        self.push_button.clicked.connect(self.push_force)

        self.rewrite_button = QPushButton("批量随机重写历史")
        self.rewrite_button.clicked.connect(self.rewrite_commits_randomly)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("选择Git仓库目录:"))
        layout.addWidget(self.repo_path)
        layout.addWidget(browse_button)
        layout.addWidget(QLabel("选择分支:"))
        layout.addWidget(self.branch_selector)
        # layout.addWidget(load_button)
        layout.addWidget(self.commit_listbox)
        layout.addWidget(self.rewrite_button)
        layout.addWidget(self.push_button)

        self.setLayout(layout)
        self.root_commit_log = ''

        if self.repo_path.text() != "":
            self.load_branches()

    def browse_repo(self):
        file_path = self.repo_path.text() if self.repo_path.text() != '' else '.'
        path = QFileDialog.getExistingDirectory(self, "选择Git仓库", file_path)

        if path.strip() != "" and os.path.isdir(path):
            if not os.path.exists(os.path.join(path, '.git')):
                QMessageBox.warning(self, "错误", "不是Git仓库")
                return
            self.repo_path.setText(path)
            save_last_repo_path(path)
            self.load_branches()

    def load_branches(self):
        repo = self.repo_path.text()
        if not os.path.isdir(repo):
            return
        output = run_git_command(["git", "branch"], cwd=repo)
        branches = [line for line in output.split("\n") if line.strip() != '']
        if not len(branches):
            QMessageBox.critical(self, "失败", "无法获取分支列表")
            return
        items = []
        current = ""
        for branch in branches:
            if branch.startswith("*"):
                branch = branch[1:].strip()
                current = branch
            else:
                branch = branch.strip()
            items.append(branch)
        self.branch_selector.clear()
        if not len(items):
            return
        self.branch_selector.addItems(items)
        # 设置当前分支
        if current != "":
            self.branch_selector.setCurrentText(current)
            self.load_commits()

    def load_commits(self):
        repo = self.repo_path.text()
        branch = self.branch_selector.currentText()
        if branch == "":
            return
        result = subprocess.run(["git", "checkout", branch], cwd=repo, capture_output=True, text=True)
        if result.returncode != 0:
            QMessageBox.critical(self, "失败", result.stderr)
            return
        cmd = ["git", "log", branch, "--pretty=format:%h %an <%ae> %ad %s %d", "--date=iso"]
        output = run_git_command(cmd, cwd=repo)
        self.commit_listbox.clear()
        commit_logs = output.splitlines()
        if not len(commit_logs):
            QMessageBox.critical(self, "失败", "无法获取提交记录")
            return
        # 记录当前分支的根记录
        self.root_commit_log = commit_logs[-1].split(' ')[0]
        self.commit_listbox.addItems(commit_logs)

    def rewrite_commits_randomly(self):
        dialog = BulkRewriteDialog()
        if dialog.exec_():
            authors, start, end, base_commit = dialog.get_values()
            if not len(authors):
                QMessageBox.critical(self, "失败", "请选择作者")
                return
            repo = self.repo_path.text()
            branch = self.branch_selector.currentText()

            commits = run_git_command(["git", "rev-list", branch], cwd=repo).splitlines()

            new_commits = [commit[:7] for commit in commits]
            if base_commit != "" and base_commit in new_commits:
                index = new_commits.index(base_commit)
                index = index+1 if index<(len(commits)-1) else -1
                commits = commits[:index]

            total = len(commits)
            seconds_range = int((end - start).total_seconds())
            time_steps = sorted([random.randint(0, seconds_range) for _ in range(total)], reverse=True)

            # 忽略第一次提交，因为无法修改
            for i, commit in enumerate(commits):
                rand_time = start + timedelta(seconds=time_steps[i])
                formatted_date = rand_time.strftime("%Y-%m-%dT%H:%M:%S")
                rand_author = random.choice(authors)
                name = rand_author.split("<")[0].strip()
                email = rand_author.split("<")[1].strip(" >")
                _, _, message = self.get_commit_info(commit)
                script_path = os.path.join(tempfile.gettempdir(), f"editor_{commit}.py")
                generate_rebase_editor_script(script_path)
                env = build_env(name, email, formatted_date, script_path)

                rebase_interactive(repo, commit, env, self.root_commit_log in commit)
                amend_commit(repo, env, message)
                rebase_continue(repo, env)
                delete_temp_file(script_path)

            self.load_commits()
            QMessageBox.information(self, "完成", "批量重写完成")

    def push_force(self):
        repo = self.repo_path.text()
        branch = self.branch_selector.currentText()
        remotes = run_git_command(["git", "branch", "-r"], cwd=repo).splitlines()
        if not any(f"origin/{branch}" in r for r in remotes):
            QMessageBox.warning(self, "警告", f"远程未检测到分支 {branch}")
            return
        result = subprocess.run(["git", "push", "origin", branch, "--force"], cwd=repo, capture_output=True, text=True)
        if result.returncode == 0:
            QMessageBox.information(self, "成功", "强推完成")
        else:
            QMessageBox.critical(self, "失败", result.stderr)

    def edit_commit(self, item):
        selected_commit = item.text().split()[0]

        author, date, message = self.get_commit_info(selected_commit)

        dialog = EditDialog(authors=GitCommitEditor.AUTHORS, author=author, message=message, datetime_str=date)

        if dialog.exec_():
            new_author, new_msg, new_date = dialog.get_values()

            if not new_author or not new_msg or not new_date:
                QMessageBox.information(self, "提示", "作者、信息或时间不能为空")
                return

            repo_path = self.repo_path.text()
            try:
                author_name = new_author.split("<")[0].strip()
                author_email = new_author.split("<")[1].strip(" >")

                full_log = self.run_git_command(
                    ["git", "rev-list", self.branch_selector.currentText()],
                    cwd=repo_path
                ).splitlines()
                full_log = [v[:7] for v in full_log]
                if selected_commit not in full_log:
                    QMessageBox.critical(self, "错误", "未能在分支中找到该提交")
                    return

                index = full_log.index(selected_commit)
                # if index == len(full_log) - 1:
                #     QMessageBox.warning(self, "提示", "无法 rebase 第一个提交")
                #     return

                rebase_start = full_log[index]

                editor_script = os.path.join(tempfile.gettempdir(), "rebase_editor.py")
                generate_rebase_editor_script(editor_script)
                env = build_env(author_name, author_email, new_date, editor_script)

                # 根提交记录的修改
                rebase_interactive(repo_path, rebase_start, env, self.root_commit_log in rebase_start)

                amend_commit(repo_path, env, new_msg)

                rebase_continue(repo_path, env)

                os.remove(editor_script)
                self.load_commits()
                QMessageBox.information(self, "成功", "提交修改成功！")

            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))

    def get_commit_info(self, selected_commit):
        try:
            output = self.run_git_command(
                ["git", "show", selected_commit, "--quiet", "--pretty=format:%an <%ae>%n%ad%n%s", "--date=iso"],
                cwd=self.repo_path.text())
            lines = output.splitlines()
            if len(lines) < 3:
                QMessageBox.critical(self, "错误", "获取提交信息失败，可能是 Git 命令错误或提交记录异常")
                return None
            author, date, message = lines
            return author, date, message
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))
            return None

    def show_commit_context_menu(self, position):
        item = self.commit_listbox.itemAt(position)
        if item is None:
            return

        menu = QMenu()
        copy_action = menu.addAction("复制提交哈希值")
        action = menu.exec_(self.commit_listbox.mapToGlobal(position))

        if action == copy_action:
            commit_hash = item.text().split()[0]
            QApplication.clipboard().setText(commit_hash)
            QMessageBox.information(self, "已复制", f"提交哈希值已复制到剪贴板：{commit_hash}")

    def run_git_command(self, cmd_list, cwd=None, env=None):
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            result = subprocess.run(
                cmd_list,
                cwd=cwd,
                capture_output=True,
                text=True,
                env=env,
                encoding='utf-8',
                errors='replace',
                startupinfo=startupinfo
            )
            return result.stdout.strip()
        except Exception as e:
            QMessageBox.critical(self, "命令执行出错", str(e))
            return ""


def log_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    print("Uncaught exception")
    logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    QMessageBox.information(None, '未知错误', str(exc_type) + '\n' + str(exc_value) + '\n' + str(exc_traceback))


sys.excepthook = log_exception
if __name__ == '__main__':
    try:
        app = QApplication(sys.argv)
        editor = GitCommitEditor()
        editor.show()
        sys.exit(app.exec_())
    except Exception as e:
        print("An error occurred:", e)
        sys.exit(1)
