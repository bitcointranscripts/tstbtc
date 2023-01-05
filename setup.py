from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read()

setup(
    name='yt2btc',
    version='0.1.0',
    author='Peter Tyonum',
    author_email='withtvpeter@gmail.com',
    license='MIT',
    description='transcribes youtube videos to bitcointranscript',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/tvpeter/yt2btc',
    py_modules=['yttbtc'],
    packages=find_packages(),
    install_requires=[requirements],
    python_requires='>=3.9',
    classifiers=[
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    entry_points='''
        [console_scripts]
        yt2btc=yttbtc:add
    '''
)
