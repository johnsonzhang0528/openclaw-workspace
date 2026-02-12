#!/bin/bash

# OpenClaw 技能部署腳本
# 自動化部署流程

set -e  # 遇到錯誤時退出

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

# 檢查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        log_error "命令 '$1' 未找到，請先安裝"
        exit 1
    fi
}

# 顯示幫助
show_help() {
    echo "OpenClaw 技能部署腳本"
    echo ""
    echo "用法: $0 [選項] <技能名稱>"
    echo ""
    echo "選項:"
    echo "  -h, --help          顯示此幫助訊息"
    echo "  -t, --test          運行測試後再部署"
    echo "  -c, --coverage      檢查測試覆蓋率"
    echo "  -l, --lint          運行程式碼檢查"
    echo "  -f, --force         強制部署（跳過檢查）"
    echo "  -d, --dry-run       模擬部署，不實際執行"
    echo "  -v, --version       顯示版本"
    echo ""
    echo "範例:"
    echo "  $0 my-skill         部署 my-skill 技能"
    echo "  $0 -t my-skill      運行測試後部署"
    echo "  $0 -tcl my-skill    運行所有檢查後部署"
    echo ""
}

# 顯示版本
show_version() {
    echo "OpenClaw 技能部署腳本 v1.0.0"
}

# 解析參數
parse_args() {
    TEST=false
    COVERAGE=false
    LINT=false
    FORCE=false
    DRY_RUN=false
    SKILL_NAME=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -t|--test)
                TEST=true
                shift
                ;;
            -c|--coverage)
                COVERAGE=true
                shift
                ;;
            -l|--lint)
                LINT=true
                shift
                ;;
            -f|--force)
                FORCE=true
                shift
                ;;
            -d|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -v|--version)
                show_version
                exit 0
                ;;
            -*)
                log_error "未知選項: $1"
                show_help
                exit 1
                ;;
            *)
                SKILL_NAME="$1"
                shift
                ;;
        esac
    done
    
    if [ -z "$SKILL_NAME" ]; then
        log_error "請指定技能名稱"
        show_help
        exit 1
    fi
}

# 檢查必要命令
check_requirements() {
    log_info "檢查系統要求..."
    
    check_command python3
    check_command pip3
    check_command git
    
    # 檢查 Python 版本
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    log_info "Python 版本: $PYTHON_VERSION"
    
    # 檢查 OpenClaw
    if command -v openclaw &> /dev/null; then
        OPENCLAW_VERSION=$(openclaw --version 2>/dev/null || echo "未知")
        log_info "OpenClaw 版本: $OPENCLAW_VERSION"
    else
        log_warning "OpenClaw 未安裝或不在 PATH 中"
    fi
}

# 檢查技能目錄
check_skill_directory() {
    log_info "檢查技能目錄..."
    
    WORKSPACE_PATH="$HOME/.openclaw/workspace"
    SKILL_PATH="$WORKSPACE_PATH/$SKILL_NAME"
    
    if [ ! -d "$SKILL_PATH" ]; then
        log_error "技能目錄不存在: $SKILL_PATH"
        exit 1
    fi
    
    # 檢查必要檔案
    REQUIRED_FILES=("SKILL.md" "package.json" "main.py")
    for file in "${REQUIRED_FILES[@]}"; do
        if [ ! -f "$SKILL_PATH/$file" ]; then
            log_error "缺少必要檔案: $file"
            exit 1
        fi
    done
    
    log_success "技能目錄檢查通過"
}

# 安裝依賴
install_dependencies() {
    log_info "安裝依賴..."
    
    if [ -f "$SKILL_PATH/requirements.txt" ]; then
        log_info "安裝 Python 依賴..."
        if [ "$DRY_RUN" = true ]; then
            log_info "模擬: pip3 install -r $SKILL_PATH/requirements.txt"
        else
            pip3 install -r "$SKILL_PATH/requirements.txt"
        fi
    else
        log_warning "未找到 requirements.txt，跳過依賴安裝"
    fi
    
    log_success "依賴安裝完成"
}

# 運行測試
run_tests() {
    if [ "$TEST" = false ] && [ "$FORCE" = false ]; then
        log_info "跳過測試（使用 -t 選項運行測試）"
        return 0
    fi
    
    log_info "運行測試..."
    
    if [ ! -d "$SKILL_PATH/tests" ]; then
        log_warning "未找到測試目錄，跳過測試"
        return 0
    fi
    
    if [ "$DRY_RUN" = true ]; then
        log_info "模擬: python3 -m pytest $SKILL_PATH/tests/"
        return 0
    fi
    
    cd "$SKILL_PATH"
    
    if python3 -m pytest tests/ --tb=short; then
        log_success "測試通過"
    else
        log_error "測試失敗"
        if [ "$FORCE" = false ]; then
            exit 1
        fi
    fi
}

# 檢查覆蓋率
run_coverage() {
    if [ "$COVERAGE" = false ] && [ "$FORCE" = false ]; then
        return 0
    fi
    
    log_info "檢查測試覆蓋率..."
    
    if [ "$DRY_RUN" = true ]; then
        log_info "模擬: python3 -m pytest --cov=. $SKILL_PATH/tests/"
        return 0
    fi
    
    cd "$SKILL_PATH"
    
    if python3 -m pytest --cov=. tests/ --cov-report=term; then
        log_success "覆蓋率檢查完成"
    else
        log_warning "覆蓋率檢查有問題"
    fi
}

