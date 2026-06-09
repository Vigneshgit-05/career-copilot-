#!/usr/bin/env python3
from setuptools import setup, find_packages
import os
import sys

def read_readme():
    """Read README file"""
    if os.path.exists('README.md'):
        with open('README.md', 'r', encoding='utf-8') as f:
            return f.read()
    return "CareerCopilot AI - Personal Job Application System"

def get_requirements():
    """Get requirements from requirements.txt"""
    if os.path.exists('requirements.txt'):
        with open('requirements.txt', 'r') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return []

setup(
    name="careercopilot-ai",
    version="1.0.0",
    author="CareerCopilot Team",
    author_email="support@careercopilot.com",
    description="Personal AI Agent for Automated Job Applications",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/careercopilot",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Job Seekers",
        "Topic :: Office/Business :: Scheduling",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    install_requires=get_requirements(),
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-asyncio>=0.21.0',
            'pytest-cov>=4.0.0',
            'black>=23.0.0',
            'flake8>=6.0.0',
            'mypy>=1.0.0',
        ],
        'test': [
            'pytest>=7.0.0',
            'pytest-asyncio>=0.21.0',
            'pytest-mock>=3.10.0',
        ]
    },
    entry_points={
        'console_scripts': [
            'careercopilot=run:main',
            'careercopilot-dashboard=src.dashboard.streamlit_app:main',
        ],
    },
    include_package_data=True,
    zip_safe=False,
)