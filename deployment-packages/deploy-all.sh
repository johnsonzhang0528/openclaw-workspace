#!/bin/bash

# OpenClaw 功能擴展部署腳本
# 版本: v1.0.0
# 創建日期: 2026-02-11

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日誌函數
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 檢查函數
check_openclaw_installed() {
    if command -v openclaw &> /dev/null; then
        log_info "OpenClaw 已安裝: $(openclaw --version 2>/dev/null || echo '未知版本')"
        return 0
    else
        log_error "OpenClaw 未安裝"
        return 1
    fi
}

check_python_version() {
    local python_version=$(python3 --version 2>&1 | awk '{print $2}')
    local major=$(echo $python_version | cut -d. -f1)
    local minor=$(echo $python_version | cut -d. -f2)
    
    if [ $major -eq 3 ] && [ $minor -ge 8 ]; then
        log_info "Python 版本符合要求: $python_version"
        return 0
    else
        log_error "Python 版本過低: $python_version (需要 3.8+)"
        return 1
    fi
}

check_dependencies() {
    log_info "檢查系統依賴..."
    
    # 檢查必要命令
    local commands=("cp" "mkdir" "chmod" "systemctl" "journalctl")
    for cmd in "${commands[@]}"; do
        if ! command -v $cmd &> /dev/null; then
            log_error "缺少必要命令: $cmd"
            return 1
        fi
    done
    
    # 檢查 Python 模組
    local python_modules=("psutil" "requests" "telegram")
    for module in "${python_modules[@]}"; do
        if ! python3 -c "import $module" 2>/dev/null; then
            log_warning "缺少 Python 模組: $module"
            log_info "嘗試安裝: pip3 install $module"
            pip3 install $module || {
                log_error "無法安裝 $module"
                return 1
            }
        fi
    done
    
    log_success "所有依賴檢查通過"
    return 0
}

# 部署函數
deploy_skill() {
    local skill_name=$1
    local source_dir=$2
    local target_dir="/usr/lib/node_modules/openclaw/skills/$skill_name"
    
    log_info "部署技能: $skill_name"
    
    # 檢查來源目錄
    if [ ! -d "$source_dir" ]; then
        log_error "來源目錄不存在: $source_dir"
        return 1
    fi
    
    # 備份現有技能（如果存在）
    if [ -d "$target_dir" ]; then
        local backup_dir="${target_dir}.backup.$(date +%Y%m%d_%H%M%S)"
        log_info "備份現有技能到: $backup_dir"
        cp -r "$target_dir" "$backup_dir"
    fi
    
    # 部署技能
    log_info "複製技能檔案到: $target_dir"
    mkdir -p "$(dirname "$target_dir")"
    cp -r "$source_dir" "$target_dir"
    
    # 設置權限
    chmod -R 755 "$target_dir"
    
    # 檢查部署結果
    if [ -f "$target_dir/SKILL.md" ] && [ -f "$target_dir/main.py" ]; then
        log_success "技能部署成功: $skill_name"
        return 0
    else
        log_error "技能部署失敗: $skill_name"
        return 1
    fi
}

update_openclaw_config() {
    local config_file="/root/.openclaw/openclaw.json"
    
    log_info "更新 OpenClaw 配置"
    
    # 檢查配置檔案是否存在
    if [ ! -f "$config_file" ]; then
        log_error "OpenClaw 配置檔案不存在: $config_file"
        return 1
    fi
    
    # 備份配置檔案
    local backup_file="${config_file}.backup.$(date +%Y%m%d_%H%M%S)"
    cp "$config_file" "$backup_file"
    log_info "配置備份到: $backup_file"
    
    # 創建臨時配置檔案
    local temp_file="/tmp/openclaw_config_$(date +%s).json"
    
    # 使用 Python 更新配置
    python3 -c "
import json
import sys

config_file = '$config_file'
temp_file = '$temp_file'

try:
    # 讀取現有配置
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    # 確保 skills 部分存在
    if 'skills' not in config:
        config['skills'] = {}
    
    # 添加新技能配置
    skills_to_add = {
        'skills-marketplace': {
            'enabled': True,
            'telegram_enabled': True,
            'marketplace_url': 'https://clawhub.com',
            'cache_duration': 300,
            'update_check_interval': 3600
        },
        'workspace-manager': {
            'enabled': True,
            'telegram_enabled': True,
            'default_path': '/root/.openclaw/workspace',
            'max_file_size': 10485760,
            'allowed_extensions': ['.py', '.md', '.txt', '.json', '.yaml', '.yml']
        },
        'performance-monitor': {
            'enabled': True,
            'telegram_enabled': True,
            'collection_interval': 5,
            'alert_thresholds': {
                'cpu': 80,
                'memory': 85,
                'disk': 90
            },
            'retention_days': 7
        },
        'smart-shortcuts': {
            'enabled': True,
            'telegram_enabled': True,
            'max_shortcuts': 100,
            'template_path': '/root/.openclaw/shortcut-templates',
            'execution_timeout': 30
        }
    }
    
    # 合併配置（不覆蓋現有配置）
    for skill_name, skill_config in skills_to_add.items():
        if skill_name not in config['skills']:
            config['skills'][skill_name] = skill_config
        else:
            # 合併現有配置
            for key, value in skill_config.items():
                if key not in config['skills'][skill_name]:
                    config['skills'][skill_name][key] = value
    
    # 寫入臨時檔案
    with open(temp_file, 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print('配置更新成功')
    
except Exception as e:
    print(f'配置更新失敗: {e}')
    sys.exit(1)
" || {
        log_error "配置更新失敗"
        return 1
    }
    
    # 替換原配置檔案
    mv "$temp_file" "$config_file"
    chmod 600 "$config_file"
    
    log_success "OpenClaw 配置更新完成"
    return 0
}

