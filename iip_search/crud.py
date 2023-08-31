import unicodedata

from typing import Literal
from urllib import parse

from sqlalchemy import and_, or_
from sqlalchemy import func
from sqlalchemy import select

from sqlalchemy.orm import Session

from iip_search import models
from iip_search import schemas


def get_city(db: Session, city_id: int):
    return db.query(models.City).filter(models.City.id == city_id).one()


def get_inscription(db: Session, slug: str):
    return (
        db.query(models.Inscription)
        .filter(models.Inscription.filename == f"{slug}.xml")
        .one()
    )


def get_provenance(db: Session, provenance_id: id):
    return (
        db.query(models.Provenance).filter(models.Provenance.id == provenance_id).one()
    )


def get_region(db: Session, region_id: int):
    return db.query(models.Region).filter(models.Region.id == region_id).one()


def facet_cities_query(db: Session):
    return (
        db.query(models.City, func.count(models.Inscription.id).label("hits"))
        .join(models.City.inscriptions)
        .order_by(models.City.placename)
        .group_by(models.City.id)
    )


def facet_forms_query(db: Session):
    return (
        db.query(models.IIPForm, func.count(models.Inscription.id))
        .join(models.IIPForm.inscriptions)
        .group_by(models.IIPForm.id)
        .order_by(
            func.lower(models.IIPForm.description), func.lower(models.IIPForm.xml_id)
        )
    )


def facet_genres_query(db: Session):
    return (
        db.query(models.IIPGenre, func.count(models.Inscription.id))
        .join(models.IIPGenre.inscriptions)
        .group_by(models.IIPGenre.id)
        .order_by(
            func.lower(models.IIPGenre.description), func.lower(models.IIPGenre.xml_id)
        )
    )


def facet_languages_query(db: Session):
    return (
        db.query(models.Language, func.count(models.Inscription.id))
        .join(models.Language.inscriptions)
        .group_by(models.Language.id)
        .order_by(
            func.lower(models.Language.label), func.lower(models.Language.short_form)
        )
    )


def facet_materials_query(db: Session):
    return (
        db.query(models.IIPMaterial, func.count(models.Inscription.id))
        .join(models.IIPMaterial.inscriptions)
        .group_by(models.IIPMaterial.id)
        .order_by(
            func.lower(models.IIPMaterial.description),
            func.lower(models.IIPMaterial.xml_id),
        )
    )


def facet_religions_query(db: Session):
    return (
        db.query(models.IIPReligion, func.count(models.Inscription.id))
        .join(models.IIPReligion.inscriptions)
        .group_by(models.IIPReligion.id)
        .order_by(
            func.lower(models.IIPReligion.description),
            func.lower(models.IIPReligion.xml_id),
        )
    )


def list_cities(db: Session):
    return db.query(models.City).order_by(models.City.placename).all()


# possibly maps to "physical type" in the interface?
def list_forms(db: Session):
    return (
        db.query(models.IIPForm)
        .order_by(
            func.lower(models.IIPForm.description), func.lower(models.IIPForm.xml_id)
        )
        .all()
    )


def list_genres(db: Session):
    return (
        db.query(models.IIPGenre)
        .order_by(
            func.lower(models.IIPGenre.description), func.lower(models.IIPGenre.xml_id)
        )
        .all()
    )


def list_languages(db: Session):
    return (
        db.query(models.Language)
        .order_by(
            func.lower(models.Language.label), func.lower(models.Language.short_form)
        )
        .all()
    )


def list_languages_query(db: Session):
    return (
        db.query(models.Language, func.count(models.Inscription.id))
        .join(models.Language.inscriptions)
        .order_by(
            func.lower(models.Language.label), func.lower(models.Language.short_form)
        )
        .group_by(models.Language.id)
    )


def list_locations(db: Session):
    cities = list_cities(db)
    provenances = list_provenances(db)
    regions = list_regions(db)

    return cities + provenances + regions


def list_materials(db: Session):
    return (
        db.query(models.IIPMaterial)
        .order_by(
            func.lower(models.IIPMaterial.description),
            func.lower(models.IIPMaterial.xml_id),
        )
        .all()
    )


