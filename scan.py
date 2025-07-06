#!/usr/bin/env python3
import os
import sys
import json
import base64
from datetime import datetime
import requests
import subprocess

# 配置参数
GITHUB_TOKEN = "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"
REPO_OWNER = "key5499"
REPO_NAME = "ServerConfig"
BRANCH = "main"
IP_FILE_PATH = "ip.txt"  # 仓库根目录下的ip.txt
SCAN_RESULTS_DIR = "scan_results"
PORTS = [4899, 7899]  # 要扫描的端口列表
SCAN_RATE = 1000  # 扫描速率

def download_ip_file():
    """从GitHub下载IP列表文件"""
    url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/{IP_FILE_PATH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3.raw"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        with open("ip.txt", "wb") as f:
            f.write(response.content)
            
        if os.path.getsize("ip.txt") == 0:
            raise Exception("下载的IP文件为空")
            
        print("成功下载IP列表文件")
    except Exception as e:
        print(f"下载IP文件失败: {e}")
        sys.exit(1)

def run_masscan(port):
    """运行masscan扫描指定端口"""
    output_file = f"scan_{port}.json"
    
    try:
        cmd = [
            "sudo", "masscan",
            "-iL", "ip.txt",
            "-p", str(port),
            "--rate", str(SCAN_RATE),
            "-oJ", output_file
        ]
        
        subprocess.run(cmd, check=True)
        
        if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
            return None
            
        return output_file
    except subprocess.CalledProcessError as e:
        print(f"扫描端口 {port} 失败: {e}")
        return None

def extract_ips_from_result(result_file):
    """从扫描结果中提取IP地址"""
    try:
        with open(result_file, "r") as f:
            data = json.load(f)
            
        ips = set()
        for item in data:
            ips.add(item["ip"])
            
        return sorted(ips)
    except Exception as e:
        print(f"解析扫描结果失败: {e}")
        return []

def upload_to_github(port, ips):
    """将扫描结果上传到GitHub"""
    if not ips:
        print(f"端口 {port} 没有发现开放IP，跳过上传")
        return
        
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{port}_{len(ips)}.txt"
    content = "\n".join(ips) + "\n"
    
    # Base64编码内容
    content_b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    
    # 准备API请求
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{SCAN_RESULTS_DIR}/{filename}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "message": f"添加扫描结果 {port} ({len(ips)}个IP)",
        "content": content_b64,
        "branch": BRANCH
    }
    
    try:
        response = requests.put(url, headers=headers, json=data)
        response.raise_for_status()
        print(f"成功上传结果: {filename}")
    except Exception as e:
        print(f"上传结果失败: {e}")

def check_masscan_installed():
    """检查masscan是否已安装"""
    try:
        subprocess.run(["masscan", "--version"], 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE,
                      check=True)
        return True
    except:
        return False

def install_masscan():
    """安装masscan"""
    print("正在安装masscan...")
    try:
        subprocess.run(["sudo", "apt-get", "update"], check=True)
        subprocess.run(["sudo", "apt-get", "install", "-y", "masscan"], check=True)
        print("masscan安装成功")
    except subprocess.CalledProcessError as e:
        print(f"安装masscan失败: {e}")
        sys.exit(1)

def main():
    # 检查并安装masscan
    if not check_masscan_installed():
        install_masscan()
    
    # 下载IP列表
    # download_ip_file()
    
    # 扫描每个端口
    for port in PORTS:
        print(f"\n开始扫描端口 {port}...")
        
        # 运行扫描
        result_file = run_masscan(port)
        if not result_file:
            continue
            
        # 提取IP地址
        ips = extract_ips_from_result(result_file)
        
        # 上传结果
        upload_to_github(port, ips)
        
        # 清理临时文件
        os.remove(result_file)
    
    # 清理IP文件
    os.remove("ip.txt")
    print("\n所有端口扫描完成!")

if __name__ == "__main__":
    main()
