#!/usr/bin/env python3
"""
OpenClaw 技能測試運行器
"""

import os
import sys
import json
import argparse
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Any


class TestRunner:
    """技能測試運行器"""
    
    def __init__(self, workspace_path: str = None):
        self.workspace_path = workspace_path or os.path.join(
            os.path.expanduser('~'), '.openclaw', 'workspace'
        )
        
    def run_tests(self, skill_name: str, test_type: str = 'all') -> Dict[str, Any]:
        """運行技能測試
        
        Args:
            skill_name: 技能名稱
            test_type: 測試類型 (all/unit/integration/e2e)
            
        Returns:
            測試結果
        """
        print(f"運行 {skill_name} 的測試...")
        
        skill_dir = os.path.join(self.workspace_path, skill_name)
        if not os.path.exists(skill_dir):
            return {
                'success': False,
                'error': f'技能目錄不存在: {skill_dir}',
                'tests_run': 0,
                'tests_passed': 0,
                'tests_failed': 0
            }
        
        # 檢查測試目錄
        test_dir = os.path.join(skill_dir, 'tests')
        if not os.path.exists(test_dir):
            print(f"⚠️  測試目錄不存在: {test_dir}")
            return {
                'success': True,
                'warning': '沒有測試檔案',
                'tests_run': 0,
                'tests_passed': 0,
                'tests_failed': 0
            }
        
        try:
            # 運行 pytest
            cmd = [
                sys.executable, '-m', 'pytest',
                '--tb=short',
                '--verbose',
                '--color=yes'
            ]
            
            # 根據測試類型添加參數
            if test_type == 'unit':
                cmd.extend(['-k', 'not integration and not e2e'])
            elif test_type == 'integration':
                cmd.extend(['-k', 'integration'])
            elif test_type == 'e2e':
                cmd.extend(['-k', 'e2e'])
            
            # 添加測試目錄
            cmd.append(test_dir)
            
            print(f"執行命令: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=skill_dir,
                timeout=300  # 5分鐘超時
            )
            
            # 解析測試結果
            test_results = self._parse_pytest_output(result.stdout, result.stderr)
            
            if result.returncode == 0:
                print(f"✅ 測試通過: {test_results['tests_passed']}/{test_results['tests_run']}")
            else:
                print(f"❌ 測試失敗: {test_results['tests_failed']}/{test_results['tests_run']}")
                if result.stderr:
                    print(f"錯誤輸出:\n{result.stderr}")
            
            return {
                'success': result.returncode == 0,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                **test_results
            }
            
        except subprocess.TimeoutExpired:
            error_msg = '測試執行超時 (5分鐘)'
            print(f"❌ {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'tests_run': 0,
                'tests_passed': 0,
                'tests_failed': 0
            }
        except Exception as e:
            error_msg = f'運行測試時出錯: {e}'
            print(f"❌ {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'tests_run': 0,
                'tests_passed': 0,
                'tests_failed': 0
            }
    
    def run_coverage(self, skill_name: str) -> Dict[str, Any]:
        """運行測試覆蓋率檢查
        
        Args:
            skill_name: 技能名稱
            
        Returns:
            覆蓋率結果
        """
        print(f"檢查 {skill_name} 的測試覆蓋率...")
        
        skill_dir = os.path.join(self.workspace_path, skill_name)
        if not os.path.exists(skill_dir):
            return {
                'success': False,
                'error': f'技能目錄不存在: {skill_dir}',
                'coverage': 0.0
            }
        
        try:
            # 運行 pytest 帶覆蓋率檢查
            cmd = [
                sys.executable, '-m', 'pytest',
                '--cov=.',
                '--cov-report=term',
                '--cov-report=html',
                '--cov-report=xml',
                '--tb=short'
            ]
            
            # 添加測試目錄
            test_dir = os.path.join(skill_dir, 'tests')
            cmd.append(test_dir)
            
            print(f"執行命令: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=skill_dir,
                timeout=300
            )
            
            # 解析覆蓋率結果
            coverage = self._parse_coverage_output(result.stdout)
            
            if result.returncode == 0:
                print(f"✅ 覆蓋率檢查完成: {coverage:.1f}%")
            else:
                print(f"⚠️  覆蓋率檢查有問題")
            
            # 生成覆蓋率報告
            coverage_report = self._generate_coverage_report(skill_dir, coverage)
            
            return {
                'success': result.returncode == 0,
                'coverage': coverage,
                'report': coverage_report,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
        except Exception as e:
            error_msg = f'運行覆蓋率檢查時出錯: {e}'
            print(f"❌ {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'coverage': 0.0
            }
    
    def run_linting(self, skill_name: str) -> Dict[str, Any]:
        """運行程式碼檢查
        
        Args:
            skill_name: 技能名稱
            
        Returns:
            檢查結果
        """
        print(f"檢查 {skill_name} 的程式碼品質...")
        
        skill_dir = os.path.join(self.workspace_path, skill_name)
        if not os.path.exists(skill_dir):
            return {
                'success': False,
                'error': f'技能目錄不存在: {skill_dir}',
                'issues': 0
            }
        
        results = {}
        
        try:
            # 運行 flake8
            flake8_result = self._run_flake8(skill_dir)
            results['flake8'] = flake8_result
            
            # 運行 black 檢查
            black_result = self._run_black_check(skill_dir)
            results['black'] = black_result
            
            # 運行 mypy
            mypy_result = self._run_mypy(skill_dir)
            results['mypy'] = mypy_result
            
            # 計算總問題數
            total_issues = (
                flake8_result.get('issues', 0) +
                black_result.get('issues', 0) +
                mypy_result.get('issues', 0)
            )
            
            if total_issues == 0:
                print("✅ 程式碼檢查通過")
            else:
                print(f"⚠️  發現 {total_issues} 個問題")
            
            return {
                'success': total_issues == 0,
                'total_issues': total_issues,
                'results': results
            }
            
        except Exception as e:
            error_msg = f'運行程式碼檢查時出錯: {e}'
            print(f"❌ {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'issues': 0
            }
    
    def run_all_checks(self, skill_name: str) -> Dict[str, Any]:
        """運行所有檢查（測試、覆蓋率、程式碼檢查）
        
        Args:
            skill_name: 技能名稱
            
        Returns:
            所有檢查結果
        """
        print(f"對 {skill_name} 運行全面檢查...")
        print("=" * 60)
        
        all_results = {}
        
        # 1. 運行測試
        print("\n1. 運行測試...")
        test_results = self.run_tests(skill_name)
        all_results['tests'] = test_results
        
        # 2. 運行覆蓋率檢查
        print("\n2. 檢查測試覆蓋率...")
        coverage_results = self.run_coverage(skill_name)
        all_results['coverage'] = coverage_results
        
        # 3. 運行程式碼檢查
        print("\n3. 檢查程式碼品質...")
        lint_results = self.run_linting(skill_name)
        all_results['linting'] = lint_results
        
        # 總結結果
        print("\n" + "=" * 60)
        print("檢查總結:")
        
        test_success = test_results.get('success', False)
        coverage_ok = coverage_results.get('coverage', 0.0) >= 70.0  # 70% 覆蓋率要求
        lint_success = lint_results.get('success', False)
        
        print(f"• 測試: {'✅ 通過' if test_success else '❌ 失敗'}")
        print(f"• 覆蓋率: {coverage_results.get('coverage', 0.0):.1f}% {'✅' if coverage_ok else '❌'}")
        print(f"• 程式碼品質: {'✅ 通過' if lint_success else '❌ 失敗'}")
        
        overall_success = test_success and coverage_ok and lint_success
        
        if overall_success:
            print("\n🎉 所有檢查通過！")
        else:
            print("\n⚠️  部分檢查未通過，請查看詳細報告")
        
        return {
            'success': overall_success,
            'test_passed': test_success,
            'coverage_ok': coverage_ok,
            'lint_passed': lint_success,
            'results': all_results
        }
    
    def _parse_pytest_output(self, stdout: str, stderr: str) -> Dict[str, Any]:
        """解析 pytest 輸出"""
        import re
        
        tests_run = 0
        tests_passed = 0
        tests_failed = 0
        
        # 嘗試從輸出中解析測試結果
        lines = stdout.split('\n')
        
        for line in lines:
            if 'passed' in line and 'failed' in line:
                # 格式: "X passed, Y failed in Z seconds"
                match = re.search(r'(\d+) passed.*?(\d+) failed', line)
                if match:
                    tests_passed = int(match.group(1))
                    tests_failed = int(match.group(2))
                    tests_run = tests_passed + tests_failed
                    break
        
        return {
            'tests_run': tests_run,
            'tests_passed': tests_passed,
            'tests_failed': tests_failed
        }
    
    def _parse_coverage_output(self, stdout: str) -> float:
        """解析覆蓋率輸出"""
        import re
        
        coverage = 0.0
        
        # 尋找覆蓋率百分比
        lines = stdout.split('\n')
        for line in lines:
            if 'TOTAL' in line:
                # 格式: "TOTAL 123 45 63%"
                match = re.search(r'(\d+)%', line)
                if match:
                    coverage = float(match.group(1))
                    break
        
        return coverage
    
    def _generate_coverage_report(self, skill_dir: str, coverage: float) -> Dict[str, Any]:
        """生成覆蓋率報告"""
        report_dir = os.path.join(skill_dir, 'coverage_report')
        html_report = os.path.join(report_dir, 'index.html')
        
        report = {
            'coverage_percentage': coverage,
            'html_report': html_report if os.path.exists(html_report) else None,
            'xml_report': os.path.join(skill_dir, 'coverage.xml') if os.path.exists(os.path.join(skill_dir, 'coverage.xml')) else None
        }
        
        return report
    
    def _run_flake8(self, skill_dir: str) -> Dict[str, Any]:
        """運行 flake8"""
        try:
            cmd = [sys.executable, '-m', 'flake8', '.']
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=skill_dir,
                timeout=60
            )
            
            issues = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
            
            return {
                'success': result.returncode == 0,
                'issues': issues,
                'output': result.stdout,
                'returncode': result.returncode
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'issues': 0
            }
    
    def _run_black_check(self, skill_dir: str) -> Dict[str, Any]:
        """運行 black 檢查"""
        try:
            cmd = [sys.executable, '-m', 'black', '--check', '.']
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=skill_dir,
                timeout=60
            )
            
            # black 返回 0 表示格式正確，1 表示需要重新格式化
            issues = 0 if result.returncode == 0 else 1
            
            return {
                'success': result.returncode == 0,
                'issues': issues,
                'output': result.stdout,
                'returncode': result.returncode
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'issues': 0
            }
    
    def _run_mypy(self, skill_dir: str) -> Dict[str, Any]:
        """運行 mypy"""
        try:
            cmd = [sys.executable, '-m', 'mypy', '.']
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=skill_dir,
                timeout=120
            )
            
            # 解析 mypy 輸出中的錯誤數量
            issues = 0
            if result.stdout:
                # 計算錯誤行數
                lines = result.stdout.strip().split('\n')
                issues = sum(1 for line in lines if 'error:' in line)
            
            return {
                'success': result.returncode == 0,
                'issues': issues,
                'output': result.stdout,
                'returncode': result.returncode
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'issues': 0
            }


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='OpenClaw 技能測試運行器')
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # test 命令
    test_parser = subparsers.add_parser('test', help='運行測試')
    test_parser.add_argument('skill', help='技能名稱')
    test_parser.add_argument('--type', choices=['all', 'unit', 'integration', 'e2e'], 
                           default='all', help='測試類型')
    
    # coverage 命令
    coverage_parser = subparsers.add_parser('coverage', help='檢查測試覆蓋率')
    coverage_parser.add_argument('skill', help='技能名稱')
    
    # lint 命令
    lint_parser = subparsers.add_parser('lint', help='運行程式碼檢查')
    lint_parser.add_argument('skill', help='技能名稱')
    
    # all 命令
    all_parser = subparsers.add_parser('all', help='運行所有檢查')
    all_parser.add_argument('skill', help='技能名稱')
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    if args.command == 'test':
        results = runner.run_tests(args.skill, args.type)
        print(json.dumps(results, indent=2, ensure_ascii=False))
        
    elif args.command == 'coverage':
        results = runner.run_coverage(args.skill)
        print(json.dumps(results, indent=2, ensure_ascii=False))
        
    elif args.command == 'lint':
        results = runner.run_linting(args.skill)
        print(json.dumps(results, indent=2, ensure_ascii=False))
        
    elif args.command == 'all':
        results = runner.run_all_checks(args.skill)
        print(json.dumps(results, indent=2, ensure_ascii=False))
        
    else:
        parser.print_help()


if __name__ == '__main__':
    main()