# 運行程式碼檢查
run_linting() {
    if [ "$LINT" = false ] && [ "$FORCE" = false ]; then
        return 0
    fi
    
    log_info "運行程式碼檢查..."
    
    if [ "$DRY_RUN" = true ]; then
        log_info "模擬: 運行 flake8, black, mypy"
        return 0
    fi
    
    cd "$SKILL_PATH"
    
    # 檢查 flake8
    log_info "運行 flake8..."
    if python3 -m flake8 .; then
        log_success "flake8 檢查通過"
    else
        log_warning "flake8 發現問題"
    fi
    
    # 檢查 black 格式
    log_info "檢查程式碼格式 (black)..."
    if python3 -m black --check .; then
        log_success "程式碼格式正確"
    else
        log_warning "程式碼格式需要調整，運行: black ."
    fi
    
    # 檢查類型提示
    log_info "檢查類型提示 (mypy)..."
    if python3 -m mypy .; then
        log_success "類型提示檢查通過"
    else
        log_warning "類型提示檢查發現問題"
    fi
}

# 打包技能
package_skill() {
    log_info "打包技能..."
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    PACKAGE_NAME="$SKILL_NAME-$TIMESTAMP.tar.gz"
    PACKAGE_PATH="$WORKSPACE_PATH/$PACKAGE_NAME"
    
    if [ "$DRY_RUN" = true ]; then
        log_info "模擬: 打包 $SKILL_PATH 到 $PACKAGE_PATH"
        return 0
    fi
    
    cd "$WORKSPACE_PATH"
    
    if tar -czf "$PACKAGE_NAME" "$SKILL_NAME"; then
        log_success "打包完成: $PACKAGE_NAME"
        echo "檔案大小: $(du -h "$PACKAGE_PATH" | cut -f1)"
    else
        log_error "打包失敗"
        exit 1
    fi
}

# 安裝技能
install_skill() {
    log_info "安裝技能..."
    
    PACKAGE_PATH="$WORKSPACE_PATH/$SKILL_NAME-*.tar.gz"
    LATEST_PACKAGE=$(ls -t $PACKAGE_PATH 2>/dev/null | head -1)
    
    if [ -z "$LATEST_PACKAGE" ]; then
        log_error "未找到技能套件"
        exit 1
    fi
    
    if [ "$DRY_RUN" = true ]; then
        log_info "模擬: 安裝 $LATEST_PACKAGE"
        log_info "模擬: 重啟 OpenClaw"
        return 0
    fi
    
    # 使用技能創建工具安裝
    if python3 "$WORKSPACE_PATH/dev-tools/skill-builder.py" install "$LATEST_PACKAGE"; then
        log_success "技能安裝完成"
    else
        log_error "技能安裝失敗"
        exit 1
    fi
    
    # 重啟 OpenClaw
    log_info "重啟 OpenClaw..."
    if systemctl restart openclaw-gateway 2>/dev/null || \
       openclaw gateway restart 2>/dev/null; then
        log_success "OpenClaw 已重啟"
    else
        log_warning "無法重啟 OpenClaw，請手動重啟"
    fi
}

# 驗證安裝
verify_installation() {
    log_info "驗證安裝..."
    
    if [ "$DRY_RUN" = true ]; then
        log_info "模擬: 驗證技能安裝"
        return 0
    fi
    
    # 檢查技能是否出現在配置中
    CONFIG_FILE="$HOME/.openclaw/openclaw.json"
    if [ -f "$CONFIG_FILE" ]; then
        if grep -q "\"$SKILL_NAME\"" "$CONFIG_FILE"; then
            log_success "技能已添加到配置"
        else
            log_warning "技能未出現在配置中，可能需要手動添加"
        fi
    fi
    
    log_success "部署完成！"
    log_info "下一步:"
    log_info "  1. 測試技能命令: /${SKILL_NAME//-/} help"
    log_info "  2. 查看技能狀態: /${SKILL_NAME//-/} status"
    log_info "  3. 檢查技能配置: /${SKILL_NAME//-/} config"
}

# 清理臨時檔案
cleanup() {
    log_info "清理臨時檔案..."
    
    # 保留最新的 5 個套件
    cd "$WORKSPACE_PATH"
    PACKAGE_FILES=$(ls -t $SKILL_NAME-*.tar.gz 2>/dev/null | wc -l)
    
    if [ "$PACKAGE_FILES" -gt 5 ]; then
        FILES_TO_REMOVE=$((PACKAGE_FILES - 5))
        ls -t $SKILL_NAME-*.tar.gz | tail -$FILES_TO_REMOVE | xargs rm -f
        log_info "已清理 $FILES_TO_REMOVE 個舊套件"
    fi
    
    # 清理 Python 快取
    find "$SKILL_PATH" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find "$SKILL_PATH" -name "*.pyc" -delete 2>/dev/null || true
    
    log_success "清理完成"
}

# 主函數
main() {
    log_info "開始部署技能: $SKILL_NAME"
    echo ""
    
    # 檢查參數
    parse_args "$@"
    
    # 顯示部署選項
    log_info "部署選項:"
    log_info "  • 測試: $([ "$TEST" = true ] && echo "是" || echo "否")"
    log_info "  • 覆蓋率: $([ "$COVERAGE" = true ] && echo "是" || echo "否")"
    log_info "  • 程式碼檢查: $([ "$LINT" = true ] && echo "是" || echo "否")"
    log_info "  • 強制模式: $([ "$FORCE" = true ] && echo "是" || echo "否")"
    log_info "  • 模擬模式: $([ "$DRY_RUN" = true ] && echo "是" || echo "否")"
    echo ""
    
    # 執行部署流程
    check_requirements
    check_skill_directory
    install_dependencies
    run_tests
    run_coverage
    run_linting
    package_skill
    install_skill
    verify_installation
    cleanup
    
    echo ""
    log_success "🎉 技能部署流程完成！"
}

# 執行主函數
main "$@"