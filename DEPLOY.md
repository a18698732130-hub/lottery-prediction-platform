# 部署指南 (Deployment Guide)

本指南旨在帮助您在已运行其他服务的 Docker 服务器上安全部署本应用。

## 1. 准备工作

### 上传代码
将项目文件上传到服务器的独立目录，例如 `/root/lottery-prediction`。

### 检查端口
本应用默认使用 **8501** 端口。如果该端口已被占用，请修改 `docker-compose.yml` 中的 `ports` 部分：
```yaml
ports:
  - "8501:8501"  # 格式为 "外部端口:内部端口"，例如改为 "9090:8501"
```

## 2. 安全启动 (不影响其他服务)

为了确保不干扰服务器上的其他应用，我们建议指定**项目名称 (Project Name)** 进行启动。

进入项目目录：
```bash
cd /root/lottery-prediction
```

**构建并启动：**
```bash
# -p lottery 指定项目名称，确保与其他 docker-compose 项目隔离
# -d 后台运行
docker compose -p lottery up -d --build
```

## 3. 日常维护命令

由于我们指定了项目名称 `lottery`，后续的所有命令也建议加上 `-p lottery`，或者直接针对服务操作。

**查看日志：**
```bash
# 查看 lottery-app 服务的日志
docker compose -p lottery logs -f lottery-app
```

**停止服务 (仅停止本应用)：**
```bash
docker compose -p lottery stop lottery-app
```

**重启服务：**
```bash
docker compose -p lottery restart lottery-app
```

**彻底移除 (停止并删除容器)：**
```bash
# 这只会移除本项目的容器，不会影响其他项目
docker compose -p lottery down
```

## 4. 数据备份
所有数据（数据库、历史记录）都保存在服务器的 `./data` 目录下。
如果需要备份，只需复制该目录即可：
```bash
cp -r ./data ./data_backup_2023
```
