#!/usr/bin/env python3
"""
OpenClaw 技能創建工具
"""

import os
import sys
import json
import shutil
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


class SkillBuilder:
    """技能創建和打包工具"""
    
    def __init__(self, workspace_path: str = None):
        self.workspace_path = workspace_path or os.path.join(
            os.path.expanduser('~'), '.openclaw', 'workspace'
        )
        self.template_path = os.path.join(self.workspace_path, 'skill-template')
        
        # 確保目錄存在
        os.makedirs(self.workspace_path, exist_ok=True)
        os.makedirs(self.template_path, exist_ok=True)
    
    def create(self, skill_name: str, author: str = None, description: str = None):
        """創建新技能
        
        Args:
            skill_name: 技能名稱（小寫，使用連字符）
            author: 作者名稱
            description: 技能描述
        """
        print(f"創建新技能: {skill_name}")
        
        # 驗證技能名稱
        if not self._validate_skill_name(skill_name):
            print("錯誤: 技能名稱只能包含小寫字母、數字和連字符")
            return False
        
        # 設置預設值
        if not author:
            author = input("作者名稱: ").strip() or "OpenClaw User"
        
        if not description:
            description = input("技能描述: ").strip() or f"{skill_name} skill for OpenClaw"
        
        # 創建技能目錄
        skill_dir = os.path.join(self.workspace_path, skill_name)
        if os.path.exists(skill_dir):
            print(f"錯誤: 技能目錄已存在: {skill_dir}")
            return False
        
        os.makedirs(skill_dir)
        
        try:
            # 複製模板檔案
            self._copy_template_files(skill_dir, skill_name, author, description)
            
            # 創建子目錄
            self._create_subdirectories(skill_dir)
            
            # 初始化 Git 倉庫（可選）
            if self._confirm("初始化 Git 倉庫？"):
                self._init_git_repo(skill_dir)
            
            print(f"\n✅ 技能創建完成！")
            print(f"📁 目錄: {skill_dir}")
            print(f"🚀 下一步:")
            print(f"  1. cd {skill_dir}")
            print(f"  2. 編輯 main.py 實現你的功能")
            print(f"  3. 運行測試: python -m pytest tests/")
            print(f"  4. 打包: python dev-tools/skill-builder.py package {skill_name}")
            
            return True
            
        except Exception as e:
            print(f"創建技能時出錯: {e}")
            # 清理失敗的目錄
            if os.path.exists(skill_dir):
                shutil.rmtree(skill_dir)
            return False
    
    def package(self, skill_name: str, output_dir: str = None):
        """打包技能
        
        Args:
            skill_name: 技能名稱
            output_dir: 輸出目錄（預設為 workspace）
        """
        print(f"打包技能: {skill_name}")
        
        skill_dir = os.path.join(self.workspace_path, skill_name)
        if not os.path.exists(skill_dir):
            print(f"錯誤: 技能目錄不存在: {skill_dir}")
            return False
        
        # 檢查必要檔案
        required_files = ['SKILL.md', 'package.json', 'main.py']
        for file in required_files:
            if not os.path.exists(os.path.join(skill_dir, file)):
                print(f"錯誤: 缺少必要檔案: {file}")
                return False
        
        # 設置輸出目錄
        if not output_dir:
            output_dir = self.workspace_path
        
        # 創建壓縮檔
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        package_name = f"{skill_name}-{timestamp}.tar.gz"
        package_path = os.path.join(output_dir, package_name)
        
        try:
            # 創建壓縮檔
            import tarfile
            
            with tarfile.open(package_path, 'w:gz') as tar:
                tar.add(skill_dir, arcname=skill_name)
            
            print(f"\n✅ 打包完成！")
            print(f"📦 套件檔案: {package_path}")
            print(f"📏 檔案大小: {os.path.getsize(package_path) / 1024:.1f} KB")
            
            return package_path
            
        except Exception as e:
            print(f"打包時出錯: {e}")
            return None
    
    def install(self, package_path: str, target_dir: str = None):
        """安裝技能套件
        
        Args:
            package_path: 套件檔案路徑
            target_dir: 安裝目錄（預設為系統技能目錄）
        """
        print(f"安裝技能套件: {package_path}")
        
        if not os.path.exists(package_path):
            print(f"錯誤: 套件檔案不存在: {package_path}")
            return False
        
        # 設置目標目錄
        if not target_dir:
            # 嘗試找到系統技能目錄
            possible_paths = [
                '/usr/lib/node_modules/openclaw/skills',
                '/usr/local/lib/node_modules/openclaw/skills',
                os.path.join(os.path.expanduser('~'), '.openclaw', 'skills')
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    target_dir = path
                    break
            
            if not target_dir:
                print("錯誤: 找不到技能安裝目錄")
                return False
        
        try:
            # 解壓縮套件
            import tarfile
            
            with tarfile.open(package_path, 'r:gz') as tar:
                # 獲取技能名稱
                members = tar.getmembers()
                if not members:
                    print("錯誤: 套件為空")
                    return False
                
                skill_name = os.path.basename(members[0].name)
                install_path = os.path.join(target_dir, skill_name)
                
                # 檢查是否已存在
                if os.path.exists(install_path):
                    if not self._confirm(f"技能 {skill_name} 已存在，是否覆蓋？"):
                        print("安裝取消")
                        return False
                    shutil.rmtree(install_path)
                
                # 解壓縮
                tar.extractall(target_dir)
            
            print(f"\n✅ 安裝完成！")
            print(f"📁 安裝位置: {install_path}")
            print(f"🚀 下一步:")
            print(f"  1. 重啟 OpenClaw: openclaw gateway restart")
            print(f"  2. 測試技能: /{skill_name} help")
            
            return True
            
        except Exception as e:
            print(f"安裝時出錯: {e}")
            return False
    
    def list(self):
        """列出所有技能"""
        skills_dir = os.path.join(self.workspace_path)
        
        print("📚 技能列表:")
        print("-" * 50)
        
        for item in os.listdir(skills_dir):
            item_path = os.path.join(skills_dir, item)
            if os.path.isdir(item_path):
                # 檢查是否為技能目錄
                skill_files = ['SKILL.md', 'package.json', 'main.py']
                is_skill = all(
                    os.path.exists(os.path.join(item_path, f))
                    for f in skill_files[:2]  # 至少需要前兩個檔案
                )
                
                if is_skill:
                    # 讀取技能信息
                    info = self._get_skill_info(item_path)
                    print(f"• {item}")
                    print(f"  📝 {info.get('description', '無描述')}")
                    print(f"  👤 {info.get('author', '未知作者')}")
                    print(f"  🏷️  {info.get('version', '未知版本')}")
                    print()
    
    def _validate_skill_name(self, name: str) -> bool:
        """驗證技能名稱"""
        import re
        pattern = r'^[a-z0-9]+(?:-[a-z0-9]+)*$'
        return bool(re.match(pattern, name))
    
    def _copy_template_files(self, skill_dir: str, skill_name: str, author: str, description: str):
        """複製模板檔案並替換變數"""
        
        # 變數映射
        variables = {
            '{{skill_name}}': skill_name,
            '{{skill_name_camel}}': self._to_camel_case(skill_name),
            '{{author}}': author,
            '{{description}}': description,
            '{{category}}': 'utility',  # 預設分類
            '{{command_prefix}}': skill_name.replace('-', ''),
            '{{skill_description}}': description,
            '{{repository_url}}': f'https://github.com/yourusername/{skill_name}',
            '{{issues_url}}': f'https://github.com/yourusername/{skill_name}/issues',
            '{{forum_url}}': 'https://discord.com/invite/clawd',
            '{{email}}': 'your-email@example.com',
            '{{homepage_url}}': f'https://clawhub.com/skills/{skill_name}',
            '{{docs_url}}': f'https://docs.openclaw.ai/skills/{skill_name}'
        }
        
        # 複製並處理每個模板檔案
        template_files = [
            ('SKILL.md', 'SKILL.md'),
            ('package.json', 'package.json'),
            ('main.py', 'main.py')
        ]
        
        for template_file, target_file in template_files:
            template_path = os.path.join(self.template_path, template_file)
            target_path = os.path.join(skill_dir, target_file)
            
            if os.path.exists(template_path):
                with open(template_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 替換變數
                for var, value in variables.items():
                    content = content.replace(var, value)
                
                with open(target_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            else:
                # 如果模板不存在，創建基本檔案
                if target_file == 'SKILL.md':
                    self._create_basic_skill_md(skill_dir, skill_name, author, description)
                elif target_file == 'package.json':
                    self._create_basic_package_json(skill_dir, skill_name, author, description)
                elif target_file == 'main.py':
                    self._create_basic_main_py(skill_dir, skill_name)
    
    def _create_subdirectories(self, skill_dir: str):
        """創建子目錄"""
        subdirs = [
            'tests',
            'assets',
            'assets/icons',
            'assets/templates',
            'docs'
        ]
        
        for subdir in subdirs:
            os.makedirs(os.path.join(skill_dir, subdir), exist_ok=True)
        
        # 創建基本測試檔案
        test_file = os.path.join(skill_dir, 'tests', 'test_basic.py')
        if not os.path.exists(test_file):
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write('''#!/usr/bin/env python3
"""
基本測試
"""

def test_skill_structure():
    """測試技能結構"""
    assert True

def test_import():
    """測試導入"""
    try:
        import main
        assert True
    except ImportError:
        assert False
''')
    
    def _init_git_repo(self, skill_dir: str):
        """初始化 Git 倉庫"""
        try:
            subprocess.run(['git', 'init'], cwd=skill_dir, check=True)
            subprocess.run(['git', 'add', '.'], cwd=skill_dir, check=True)
            subprocess.run(
                ['git', 'commit', '-m', 'Initial commit'],
                cwd=skill_dir, check=True
            )
            print("✅ Git 倉庫初始化完成")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Git 初始化失敗: {e}")
        except FileNotFoundError:
            print("⚠️  Git 未安裝，跳過初始化")
    
    def _confirm(self, message: str) -> bool:
        """確認提示"""
        response = input(f"{message} (y/N): ").strip().lower()
        return response in ['y', 'yes']
    
    def _to_camel_case(self, text: str) -> str:
        """轉換為駝峰命名法"""
        parts = text.split('-')
        return ''.join(part.capitalize() for part in parts)
    
    def _get_skill_info(self, skill_dir: str) -> Dict[str, Any]:
        """獲取技能信息"""
        info = {}
        
        # 從 package.json 讀取
        package_path = os.path.join(skill_dir, 'package.json')
        if os.path.exists(package_path):
            try:
                with open(package_path, 'r', encoding='utf-8') as f:
                    package_data = json.load(f)
                    info.update({
                        'name': package_data.get('name'),
                        'version': package_data.get('version'),
                        'description': package_data.get('description'),
                        'author': package_data.get('author')
                    })
            except:
                pass
        
        return info
    
    def _create_basic_skill_md(self, skill_dir: str, skill_name: str, author: str, description: str):
        """創建基本的 SKILL.md"""
        content = f"""# {skill_name}

## 描述
{description}

## 作者
{author}

## 安裝
1. 複製此目錄到 OpenClaw 技能目錄
2. 重啟 OpenClaw: `openclaw gateway restart`

## 使用
/{skill_name.replace('-', '')} - 使用此技能

## 開發
編輯 `main.py` 實現你的功能
"""
        
        with open(os.path.join(skill_dir, 'SKILL.md'), 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _create_basic_package_json(self, skill_dir: str, skill_name: str, author: str, description: str):
        """創建基本的 package.json"""
        package_data = {
            "name": skill_name,
            "version": "1.0.0",
            "description": description,
            "main": "main.py",
            "author": author,
            "license": "MIT",
            "openclaw": {
                "skill": True,
                "commands": [
                    {
                        "command": f"/{skill_name.replace('-', '')}",
                        "description": description,
                        "handler": "main.handle_command"
                    }
                ]
            }
        }
        
        with open(os.path.join(skill_dir, 'package.json'), 'w', encoding='utf-8') as f:
            json.dump(package_data, f, indent=2)
    
    def _create_basic_main_py(self, skill_dir: str, skill_name: str):
        """創建基本的 main.py"""
        content = f'''#!/usr/bin/env python3
"""
{skill_name} - OpenClaw 技能
"""

def handle_command(command, args, context):
    """處理命令"""
    return {{
        'success': True,
        'message': f'{skill_name} 技能已啟用，命令: {{command}}',
        'format': 'text'
    }}


if __name__ == '__main__':
    # 測試程式
    result = handle_command('test', [], {{}})
    print(result)
'''
        
        with open(os.path.join(skill_dir, 'main.py'), 'w', encoding='utf-8') as f:
            f.write(content)


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='OpenClaw 技能創建工具')
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # create 命令
    create_parser = subparsers.add_parser('create', help='創建新技能')
    create_parser.add_argument('name', help='技能名稱（小寫，使用連字符）')
    create_parser.add_argument('--author', help='作者名稱')
    create_parser.add_argument('--description', help='技能描述')
    
    # package 命令
    package_parser = subparsers.add_parser('package', help='打包技能')
    package_parser.add_argument('name', help='技能名稱')
    package_parser.add_argument('--output', help='輸出目錄')
    
    # install 命令
    install_parser = subparsers.add_parser('install', help='安裝技能套件')
    install_parser.add_argument('package', help='套件檔案路徑')
    install_parser.add_argument('--target', help='安裝目錄')
    
    # list 命令
    subparsers.add_parser('list', help='列出所有技能')
    
    args = parser.parse_args()
    
    builder = SkillBuilder()
    
    if args.command == 'create':
        builder.create(args.name, args.author, args.description)
    elif args.command == 'package':
        builder.package(args.name, args.output)
    elif args.command == 'install':
        builder.install(args.package, args.target)
    elif args.command == 'list':
        builder.list()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()