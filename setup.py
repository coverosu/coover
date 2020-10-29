import setuptools
import config

with open("README.md", "r") as fh:
	long_description = fh.read()

setuptools.setup(
	name="coover",
	version="0.0.7",
	author="coverosu",
	author_email=config.email,
	description="Using this package for code that I tend to rewrite a lot",
	long_description=long_description,
	long_description_content_type="text/markdown",
	url="https://github.com/coverosu/coover",
	packages=setuptools.find_packages(),
	classifiers=[
		"Programming Language :: Python :: 3",
		"License :: OSI Approved :: MIT License",
		"Operating System :: OS Independent",
	],
	python_requires='>=3.6',
)