restart_openclaw_service() {
    log_info "重啟 OpenClaw 服務"
    
    # 檢查服務狀態
    if systemctl is-active openclaw.service &> /dev/null; then
        log_info "重新啟動 OpenClaw 服務"
        systemctl restart openclaw.service || {
            log_error "重啟 OpenClaw 服務失敗"
            return 1
        }
    else
        log_info "啟動 OpenClaw 服務"
        systemctl start openclaw.service || {
            log_error "啟動 OpenClaw 服務失敗"
            return 1
        }
    fi
    
    # 等待服務啟動
    log_info "等待服務啟動..."
    sleep 5
    
    # 檢查服務狀態
    if systemctl is-active openclaw.service &> /dev/null; then
        log_success "OpenClaw 服務運行正常"
        return 0
    else
        log_error "OpenClaw 服務啟動失敗"
        return 1
    fi
}

verify_deployment() {
    log_info "驗證部署結果"
    
    local skills=("skills-marketplace" "workspace-manager" "performance-monitor" "smart-shortcuts")
    local success=true
    
    for skill in "${skills[@]}"; do
        local skill_dir="/usr/lib/node_modules/openclaw/skills/$skill"
        
        if [ -d "$skill_dir" ] && [ -f "$skill_dir/SKILL.md" ] && [ -f "$skill_dir/main.py" ]; then
            log_info "✓ $skill 部署成功"
        else
            log_error "✗ $skill 部署失敗"
            success=false
        fi
    done
    
    if $success; then
        log_success "所有技能部署驗證通過"
        return 0
    else
        log_error "部分技能部署失敗"
        return 1
    fi
}

# 主函數
main() {
    log_info "開始部署 OpenClaw 功能擴展"
    log_info "========================================"
    
    # 檢查當前目錄
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local parent_dir="$(dirname "$script_dir")"
    
    log_info "工作目錄: $parent_dir"
    
    # 執行檢查
    check_openclaw_installed || exit 1
    check_python_version || exit 1
    check_dependencies || exit 1
    
    # 部署技能
    log_info "========================================"
    log_info "開始部署技能"
    
    deploy_skill "skills-marketplace" "$parent_dir/skills-marketplace" || exit 1
    deploy_skill "workspace-manager" "$parent_dir/workspace-manager" || exit 1
    deploy_skill "performance-monitor" "$parent_dir/performance-monitor" || exit 1
    deploy_skill "smart-shortcuts" "$parent_dir/smart-shortcuts" || exit 1
    
    # 更新配置
    log_info "========================================"
    update_openclaw_config || exit 1
    
    # 重啟服務
    log_info "========================================"
    restart_openclaw_service || exit 1
    
    # 驗證部署
    log_info "========================================"
    verify_deployment || exit 1
    
    # 完成
    log_info "========================================"
    log_success "OpenClaw 功能擴展部署完成！"
    log_info ""
    log_info "🎉 部署完成！"
    log_info ""
    log_info "現在您可以使用以下命令："
    log_info "  /技能市集     - 瀏覽和安裝技能"
    log_info "  /工作空間     - 管理檔案和目錄"
    log_info "  /效能監控     - 監控系統資源"
    log_info "  /快捷指令     - 創建和使用快捷指令"
    log_info ""
    log_info "快捷命令："
    log_info "  /sm, /ws, /pm, /sc"
    log_info ""
    log_info "查看詳細文檔："
    log_info "  cat $parent_dir/user-docs.md | less"
    log_info ""
    log_info "如有問題，請檢查日誌："
    log_info "  journalctl -u openclaw -f"
}

# 執行主函數
main "$@"