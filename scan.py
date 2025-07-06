#!/usr/bin/env python3
import os
import json
import base64
from datetime import datetime
import requests
import subprocess
import getpass  # 用于安全输入Token

# 配置参数（不包含敏感信息）
REPO_OWNER = "key5499"
REPO_NAME = "ServerConfig"
BRANCH = "main"
SCAN_RESULTS_DIR = "scan_results"
PORTS = [4899, 7899]  # 要扫描的端口列表
SCAN_RATE = 20000  # 扫描速率

def get_github_token():
    """安全地从命令行获取GitHub Token"""
    print("\n请输入GitHub个人访问令牌（输入时不会显示）")
    print("注意：Token需要repo权限")
    print("获取地址：https://github.com/settings/tokens/new?scopes=repo")
    return getpass.getpass("Token: ").strip()

def run_masscan(port):
    """运行masscan扫描指定端口"""
    output_file = f"scan_{port}.json"
    
    try:
        cmd = [
            "masscan",
            "-iL", "ip.txt",
            "-p", str(port),
            "--rate", str(SCAN_RATE),
            "-oJ", output_file
        ]
        
        subprocess.run(cmd, check=True)
        return output_file if os.path.exists(output_file) and os.path.getsize(output_file) > 0 else None
    except subprocess.CalledProcessError as e:
        print(f"扫描端口 {port} 失败: {e}")
        return None

def extract_ips(result_file):
    """从扫描结果中提取IP地址"""
    try:
        with open(result_file) as f:
            return sorted({item["ip"] for item in json.load(f)})
    except Exception as e:
        print(f"解析扫描结果失败: {e}")
        return []

def upload_results(port, ips, token):
    """上传结果到GitHub"""
    if not ips:
        print(f"端口 {port} 无开放主机，跳过上传")
        return

    # 准备文件内容
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{port}_{len(ips)}.txt"
    content = "\n".join(ips) + "\n"
    
    # API请求配置
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{SCAN_RESULTS_DIR}/{filename}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    data = {
        "message": f"Add scan results for port {port}",
        "content": base64.b64encode(content.encode()).decode(),
        "branch": BRANCH
    }

    # 执行上传
    try:
        response = requests.put(url, headers=headers, json=data)
        response.raise_for_status()
        print(f"结果已上传: {filename}")
    except requests.HTTPError as e:
        print(f"上传失败 (HTTP {response.status_code}): {response.text}")
    except Exception as e:
        print(f"上传出错: {str(e)}")

def main():
    # 1. 获取GitHub Token
    token = get_github_token()
    
    # 2. 检查ip.txt是否存在
    if not os.path.exists("ip.txt"):
        print("错误：当前目录下未找到ip.txt文件")
        print("请创建包含IP地址列表的ip.txt文件（每行一个IP）")
        return

    # 3. 扫描并上传结果
    for port in PORTS:
        print(f"\n扫描端口 {port}...")
        if result_file := run_masscan(port):
            if ips := extract_ips(result_file):
                upload_results(port, ips, token)
            os.remove(result_file)

    print("\n扫描任务完成")

if __name__ == "__main__":
    main()
