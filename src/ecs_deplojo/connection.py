import boto3
from botocore.config import Config


class Connection:
    def __init__(self, role_arn=None):
        credentials = {}
        if role_arn:
            sts = boto3.client("sts")
            resp = sts.assume_role(RoleArn=role_arn, RoleSessionName="ecs-deplojo")
            credentials.update(
                {
                    "aws_secret_access_key": resp["Credentials"]["SecretAccessKey"],
                    "aws_access_key_id": resp["Credentials"]["AccessKeyId"],
                    "aws_session_token": resp["Credentials"]["SessionToken"],
                }
            )
        config = Config(
            signature_version="v4", retries={"max_attempts": 10, "mode": "standard"}
        )

        self.ecs = boto3.client("ecs", config=config, **credentials)