def list_provenances(db: Session):
    return db.query(models.Provenance).all()


def list_regions(db: Session):
    return db.query(models.Region).all()


def list_religions(db: Session):
    return (
        db.query(models.IIPReligion)
        .order_by(
            func.lower(models.IIPReligion.description),
            func.lower(models.IIPReligion.xml_id),
        )
        .all()
    )


def list_facets(db: Session):
    cities = facet_cities_query(db).all()
    genres = facet_genres_query(db).all()
    languages = facet_languages_query(db).all()
    materials = facet_materials_query(db).all()
    physical_types = facet_forms_query(db).all()
    religions = facet_religions_query(db).all()

    return dict(
        cities=cities,
        genres=genres,
        languages=languages,
        materials=materials,
        physical_types=physical_types,
        religions=religions,
    )


def list_inscriptions(
    db: Session,
    text_search: str | None = None,
    description_place_id: str | None = None,
    figures: str | None = None,
    not_before: int | None = None,
    not_before_era: Literal["bce"] | Literal["ce"] | None = None,
    not_after: int | None = None,
    not_after_era: Literal["bce"] | Literal["ce"] | None = None,
    cities: list[int] | None = [],
    provenances: list[int] | None = [],
    genres: list[int] | None = [],
    physical_types: list[int] | None = [],
    languages: list[int] | None = [],
    religions: list[int] | None = [],
    materials: list[int] | None = [],
):
    query = (
        db.query(models.Inscription)
        .filter(models.Inscription.display_status == models.DisplayStatus.APPROVED)
        .distinct(models.Inscription.id)
    )

    ands = []
    ors = []

    if text_search is not None and text_search != "":
        cleaned_text_search = remove_accents(parse.unquote(text_search))
        ors.append(
            models.Inscription.editions.any(
                models.Edition.searchable_text.match(cleaned_text_search)
            )
        )

    if description_place_id is not None and description_place_id != "":
        query = query.filter(
            models.Inscription.searchable_text.match(description_place_id)
        )

    if figures is not None and figures != "":
        ors.append(
            models.Inscription.figures.any(models.Figure.searchable_text.match(figures))
        )

    if not_before is not None and not_before != "":
        if not_before_era == "bce":
            not_before = -int(not_before)
        else:
            not_before = int(not_before)
        ands.append(models.Inscription.not_before >= not_before)

    if not_after is not None and not_after != "":
        if not_after_era == "bce":
            not_after = -int(not_after)
        else:
            not_after = int(not_after)
        ands.append(models.Inscription.not_after <= not_after)

    if cities is not None and len(cities) > 0:
        ands.append(models.Inscription.city_id.in_(cities))

    if provenances is not None and len(provenances) > 0:
        ands.append(models.Inscription.provenance_id.in_(provenances))

    if genres is not None and len(genres) > 0:
        ands.append(models.Inscription.iip_genres.any(models.IIPGenre.id.in_(genres)))

    if physical_types is not None and len(physical_types) > 0:
        ands.append(
            models.Inscription.iip_forms.any(models.IIPForm.id.in_(physical_types))
        )

    if languages is not None and len(languages) > 0:
        ands.append(models.Inscription.languages.any(models.Language.id.in_(languages)))

    if religions is not None and len(religions) > 0:
        ands.append(
            models.Inscription.iip_religions.any(models.IIPReligion.id.in_(religions))
        )

    if materials is not None and len(materials) > 0:
        ands.append(
            models.Inscription.iip_materials.any(models.IIPMaterial.id.in_(materials))
        )

    return query.filter(or_(*ors)).filter(and_(*ands)).group_by(models.Inscription.id)


def remove_accents(input_str):
    nfkd_form = unicodedata.normalize("NFKD", input_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])


def update_inscription(db: Session, slug: str, inscription: schemas.InscriptionPatch):
    to_update = db.query(models.Inscription).filter_by(filename=f"{slug}.xml").one()
    to_update.display_status = inscription.display_status

    db.commit()

    return get_inscription(db, slug)
