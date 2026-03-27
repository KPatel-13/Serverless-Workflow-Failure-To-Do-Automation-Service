from decimal import Decimal

import boto3


def _to_plain(value):
    """Convert DynamoDB Decimal values into normal Python JSON-safe values."""
    if isinstance(value, list):
        return [_to_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, Decimal):
        # Keep whole numbers as int, fractional numbers as float.
        return int(value) if value % 1 == 0 else float(value)
    return value


class DynamoDBRepository:
    """
    DynamoDB-backed repository implementation.

    Why this version keeps more complexity:
    - Supports existing GSI design on (repo, fingerprint)
    - Leaves room for more targeted lookup/query patterns later
    - Still keeps the same method interface as LocalRepository
    """

    def __init__(self, table_name: str):
        self.table_name = table_name
        dynamodb = boto3.resource("dynamodb")
        self.table = dynamodb.Table(table_name)

    def get_by_id(self, ticket_id: str) -> dict | None:
        """Fetch a single ticket by primary key."""
        response = self.table.get_item(Key={"id": ticket_id})
        item = response.get("Item")
        return _to_plain(item) if item else None

    def upsert(self, ticket: dict) -> dict:
        """Insert or replace a ticket."""
        self.table.put_item(Item=ticket)
        return _to_plain(ticket)

    def get_open_by_fingerprint(self, fingerprint: str) -> dict | None:
        """
        Look up an OPEN ticket for a given fingerprint.

        Why:
        - In the current service design, id == fingerprint.
        - So the fastest lookup is still GetItem by id.
        """
        item = self.get_by_id(fingerprint)
        if item and item.get("status") == "open":
            return item
        return None

    def query_by_repo_and_fingerprint(self, repo: str, fingerprint: str) -> list[dict]:
        """Forward-looking helper using the GSI directly."""
        response = self.table.query(
            IndexName="gsi_repo_fingerprint",
            KeyConditionExpression="repo = :repo AND fingerprint = :fingerprint",
            ExpressionAttributeValues={
                ":repo": repo,
                ":fingerprint": fingerprint,
            },
        )
        return _to_plain(response.get("Items", []))

    def list_tickets(self, status: str | None = None) -> list[dict]:
        """
        List tickets.

        Why Scan is acceptable here:
        - Table size is expected to stay small
        - Simpler than designing more indexes too early
        """
        scan_kwargs = {}
        if status:
            scan_kwargs = {
                "FilterExpression": "#s = :status",
                "ExpressionAttributeNames": {"#s": "status"},
                "ExpressionAttributeValues": {":status": status},
            }

        response = self.table.scan(**scan_kwargs)
        items = response.get("Items", [])

        while "LastEvaluatedKey" in response:
            scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
            response = self.table.scan(**scan_kwargs)
            items.extend(response.get("Items", []))

        return _to_plain(items)
