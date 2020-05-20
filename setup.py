from setuptools import setup
import json


with open('metadata.json', encoding='utf-8') as fp:
    metadata = json.load(fp)


setup(
    name='lexibank_asjp',
    description=metadata['title'],
    license=metadata.get('license', ''),
    url=metadata.get('url', ''),
    py_modules=['lexibank_asjp'],
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'lexibank.dataset': [
            'asjp=lexibank_asjp:Dataset',
        ]
    },
    install_requires=[
        'pyasjp>=1.1',
        'pylexibank>=2.1',
    ]
)
