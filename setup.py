from setuptools import setup

setup(
    name='pypi2nixpkgs',
    version='0.1dev',
    packages=['pypi2nixpkgs',],
    license='GPLv3+',
    # long_description=open('README.txt').read(),
    tests_require=['pytest', 'pytest-asyncio'],
    install_requires=['aiohttp<4.0.0', 'aiofiles', 'click'],
    entry_points={
        'console_scripts': [
            'pypi2nixpkgs=pypi2nixpkgs.command:main'
        ]
    },
)
