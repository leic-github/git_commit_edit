import os
from datetime import datetime, timezone, timedelta


class CallbackScriptBuilder:
    @staticmethod
    def build_bulk_commit_callback(filepath: str, commit_changes: dict) -> bool:
        """
        生成 callback 脚本，针对多次提交，每个提交设置独立的 author/email/date/message
        """
        try:
            import json
            changes_json = json.dumps(commit_changes, indent=2, ensure_ascii=False)

            content = f'''
from datetime import datetime, timezone, timedelta

commit_changes = {changes_json}
commit_id = commit.original_id.decode()[:7]
if commit_id in commit_changes:
    change = commit_changes[commit_id]
    commit.author_name = change["name"].encode("utf-8")
    commit.author_email = change["email"].encode("utf-8")
    commit.committer_name = change["name"].encode("utf-8")
    commit.committer_email = change["email"].encode("utf-8")

    dt = datetime.strptime(change["date"], "%Y-%m-%dT%H:%M:%S")
    dt = dt.replace(tzinfo=timezone(timedelta(hours=8)))
    timestamp = int(dt.timestamp())
    commit.author_date = f"{{timestamp}} +0800".encode("utf-8")
    commit.committer_date = f"{{timestamp}} +0800".encode("utf-8")
    commit.message = change["message"].encode("utf-8")
'''
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8", newline="\n") as f:
                f.write(content.lstrip())
            return True
        except Exception as e:
            print(f"[CallbackScriptBuilder] 错误: {e}")
            return False

    @staticmethod
    def build_single_commit_callback(
            filepath: str,
            target_hash: str,
            author_name: str,
            author_email: str,
            commit_message: str,
            date_str: str
    ):
        """
        生成 callback 脚本（用于 git-filter-repo），只修改一个指定提交
        """
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
            safe_msg = commit_message.replace('"""', r'\"\"\"')

            new_dt = datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second,
                              tzinfo=timezone(timedelta(hours=8)))
            timestamp = int(new_dt.timestamp())

            def encode_line(key: str, value: str) -> str:
                return f'commit.{key} = "{value}".encode("utf-8")'

            content = f'''
if commit.original_id.decode()[:7] == "{target_hash}":
    {encode_line("author_name", author_name)}
    {encode_line("author_email", author_email)}
    {encode_line("committer_name", author_name)}
    {encode_line("committer_email", author_email)}
    commit.message = "{safe_msg}".encode("utf-8")
    commit.author_date = f"{timestamp} +0800".encode("utf-8")  # 格式化为字节
    commit.committer_date = f"{timestamp} +0800".encode("utf-8")  # 格式化为字节
'''

            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"CallbackScriptBuilder 错误: {e}")
            return False
