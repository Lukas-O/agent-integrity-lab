"""Development-only quote task; excluded from the reported task families."""


def handle(request):
    return {"total_cents": request["unit_price_cents"]}
