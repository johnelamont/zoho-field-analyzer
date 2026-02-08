"""
Setup configuration for Zoho Field Analyzer
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / 'README.md'
long_description = readme_file.read_text(encoding='utf-8') if readme_file.exists() else ''

setup(
    name='zoho-field-analyzer',
    version='0.1.0',
    description='Extract and analyze Zoho CRM metadata to understand field transformations',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Your Name',
    author_email='your.email@example.com',
    url='https://github.com/yourusername/zoho-field-analyzer',
    packages=find_packages(),
    python_requires='>=3.8',
    install_requires=[
        'requests>=2.31.0',
        'pyyaml>=6.0',
        'python-dotenv>=1.0.0',
        'pathlib>=1.0.1',
        'jinja2>=3.1.2',
        'networkx>=3.1',
        'matplotlib>=3.7.1',
        'pandas>=2.0.0',
    ],
    extras_require={
        'dev': [
            'pytest>=7.0',
            'pytest-cov>=4.0',
            'black>=23.0',
            'flake8>=6.0',
            'mypy>=1.0',
        ]
    },
    entry_points={
        'console_scripts': [
            'zoho-extract=src.extractors.main:main',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
)
