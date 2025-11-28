"""
Python module to generate LegalDocML XML from eISB XML.

"""

from datetime import datetime as dt
from copy import deepcopy

from lxml.builder import E
from lxml import etree

from .utils import eli_uri_fragment, date_suffix

def akn_skeleton(act_meta: etree) -> E:
    """
    Inserts Act metadata (LegalDocML meta element) and skeleton body for LegalDocML XML).
    
    :param act_meta: etree.root of eISB XML
    :type act_meta: etree.root
    :return: LegalDocML XML with basic metadata elements and skeleton body structure, including cover pages.
    :rtype: lxml.builder.E object
    """

    uris = eli_uri_fragment(act_meta)

    meta = E.meta(
        E.identification(
            E.FRBRWork(
                E.FRBRthis(value=uris.work, showAs=act_meta.short_title),
                E.FRBRuri(value=uris.work),
                E.FRBRdate(date=act_meta.date_enacted.isoformat(), name="enacted"),
                E.FRBRauthor({"href": "#source"}),
                E.FRBRcountry(value="ie"),
                E.FRBRnumber(value=act_meta.number),
                E.FRBRname(value=act_meta.short_title)
            ),
            E.FRBRExpression(
                E.FRBRthis(value=uris.exp),
                E.FRBRuri(value=uris.exp),
                E.FRBRdate(date=act_meta.date_enacted.isoformat(), name="enacted"),
                E.FRBRauthor({"href": "#source"}),
                E.FRBRauthoritative(value="true"),
                E.FRBRlanguage(language="eng")
            ),
            E.FRBRManifestation(
                E.FRBRthis(value=uris.mani),
                E.FRBRuri(value=uris.mani),
                E.FRBRdate(date=dt.today().date().isoformat(), name="transformed"),
                E.FRBRauthor({"href": "#source"}),
                E.FRBRformat(value="application/akn+xml")
              
            ),
            source="#source"
        ),
        E.analysis(
            E.activeModifications(),
            source="#source"
        ),
        E.references(
            E.TLCOrganization(
                eId="source",
                href="https://www.data.oireachtas.ie",
                showAs="Houses of the Oireachtas"
            ),
            source="#source"
        )
    )

    harp = E.p(
        {"class": "harp"},
        E.img(src="/static/images/base/harp.jpg")
        )
    number = E.p(
        {"class": "Number"},
        E.docNumber(
            E.i("Number"),
            act_meta.number,
            E.i("of"),
            act_meta.year
        )
    )

    short_title = E.p(
        {"class": "shortTitle"},
        E.shortTitle(act_meta.short_title)
    )
    long_title = E.longTitle(
        act_meta.long_title
    )
    date_enacted = E.p(
        {"class": "DateOfEnactment", "style": "text-indent:0;margin-left:8;text-align:right"},
        E.docDate(
        {"date": act_meta.date_enacted.isoformat()},
        f"[{date_suffix(act_meta.date_enacted.day)} {act_meta.date_enacted.strftime('%B, %Y')}]"
        )
    )

    enacting_text = E.formula(
        {"name": "EnactingText", "style": "text-indent:0;margin-left:8;text-align:left"},
        E.p("Be it enacted by the Oireachtas as follows:")
    )

    cover_page = E.coverPage(
        deepcopy(harp),
        deepcopy(number),
        deepcopy(short_title),
        E.p("CONTENTS"),
        E.toc
    )

    preface = E.preface(
        harp,
        number,
        short_title,
        long_title,
        date_enacted,
        enacting_text
    )

    act = E.act(
            {"name": "ActOfTheOireachtas"},            
            meta,
            cover_page,
            preface,
            E.body()
            )

    return act
