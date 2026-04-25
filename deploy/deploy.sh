#!/bin/bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

if [[ $EUID -eq 0 ]]; then
   log_warn "建议不要使用 root 用户运行此脚本"
fi

if ! command -v docker &> /dev/null; then
    log_error "Docker 未安装"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

log_info "开始部署 OCR 审计文档处理系统..."

log_info "创建必要的目录..."
sudo mkdir -p /data/ocr_project/{ocr_results,tmp_uploads,logs}
sudo mkdir -p "$PROJECT_DIR/nginx/ssl"

if [ ! -f "$PROJECT_DIR/deploy/production.env" ]; then
    log_warn "production.env 文件不存在，复制模板..."
    cp "$PROJECT_DIR/deploy/production.env.example" "$PROJECT_DIR/deploy/production.env"
    log_warn "请编辑 production.env 文件配置生产环境参数"
    exit 1
fi

set -a
source "$PROJECT_DIR/deploy/production.env"
set +a

log_info "构建前端..."
cd "$PROJECT_DIR/frontend"
npm install
npm run build
cd "$PROJECT_DIR"

log_info "构建 Docker 镜像..."
docker compose -f "$PROJECT_DIR/deploy/production.yml" build

log_info "启动服务..."
docker compose -f "$PROJECT_DIR/deploy/production.yml" up -d

log_info "等待服务就绪..."
sleep 10

log_info "检查服务状态..."
docker compose -f "$PROJECT_DIR/deploy/production.yml" ps

if curl -sf http://localhost:8200/health > /dev/null; then
    log_info "Backend API 健康检查通过"
else
    log_error "Backend API 健康检查失败"
fi

log_info "部署完成!"
