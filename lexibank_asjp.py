# coding=utf-8
from __future__ import unicode_literals, print_function
from zipfile import ZipFile

from clldutils import jsonlib
from clldutils.text import split_text
from clldutils.path import read_text, write_text, Path

from pylexibank.dataset import Metadata
from pylexibank.providers import clld


class Dataset(clld.CLLD):
    __cldf_url__ = "http://cdstar.shh.mpg.de/bitstreams/EAEA0-CFA9-F536-516C-0/asjp_dataset.cldf.zip"
    dir = Path(__file__).parent

    def split_forms(self, row, value):
        return [self.clean_form(row, form)
                for form in split_text(value, separators="/,;")]

    def cmd_download(self, **kw):
        clld.CLLD.cmd_download(self, **kw)
        bibtex = read_text(self.raw / 'sources.bib')
        bibtex = bibtex.replace('}).},', '},')
        write_text(self.raw / 'sources.bib', bibtex)

    def cmd_install(self, **kw):
        concept_map = {
            x.english: x.concepticon_id for x in self.conceptlist.concepts.values()}
        fields = self.lexeme_class.fieldnames()

        with self.cldf as ds:
            self.add_sources(ds)

            for row in self.original_cldf['LanguageTable']:
                ds.add_language(
                    ID=row['ID'],
                    Name=row['Name'],
                    Glottocode=row['Glottocode'])
            for row in self.original_cldf['ParameterTable']:
                ds.add_concept(
                    ID=row['ID'],
                    Name=row['Name'],
                    Concepticon_ID=concept_map.get(row['Name'].upper()))
            for row in self.original_cldf['FormTable']:
                row['Value'] = row['Form']
                ds.add_lexemes(**{k: v for k, v in row.items() if k in fields})
