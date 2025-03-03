import requests, os, json

# 配置仓库信息
OWNER = "Tejo29749"  # 仓库所有者
REPO = "FT_tool"  # 仓库名
BRANCH = "main"  # 分支名

# 获取脚本所在目录的上一级路径,并确保路径是绝对路径
script_dir = os.path.dirname(os.path.abspath(__file__))
LOCAL_SHA_FILE = os.path.join(script_dir, "latest_sha.json")  # 存储最新 SHA
DOWNLOAD_DIR = os.path.abspath(os.path.join(script_dir, ".."))

def get_latest_commit_sha():
    # 获取最新的 commit SHA
    latest_commit_url = f"https://api.github.com/repos/{OWNER}/{REPO}/commits/{BRANCH}"
    try:
        response = requests.get(latest_commit_url)
        if response.status_code == 200:
            return response.json()["sha"]
        else:
            print("无法获取最新的commit信息:", response.json())
            return None
    except:
        print("确认新版本失败，请检查网络")

def load_local_sha():
    # 加载本地存储的 SHA
    if os.path.exists(LOCAL_SHA_FILE):
        with open(LOCAL_SHA_FILE, "r") as f:
            return json.load(f).get("sha", "")
    return ""

def save_local_sha(sha):
    # 保存最新的 SHA 到本地
    with open(LOCAL_SHA_FILE, "w") as f:
        json.dump({"sha": sha}, f)

def get_changed_files(old_sha, new_sha):
    # 获取两个提交之间变更的文件
    diff_url = f"https://api.github.com/repos/{OWNER}/{REPO}/compare/{old_sha}...{new_sha}"
    response = requests.get(diff_url)
    if response.status_code == 200:
        files = response.json().get("files", [])
        added_modified = [f["filename"] for f in files if f["status"] in ("added", "modified")]
        deleted = [f["filename"] for f in files if f["status"] == "removed"]
        return added_modified, deleted
    else:
        print("获取变更文件失败:", response.json())
        return []

def download_file(file_path):
    # 下载 GitHub 上的文件
    raw_url = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/{BRANCH}/{file_path}"
    save_path = os.path.join(DOWNLOAD_DIR, file_path)
    os.makedirs(os.path.dirname(save_path), exist_ok=True)  # 确保目录存在
    response = requests.get(raw_url)
    if response.status_code == 200:
        with open(save_path, "wb") as f:
            f.write(response.content)
        print(f"下载成功: {file_path}")
    else:
        print(f"下载失败: {file_path}，错误: {response.status_code}")

def delete_local_file(file_path):
    # 删除本地已被仓库移除的文件
    local_path = os.path.join(DOWNLOAD_DIR, file_path)
    if os.path.exists(local_path):
        os.remove(local_path)
        print(f"已删除本地文件: {file_path}")

def main():
    latest_sha = get_latest_commit_sha()
    if not latest_sha:
        return
    local_sha = load_local_sha()

    if latest_sha != local_sha:
        print("检测到更新，开始下载变更的文件...")
        added_modified, deleted = get_changed_files(local_sha, latest_sha)
        # 下载新增和修改的文件
        for file in added_modified:
            download_file(file)
        # 删除仓库中已删除的文件
        for file in deleted:
            delete_local_file(file)

        save_local_sha(latest_sha)
        print("更新完成！")
    else:
        print("当前是最新版本")


if __name__ == "__main__":
    main()
