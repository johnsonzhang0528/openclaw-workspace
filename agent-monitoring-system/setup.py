"""
Agent Monitoring System 安裝設定
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="agent-monitoring-system",
    version="1.0.0",
    author="OpenClaw Team",
    author_email="team@openclaw.ai",
    description="Telegram 介面的即時可視化監控系統 for OpenClaw",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/openclaw/agent-monitoring-system",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Monitoring",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "python-dotenv>=1.0.0",
        "requests>=2.28.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "agent-monitor=agent_monitor:main",
            "test-monitoring=test_monitoring:run_all_tests",
        ],
    },
    package_data={
        "agent_monitoring_system": ["*.env", "*.md"],
    },
    include_package_data=True,
    zip_safe=False,
)