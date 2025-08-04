# Releasing ASJP

Replace files
- raw/sources.csv with CSV export of sources sheet in excel file
- raw/transcribers.csv from CSV export of corresponding sheet in excel file
- raw/lists.txt

Adapt citation in metadata.json

Recreate the cldf:
```shell
cldfbench lexibank.makecldf --glottolog-version v5.2 lexibank_asjp.py
```

Validate:
```shell
cldf validate cldf
pytest
rm asjp.sqlite
cldf createdb cldf asjp.sqlite
```

Make sure the clld app db can be recreated
cd ../asjp
clld initdb development.ini --cldf ../asjp/cldf/cldf-metadata.json
