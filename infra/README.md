# Infrastructure (Terraform)

## Planned resources
- DynamoDB table for To-Do tickets (incl. GSI for repo/status lookup)
- Lambda (Python 3.11) + IAM role (least privilege)
- API Gateway HTTP API (routes + CORS)
- CloudWatch log group retention (7–14 days)

## Commands (later, when AWS creds are configured)
From `infra/terraform`:
- `terraform fmt -recursive`
- `terraform init`
- `terraform validate`
- `terraform plan`

> Deployment (`terraform apply`) will be done only when explicitly ready.
