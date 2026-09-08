from setuptools import setup, find_packages

setup(
    name='boohee-sdk',
    version='0.1.0',
    description='薄荷科学.ai Python SDK',
    author='Boohee',
    author_email='dev@boohee.com',
    packages=find_packages(),
    install_requires=[
        'pycryptodome>=3.15.0',
        'requests>=2.28.0',
    ],
    python_requires='>=3.7',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
)
