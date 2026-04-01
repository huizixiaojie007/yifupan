#!/bin/bash
# 安装认证功能所需的依赖

echo "正在安装认证功能依赖..."

pip install python-jose[cryptography]
pip install passlib[bcrypt]
pip install email-validator

echo "依赖安装完成！"

