
class LocalRepository:
    """
    In-memory storage used for local tests.

    Why:
    - Unit tests shouldn't require AWS creds or DynamoDB.
    - This keeps it "local-first".
    - Later we can add DynamoDBRepository with the same methods.
    """

    def __init__(self):
        # Store tickets by id
        self.items = {}  # dict[str, dict]

    def get_open_by_fingerprint(self, fingerprint: str) -> dict | None:
        """
        Return an OPEN ticket matching fingerprint, else None.

        Used by service layer to implement dedupe behaviour.
        """
        for t in self.items.values():
            if t.get("fingerprint") == fingerprint and t.get("status") == "open":
                return t
        return None

    def get_by_id(self, ticket_id: str) -> dict | None:
        """Get a ticket by id."""
        return self.items.get(ticket_id)

    def upsert(self, ticket: dict) -> dict:
        """
        Insert or update a ticket.

        The service uses this after it creates/updates a ticket.
        """
        self.items[ticket["id"]] = ticket
        return ticket

    def list_tickets(self, status: str | None = None) -> list[dict]:
        """
        List tickets, optionally filtered by status.
        """
        values = list(self.items.values())
        if status:
            values = [t for t in values if t.get("status") == status]
        return values