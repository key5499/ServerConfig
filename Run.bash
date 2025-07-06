#!/bin/bash

# 配置参数
GITHUB_TOKEN="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"
REPO_OWNER="key5499"                           # 仓库所有者用户名
REPO_NAME="ServerConfig"                       # 仓库名称
BRANCH="main"                                  # 分支名称
IP_FILE_PATH="ip.txt"                          # IP文件在仓库中的路径（直接在主目录下）
SCAN_RESULTS_DIR="scan_results"                # 结果存储目录

# 端口范围 (示例: 80 443 8080-8090)
# PORTS="4899 5899 6899 7899 8999 1111 2222 3333 4444 5555 6666 7777 8888 9999 1234 2345 3456 4567 6789 7890 1000 2000 3000 4000 5000 6000 7000 8000 9000 10086 1024 2048 1433 3389 3306 3030 4040 5050 6060 7070 8080 9090 1001 2002 3003 4004 5005 6006 7007 8008 9009 10000 20000 30000 40000 50000 60000 9010 9020 9030 9040 9050 9060 9070 9080 9090 2020 2021 2022 2023 2024 2025" 
PORTS="4899 7899"

# 步骤1：下载IP列表
echo "下载IP列表..."
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3.raw" \
  -o ip.txt \
  "https://raw.githubusercontent.com/$REPO_OWNER/$REPO_NAME/$BRANCH/$IP_FILE_PATH"

[ -s ip.txt ] || { echo "错误：IP文件为空或下载失败"; exit 1; }

# 安装masscan (如果未安装)
if ! command -v masscan &> /dev/null; then
  sudo apt-get update && sudo apt-get install -y masscan
fi

# 步骤2：逐个端口扫描
for PORT in $PORTS; do
  echo "扫描端口: $PORT ..."
  
  # 临时结果文件
  TEMP_RESULT="temp_scan.json"
  
  # 运行扫描
  sudo masscan -iL ip.txt -p$PORT --rate=10000 -oJ $TEMP_RESULT
  
  # 提取IP地址 (使用jq处理JSON)
  if [ -s "$TEMP_RESULT" ]; then
    IPS=$(jq -r '.[] | .ip' $TEMP_RESULT | sort -u)
    COUNT=$(echo "$IPS" | wc -l)
    
    # 生成文件名
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    RESULT_FILENAME="${TIMESTAMP}_${PORT}_${COUNT}.txt"
    
    # 保存IP列表
    echo "$IPS" > $RESULT_FILENAME
    
    # 上传到GitHub
    BASE64_CONTENT=$(base64 -w0 $RESULT_FILENAME)
    JSON_PAYLOAD=$(jq -n \
      --arg msg "扫描结果 $PORT ($COUNT个IP)" \
      --arg content "$BASE64_CONTENT" \
      --arg branch "$BRANCH" \
      '{message: $msg, content: $content, branch: $branch}')
    
    curl -s -X PUT \
      -H "Authorization: token $GITHUB_TOKEN" \
      -H "Content-Type: application/json" \
      -d "$JSON_PAYLOAD" \
      "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME/contents/$SCAN_RESULTS_DIR/$RESULT_FILENAME"
    
    echo "已上传: $RESULT_FILENAME"
    rm -f $RESULT_FILENAME $TEMP_RESULT
  else
    echo "端口 $PORT 无开放主机"
  fi
done

echo "所有端口扫描完成!"
