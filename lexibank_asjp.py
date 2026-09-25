import re
import shutil
import string
import pathlib
import mimetypes
import dataclasses
import unicodedata
from typing import Optional

from pyasjp.api import ASJP
from pycldf.sources import Source
from clldutils.path import md5

import pylexibank
from pyasjp.models import MEANINGS_ALL


def slug(s):
    """Condensed version of s, containing only lowercase alphanumeric characters."""
    res = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    for c in string.punctuation:
        if c != "_":
            res = res.replace(c, "")
    res = re.sub(r"\s+", "", res)
    res = res.encode("ascii", "ignore").decode("ascii")
    assert re.match(r"[ A-Za-z0-9_]*$", res)
    return res


@dataclasses.dataclass
class Doculect(pylexibank.Language):
    classification_wals: Optional[str] = None
    classification_ethnologue: Optional[str] = None
    classification_glottolog: Optional[str] = None
    recently_extinct: Optional[str] = None
    long_extinct: Optional[str] = None
    year_of_extinction: Optional[str] = None
    code_wals: Optional[str] = None
    code_iso: Optional[str] = None
    transcribers: Optional[str] = None


@dataclasses.dataclass
class Form(pylexibank.Lexeme):
    gloss_in_source: Optional[str] = None


class Dataset(pylexibank.Dataset):
    dir = pathlib.Path(__file__).parent
    id = "asjp"
    language_class = Doculect
    lexeme_class = Form

    def cmd_makecldf(self, args):
        args.writer.cldf.add_component(
            'MediaTable',
            {'name': 'Author', 'propertyUrl': 'dc:creator'},
            {'name': 'Year', 'propertyUrl': 'dc:created'},
            {'name': 'Citation', 'propertyUrl': 'dc:bibliographicCitation'},
        )

        media = self.cldf_dir.joinpath('media')
        media.mkdir(exist_ok=True)
        for row in self.etc_dir.read_csv('media.csv', dicts=True):
            target = media / row['fname']
            shutil.copy(self.raw_dir / 'media' / row['fname'], target)
            args.writer.objects['MediaTable'].append(dict(
                ID=md5(target),
                Name=row['fname'],
                Description=row['description'],
                Media_Type=mimetypes.guess_type(target.name)[0],
                Download_URL=str(target.relative_to(self.cldf_dir)),
                Author=row['author'],
                Year=row['year'],
                Citation=row['citation'],
            ))

        asjp = ASJP(self.raw_dir)

        meaning_id_lookup = {v: k for k, v in MEANINGS_ALL.items()}
        meaning_id_lookup["breasts"] = meaning_id_lookup["breast"]

        for concept in sorted(
            self.conceptlists[0].concepts.values(),
            key=lambda c: meaning_id_lookup[c.label.replace("*", "")],
        ):
            args.writer.add_concept(
                ID=meaning_id_lookup[concept.label.replace("*", "")],
                Name=concept.label,
                Concepticon_ID=concept.concepticon_id,
                Concepticon_Gloss=concept.concepticon_gloss,
            )

        iso2gl = {l.iso: l.id for l in self.glottolog.languoids() if l.iso}

        lids = set()
        for doculect in sorted(asjp.iter_doculects(), key=lambda dl: dl.id):
            lid = slug(doculect.id)
            assert lid not in lids, doculect.id
            lids.add(lid)
            sources = asjp.source(doculect) or []
            sources = [src for src in sources if src.author or src.year or src.title_etc]
            for src in sources:
                args.writer.add_sources(
                    Source(
                        "misc", str(src.id), author=src.author, year=src.year, title=src.title_etc
                    )
                )

            # Obtain the glottocode mapping and fix it for cases with multiple mappings
            glottocode = iso2gl.get(doculect.code_iso)
            if lid == "LENCA_EL_SALVADOR":
                glottocode = "lenc1243"
            elif lid == "LENCA_HONDURAS":
                glottocode = "lenc1242"
            elif lid == "DANANSHAN_HMONG":
                glottocode = "hmon1332"
            elif lid == "SHIMENKAN_HMONG":
                glottocode = "smal1236"
            elif lid == "SUYONG_HMONG":
                glottocode = "larg1235"
            elif lid == "URADHI_ANGKAMUTHI":
                glottocode = "angg1238"
            elif lid == "URADHI_ATAMPAYA":
                glottocode = "atam1239"
            elif lid == "URADHI_YADHAYKENU":
                glottocode = "yadh1237"

            args.writer.add_language(
                ID=lid,
                Name=doculect.id,
                ISO639P3code=doculect.code_iso
                if re.fullmatch("[a-z]{3}", doculect.code_iso or "")
                else None,
                Glottocode=glottocode,
                Latitude=doculect.latitude,
                Longitude=doculect.longitude,
                classification_wals=doculect.classification_wals,
                classification_ethnologue=doculect.classification_ethnologue,
                classification_glottolog=doculect.classification_glottolog,
                recently_extinct=doculect.recently_extinct,
                long_extinct=doculect.long_extinct,
                year_of_extinction=doculect.year_of_extinction,
                code_wals=doculect.code_wals,
                code_iso=doculect.code_iso,
                transcribers=" and ".join(
                    sorted([tr.name for tr in asjp.transcriber(doculect) or []])
                ),
            )
            for synset in sorted(doculect.synsets, key=lambda ss: ss.meaning_id):
                for word in synset.words:
                    args.writer.add_form(
                        Language_ID=lid,
                        Parameter_ID=synset.meaning_id,
                        Value=word.form,
                        Form=word.form,
                        Loan=word.loan,
                        Comment=synset.comment,
                        gloss_in_source=synset.meaning,
                        Source=sorted([str(src.id) for src in sources]),
                    )
        assert not asjp.missing_transcribers
