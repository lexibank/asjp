import pathlib

from pylexibank.providers import clld


class Dataset(clld.CLLD):
    __cldf_url__ = "http://cdstar.shh.mpg.de/bitstreams/EAEA0-CFA9-F536-516C-0/asjp_dataset.cldf.zip"
    dir = pathlib.Path(__file__).parent
    id = 'asjp'

    def cmd_download(self, args):
        clld.CLLD.cmd_download(self, args)
        bibtex = self.raw_dir.read('sources.bib')
        bibtex = bibtex.replace('}).},', '},')
        (self.raw_dir / 'sources.bib').write_text(bibtex, encoding='utf8')

    def cmd_makecldf(self, args):
        concept_map = {
            x.english: x.concepticon_id for x in self.conceptlists[0].concepts.values()}
        fields = self.lexeme_class.fieldnames()

        self.add_sources(args.writer)

        for row in self.original_cldf['LanguageTable']:
            args.writer.add_language(
                ID=row['ID'],
                Name=row['Name'],
                Glottocode=row['Glottocode'])
        for row in self.original_cldf['ParameterTable']:
            args.writer.add_concept(
                ID=row['ID'],
                Name=row['Name'],
                Concepticon_ID=concept_map.get(row['Name'].upper()))
        for row in self.original_cldf['FormTable']:
            row['Value'] = row['Form']
            args.writer.add_form_with_segments(**{k: v for k, v in row.items() if k in fields})
