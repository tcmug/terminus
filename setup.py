from setuptools import setup, find_packages

setup(
    name='terminus',
    version='0.1',
    scripts=['terminus'],
    description='Experimental C/C++ source package manager',
    #long_description=long_description,
    author='tcmug',
    author_email='teemu.merikoski@gmail.com',
    license='MIT',
    packages=find_packages(exclude=['definitions']),
    install_requires=['ruamel.yaml==0.15.32'],
    python_requires='>=3',
    url="https://github.com/tcmug/terminus"
)
