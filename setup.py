from setuptools import setup, find_packages
from pathlib import Path

# Read the contents of the README file for long_description
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name='julien-python-toolkit',
    version='0.2.4',
    packages=find_packages(),
    license='Custom Non-Commercial License',  # Reference your custom license
    install_requires=[
        "certifi==2024.8.30",
        "google-api-core==2.19.1",
        "google-api-python-client==2.139.0",
        "google-auth==2.32.0",
        "google-auth-httplib2==0.2.0",
        "google-auth-oauthlib==1.2.1",
        "googleapis-common-protos==1.63.2",
    ],
    description='Important code that I reuse through multiple projects. Please see license for allowed use.',
    long_description=long_description,  # Include long description here
    long_description_content_type='text/markdown',  # Set to 'text/markdown' for Markdown files
    author='Julien Python',
    author_email='python.julien@hotmail.com',
    url='https://github.com/JulienPython/JulienPythonToolkit-V001',
    classifiers=[
        'Programming Language :: Python :: 3',
    ],
)