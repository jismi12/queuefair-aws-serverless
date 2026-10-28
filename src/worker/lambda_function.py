import json, os, time, boto3
from botocore.exceptions import ClientError

table = boto3.resource("dynamodb").Table(os.environ["TABLE"])
ses = boto3.client("sesv2")
SENDER = os.environ.get("SENDER_EMAIL")
WORK = float(os.environ.get("WORK_SECONDS", "0.5"))
LABELS = {"certificate": "Certificate", "lab-booking": "Lab booking", "fee-receipt": "Fee receipt"}

def is_condition_failure(e):
    return e.response["Error"]["Code"] == "ConditionalCheckFailedException"

def move(rid, new_status, allowed):
    """Change status only if the request exists and is currently in an allowed state."""
    values = {":new": new_status, ":t": int(time.time())}
    for i, a in enumerate(allowed):
        values[":a" + str(i)] = a
    cond = "attribute_exists(requestId) AND #s IN (" + ", ".join(
        ":a" + str(i) for i in range(len(allowed))) + ")"
    resp = table.update_item(
        Key={"requestId": rid},
        UpdateExpression="SET #s = :new, updatedAt = :t",
        ConditionExpression=cond,
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues=values,
        ReturnValues="ALL_NEW")
    return resp["Attributes"]

def send_email(item):
    """An email problem is logged but never fails the request."""
    if not (item.get("notify") and SENDER and item.get("owner")):
        return
    try:
        secs = int(item["updatedAt"]) - int(item["createdAt"])
        label = LABELS.get(item["type"], item["type"])
        text = ("Hi " + item.get("name", "") + ",\n\n"
                "Your " + label + " request is complete.\n"
                "Request ID: " + item["requestId"] + "\n"
                "Time taken: " + str(secs) + " seconds.\n\n"
                "QueueFair Campus Portal")
        ses.send_email(
            FromEmailAddress=SENDER,
            Destination={"ToAddresses": [item["owner"]]},
            Content={"Simple": {
                "Subject": {"Data": "Your " + label + " request is ready"},
                "Body": {"Text": {"Data": text}}}})
    except Exception as e:
        print("EMAIL FAILED", repr(e))

def handler(event, context):
    failures = []
    for rec in event["Records"]:
        try:
            rid = json.loads(rec["body"])["requestId"]
            try:
                move(rid, "PROCESSING", ["PENDING", "PROCESSING"])
            except ClientError as e:
                if is_condition_failure(e):
                    print("SKIP (missing or already finished)", rid)
                    continue
                raise
            time.sleep(WORK)  # stands in for real work
            try:
                item = move(rid, "DONE", ["PROCESSING"])
            except ClientError as e:
                if is_condition_failure(e):
                    print("SKIP (finished by another worker)", rid)
                    continue
                raise
            send_email(item)
        except Exception as e:
            print("FAILED", rec["messageId"], repr(e))
            failures.append({"itemIdentifier": rec["messageId"]})
    return {"batchItemFailures": failures}
