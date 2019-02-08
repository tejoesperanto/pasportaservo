import decimal

from .data import COUNTRIES_GEO, COUNTRIES_TINIEST, COUNTRIES_WITH_NO_BUFFER


def bufferize_country_boundaries(country_code):
    if country_code not in COUNTRIES_GEO:
        return None
    buffer = (
        0 if country_code in COUNTRIES_WITH_NO_BUFFER
        else
        (0.01 if country_code in COUNTRIES_TINIEST else 0.1)
    )
    precision = decimal.Decimal('0.001')  # Three decimal places.
    bbox = {
        'northeast': [
            float(decimal.Decimal(c + buffer if c < +179.9 else c).quantize(precision, decimal.ROUND_CEILING))
            for c in COUNTRIES_GEO[country_code]['bbox']['northeast']
        ],
        'southwest': [
            float(decimal.Decimal(c - buffer if c > -179.9 else c).quantize(precision, decimal.ROUND_FLOOR))
            for c in COUNTRIES_GEO[country_code]['bbox']['southwest']
        ],
    }
    return {'bbox': bbox, 'center': COUNTRIES_GEO[country_code]['center']}
