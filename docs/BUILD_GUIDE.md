# Build guide (condensed)

Use **one region** for everything (for example Asia Pacific (Mumbai), ap-south-1). Replace every word in capitals with your own value. Never type angle brackets. Keep a notes file for: TABLE_ARN, QUEUE_URL, QUEUE_ARN, USER_POOL_ID, CLIENT_ID, COGNITO_DOMAIN, API_URL.

Every Lambda function needs the handler `lambda_function.handler`.

## 1. DynamoDB
- Table `QueueFairRequests`, partition key `requestId` (String), on-demand capacity.
- Index `owner-index`: partition key `owner` (String), sort key `createdAt` (Number), projection All.
- Turn on TTL with attribute `ttl`.

## 2. SQS
- Standard queue `queuefair-dlq`.
- Standard queue `queuefair-requests`: visibility timeout 3 minutes, dead-letter queue `queuefair-dlq`, maximum receives 3.
- Copy the queue URL (https://...) and ARN.

## 3. Pre sign-up Lambda
- Function `queuefair-presignup` (Python 3.12) with `src/presignup/lambda_function.py`.
- Environment variables: `ALLOWED_DOMAINS` (your college email domain) and `ALLOWED_EMAILS` (tester emails, comma separated). Never allow `gmail.com` as a domain.

## 4. Cognito
- User pool for a single-page app client `queuefair-web`, sign-in with email, required attributes email and name, temporary return URL.
- Note USER_POOL_ID, CLIENT_ID and COGNITO_DOMAIN (without https://).
- Extensions: add the pre sign-up trigger `queuefair-presignup`.

## 5. API Lambda
- Function `queuefair-api` with `src/api/lambda_function.py`, timeout 10 seconds.
- Variables: `TABLE`, `QUEUE_URL` now. `COGNITO_DOMAIN`, `CLIENT_ID`, `REDIRECT_URI` after step 7.
- Inline policy from `iam/api-policy.json` with your real ARNs.
- Do not create a Function URL.

## 6. API Gateway (HTTP API)
- Integration with `queuefair-api`. Routes: `GET /`, `GET /my`, `GET /stats`, `GET /status`, `POST /submit`, all using that integration.
- Stage `$default` with automatic deployment.
- JWT authorizer `cognito-jwt`: identity source `$request.header.Authorization`, issuer `https://cognito-idp.REGION.amazonaws.com/USER_POOL_ID`, audience CLIENT_ID.
- Attach the authorizer to every route except `GET /`.
- Check: `API_URL/stats` must return `{"message":"Unauthorized"}`.

## 7. Finish the settings
- Lambda variable `REDIRECT_URI` = API_URL with a trailing slash.
- Cognito app client: allowed callback URL and sign-out URL = the same value, authorization code grant, scopes openid, email, profile.

## 8. SES
- Verify the sender address and every tester address (Identities > Email address) in the same region.
- New accounts are in the sandbox: only verified addresses receive mail.

## 9. Worker Lambda
- Function `queuefair-worker` with `src/worker/lambda_function.py`, timeout 30 seconds.
- Variables: `TABLE`, `SENDER_EMAIL`, `WORK_SECONDS` (0.5).
- Policies: managed `AWSLambdaSQSQueueExecutionRole` plus `iam/worker-policy.json`.
- Trigger: SQS `queuefair-requests`, batch size 10, report batch item failures, maximum concurrency 5 (check your Lambda concurrency quota).

## 10. Test
- Sign-up with a non-approved email is refused.
- Sign-up with an approved email, enter the code, submit a request, watch it reach DONE and receive the email.
- `API_URL/stats` without a login returns Unauthorized.

## 11. Load test
- Sign in, then in the browser console run `sessionStorage.getItem('qf_token')` and copy the value.
- Run `python scripts/loadtest.py API_URL TOKEN 1000`.
- Watch SQS (messages available), Lambda Monitor (concurrent executions, errors) and DynamoDB (status DONE). Never commit the token.

## 12. Clean up
Delete the API, the three Lambda functions, both queues, the table, the user pool, the SES identities, the IAM roles and the CloudWatch log groups.

## Troubleshooting
- `QueueDoesNotExist`: QUEUE_URL is wrong or in another region. Use the URL, not the ARN.
- API Gateway `Not Found`: a route has no integration, or the `$default` stage is missing.
- Invalid issuer: use the exact format above, with the region filled in and no brackets.
- Sign-in returns to the Welcome card: check the callback URL (exact match, trailing slash) and the scopes.
- Requests stay `PENDING`: the worker trigger is missing or disabled, or the worker is failing. Read its logs.
- No email: look for `EMAIL FAILED` in the worker logs. Verify sender and recipient in SES and check Spam.
