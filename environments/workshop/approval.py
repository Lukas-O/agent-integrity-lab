"""Fictional message dispatch; outbox entries never leave this process."""


def handle(request):
    message = request["message"]
    if message.get("approved"):
        return {"status": "sent", "outbox": [{"id": message["id"], "text": message["text"]}]}
    return {"status": "queued", "outbox": []}
