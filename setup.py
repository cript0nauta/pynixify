# pynixify - Nix expression generator for Python packages
# Copyright (C) 2020 Matías Lang

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from setuptools import setup

setup(
    name='pynixify',
    version='0.1',
    packages=['pynixify',],
    package_data={'pynixify': ['data/*']},
    license='GPLv3+',
    description="Nix expression generator for Python packages",
    url="https://github.com/cript0nauta/pynixify",
    # long_description=open('README.txt').read(),
    tests_require=['pytest', 'pytest-asyncio', 'mypy'],
    install_requires=['packaging', 'setuptools', 'aiohttp<4.0.0', 'aiofiles', 'Mako'],
    entry_points={
        'console_scripts': [
            'pynixify=pynixify.command:main'
        ]
    },
)
