import os
import requests
import subprocess


script_dir = os.path.dirname(os.path.abspath(__file__))
# GitHub仓库信息
repo_owner = 'Tejo29749'
repo_name = 'FT_tool'
file_path = 'tool/FieldTest_tool.py'
local_file = os.path.join(script_dir, 'FieldTest_tool.py')

# 本地commit信息
commit_hash_path = os.path.join(script_dir, 'commit_hash.txt')

# 获取最新的commit hash
def get_latest_commit():
    url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/commits/main'
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()['sha']
        else:
            print('无法获取最新的commit信息')
            return None
    except:
        print("确认新版本失败，请检查网络")

# 下载最新的文件
def download_latest_file():
    url = f'https://raw.githubusercontent.com/{repo_owner}/{repo_name}/main/{file_path}'
    try:
        response = requests.get(url)
    except:
        print("下载新版本失败，请检查网络")
    if response.status_code == 200:
        with open(local_file, 'wb') as f:
            f.write(response.content)
        print('文件已更新')
    else:
        print('无法下载最新的文件')

# 检查并更新文件
def check_and_update():
    latest_commit = get_latest_commit()
    if latest_commit:
        with open(commit_hash_path, 'r') as f:
            current_commit = f.read().strip()
        if current_commit != latest_commit:
            download_latest_file()
            with open(commit_hash_path, 'w') as f:
                f.write(latest_commit)
            print('开始启动测试工具...')
            # subprocess.run(['python', local_file])
        else:
            print('文件已是最新版本')
            # subprocess.run(['python', local_file])

if __name__ == '__main__':
    check_and_update()
