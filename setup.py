from setuptools import setup, find_packages

setup(
    name='terminus',
    version='0.1',
    scripts=['terminus'],
    description='Experimental C/C++ local package manager',
    #long_description=long_description,
    author='tcmug',
    author_email='teemu.merikoski@gmail.com',
    license='MIT',
    packages=find_packages(exclude=['contrib', 'docs', 'tests*']),
    install_requires=['PyYAML==3.12'],
    python_requires='>=3'
)
