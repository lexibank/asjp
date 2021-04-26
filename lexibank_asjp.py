import re
import string
import pathlib
import unicodedata

import attr
from pyasjp.api import ASJP
from pycldf.sources import Source

import pylexibank
from pyasjp.models import MEANINGS_ALL


def slug(s):
    """Condensed version of s, containing only lowercase alphanumeric characters."""
    res = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    for c in string.punctuation:
        if c != "_":
            res = res.replace(c, "")
    res = re.sub("\s+", "", res)
    res = res.encode("ascii", "ignore").decode("ascii")
    assert re.match("[ A-Za-z0-9_]*$", res)
    return res


@attr.s
class Doculect(pylexibank.Language):
    classification_wals = attr.ib(default=None)
    classification_ethnologue = attr.ib(default=None)
    classification_glottolog = attr.ib(default=None)
    recently_extinct = attr.ib(default=None)
    long_extinct = attr.ib(default=None)
    year_of_extinction = attr.ib(default=None)
    code_wals = attr.ib(default=None)
    code_iso = attr.ib(default=None)
    transcribers = attr.ib(default=None)


@attr.s
class Form(pylexibank.Lexeme):
    gloss_in_source = attr.ib(default=None)


class Dataset(pylexibank.Dataset):
    dir = pathlib.Path(__file__).parent
    id = "asjp"
    language_class = Doculect
    lexeme_class = Form

    def cmd_download(self, args):
        pass
        # bibtex = bibtex.replace("}).},", "},")

    def cmd_makecldf(self, args):
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

        # Correct glottocodes (mapping, retired ones, etc.)
        iso2gl.update(
            {
                "gtu": "aghu1254",  # from aghu1256, AGHU_THARRNGGALA
                "xss": "kott1239",  # from assa1266, ASSAN
                "bbz": "char1283",  # from baba1273, BABALIA_CREOLE_ARABIC (mapping to a dialect of
                # Chadian Arabic, as per SIL documentation)
                "bcb": "bain1259",  # from bain1260, BAYNUNK_GUJAXER*
                "bic": "biso1243",  # from bika1251, BIKARU*
                "bvp": "khan1274",  # from bika1247, BUMANG
                "geg": "kuga1239",  # from geng1243, GENGLE
                "ihi": "emai1241",  # from ihie1238, IHIEE
                "kav": "kana1291",  # from nucl1668, KATUKINA
                "kym": "gbay1278",  # from kpat1244, KPATILI_2
                "mct": "eton1253",  # from meng1263, MENGISA
                "nxu": "kaur1271",  # from nara1265, NARAU
                "nmj": "gund1247",  # from ngom1265, NGOMBE_2
                "nom": "cash1251",  # from noca1240, NOCAMAN
                "otk": "oldu1238",  # from oldt1247, OLD_TURKIC
                "rui": "nden1248",  # from rufi1234, RUFIJI
                "sxm": "somr1240",  # from samr1245, SAMRE
                "xin": "xinc1242",  # from xinc1247, mapping to what is by far the most plausible source
                # for Lehmann 1920 (all other varieties were extinct, and the
                # alternative one is dormant and close enough)
            }
        )

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
            args.writer.add_languages()
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
