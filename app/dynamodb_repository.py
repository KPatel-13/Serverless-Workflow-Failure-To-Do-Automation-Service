import boto3


class DynamoDBRepository:
    """
    DynamoDB-backed repository implementation.

    Why this version keeps more complexity:
    - Supports  existing GSI design on (repo, fingerprint)
    - Leaves room for more targeted lookup/query patterns later
    - Still keeps the same method interface as LocalRepository
    """

    def __init__(self, table_name: str):
        self.table_name = table_name
        dynamodb = boto3.resource("dynamodb")
        self.table = dynamodb.Table(table_name)

    def get_by_id(self, ticket_id: str) -> dict | None:
        """
        Fetch a single ticket by primary key.

        Why:
        - The service uses id == fingerprint for direct ticket retrieval.
        """
        response = self.table.get_item(Key={"id": ticket_id})
        return response.get("Item")

    def upsert(self, ticket: dict) -> dict:
        """
        Insert or replace a ticket.

        Why:
        - The service layer prepares the full ticket state.
        """
        self.table.put_item(Item=ticket)
        return ticket

    def get_open_by_fingerprint(self, fingerprint: str) -> dict | None:
        """
        Look up an OPEN ticket for a given fingerprint.

        Why:
        - In the current service design, id == fingerprint.
        - So the fastest lookup is still GetItem by id.
        - DynamoDB table/index design is still kept for future use.
        """
        item = self.get_by_id(fingerprint)
        if item and item.get("status") == "open":
            return item
        return None

    def query_by_repo_and_fingerprint(self, repo: str, fingerprint: str) -> list[dict]:
        """
        Forward-looking helper using the GSI directly.
        """
        response = self.table.query(
            IndexName="gsi_repo_fingerprint",
            KeyConditionExpression="repo = :repo AND fingerprint = :fingerprint",
            ExpressionAttributeValues={
                ":repo": repo,
                ":fingerprint": fingerprint,
            },
        )
        return response.get("Items", [])

    def list_tickets(self, status: str | None = None) -> list[dict]:
        """
        List tickets.

        Why Scan is acceptable here:
        - Table size is expected to stay small
        - Simpler than designing more indexes too early
        """
        if status:
            response = self.table.scan(
                FilterExpression="#s = :status",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={":status": status},
            )
        else:
            response = self.table.scan()

        items = response.get("Items", [])

        while "LastEvaluatedKey" in response:
            if status:
                response = self.table.scan(
                    FilterExpression="#s = :status",
                    ExpressionAttributeNames={"#s": "status"},
                    ExpressionAttributeValues={":status": status},
                    ExclusiveStartKey=response["LastEvaluatedKey"],
                )
            else:
                response = self.table.scan(
                    ExclusiveStartKey=response["LastEvaluatedKey"]
                )
            items.extend(response.get("Items", []))

        return items