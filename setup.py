"""
Setup configuration for Jingle.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / 'README.md'
long_description = readme_file.read_text(encoding='utf-8') if readme_file.exists() else ''

setup(
    name='jingle',
    version='0.1.0',
    author='Colin Wang',
    description='Lightweight timed music playback system for resource-constrained devices',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/colinwang1703/jingle',
    packages=find_packages(),
    python_requires='>=3.7',
    install_requires=[
        'pygame>=2.1.0',
        'PyYAML>=6.0',
        'schedule>=1.1.0',
    ],
    entry_points={
        'console_scripts': [
            'jingle=jingle.main:main',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Multimedia :: Sound/Audio :: Players',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    keywords='music player scheduler raspberry-pi embedded',
)
