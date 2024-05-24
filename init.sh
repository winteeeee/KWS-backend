#!/bin/bash
# chmod +x init.sh (실행 권한 부여) 이후 실행

set -o xtrace

# 종속성 설치
sudo apt update
sudo apt upgrade -y
sudo apt install python3-pip -y
python3 -m pip install -r requirements.txt

# 서버 실행
cd src
python3 main.py&