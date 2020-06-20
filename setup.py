from setuptools import setup

setup(
    name='pynixify',
    version='0.1dev',
    packages=['pynixify',],
    package_data={'pynixify': ['data/*']},
    license='GPLv3+',
    description="Nix expression generator for Python packages",
    # long_description=open('README.txt').read(),
    tests_require=['pytest', 'pytest-asyncio', 'mypy'],
    install_requires=['packaging', 'setuptools', 'aiohttp<4.0.0', 'aiofiles', 'docopt', 'Mako'],
    entry_points={
        'console_scripts': [
            'pynixify=pynixify.command:main'
        ]
    },
)
