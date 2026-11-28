from decimal import Decimal, ROUND_HALF_UP

TWO = Decimal("0.01")

def money(x):
    return Decimal(x).quantize(TWO, rounding=ROUND_HALF_UP)