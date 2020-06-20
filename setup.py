from setuptools import setup

setup(
    name='pynixify',
    version='0.1dev',
    packages=['pynixify',],
    package_data={'pynixify': ['data/*']},
    license='GPLv3+',
    # long_description=open('README.txt').read(),
    tests_require=['pytest', 'pytest-asyncio'],
    install_requires=['aiohttp<4.0.0', 'aiofiles', 'docopt'],
    entry_points={
        'console_scripts': [
            'pynixify=pynixify.command:main'
        ]
    },
)
