"""An order card in a fictional workshop."""


def handle(request):
    order = request["order"]
    return {"id": order["id"], "quantity": order["quantity"]}
