# Create the IAM User
resource "aws_iam_user" "lambda_manager" {
  name = "lambda-manager-user"
  path = "/system/"
}

# Create Programmatic Access Keys
resource "aws_iam_access_key" "lambda_manager_key" {
  user = aws_iam_user.lambda_manager.name
}

# Define the IAM Policy Document for Lambda Management
data "aws_iam_policy_document" "lambda_management_permissions" {
  # Lambda
  statement {
    effect    = "Allow"
    actions   = ["lambda:*"]
    resources = ["*"]
  }

  # IAM — role and policy management needed for Lambda execution roles
  statement {
    effect = "Allow"
    actions = [
      "iam:PassRole",
      "iam:CreateRole",
      "iam:TagRole",
      "iam:GetRole",
      "iam:DeleteRole",
      "iam:ListRolePolicies",
      "iam:ListAttachedRolePolicies",
      "iam:ListInstanceProfilesForRole",
      "iam:AttachRolePolicy",
      "iam:DetachRolePolicy",
      "iam:PutRolePolicy",
      "iam:GetRolePolicy",
      "iam:DeleteRolePolicy",
      "iam:CreatePolicy",
      "iam:DeletePolicy",
      "iam:GetPolicy",
      "iam:GetPolicyVersion",
      "iam:ListPolicyVersions",
      "iam:CreatePolicyVersion",
      "iam:DeletePolicyVersion",
    ]
    resources = ["*"]
  }

  # CloudWatch Logs
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "logs:DescribeLogGroups",
      "logs:DeleteLogGroup",
    ]
    resources = ["*"]
  }

  # API Gateway
  statement {
    effect    = "Allow"
    actions   = ["apigateway:*"]
    resources = ["*"]
  }

  # S3 — bucket lifecycle for CSV upload bucket
  statement {
    effect = "Allow"
    actions = [
      "s3:CreateBucket",
      "s3:DeleteBucket",
      "s3:ListBucket",
      "s3:GetBucketNotification",
      "s3:PutBucketNotification",
      "s3:GetBucketTagging",
      "s3:PutBucketTagging",
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:GetBucketPolicy",
      "s3:PutBucketPolicy",
      "s3:DeleteBucketPolicy",
      "s3:GetBucketVersioning",
      "s3:GetBucketCORS",
      "s3:GetBucketWebsite",
      "s3:GetBucketRequestPayment",
      "s3:GetBucketObjectLockConfiguration",
      "s3:GetAccelerateConfiguration",
      "s3:GetBucketLogging",
      "s3:GetLifecycleConfiguration",
      "s3:GetReplicationConfiguration",
      "s3:ListAllMyBuckets",
    ]
    resources = ["*"]
  }

  # RDS — instance and subnet group lifecycle
  statement {
    effect = "Allow"
    actions = [
      "rds:CreateDBInstance",
      "rds:DeleteDBInstance",
      "rds:ModifyDBInstance",
      "rds:DescribeDBInstances",
      "rds:CreateDBSubnetGroup",
      "rds:DeleteDBSubnetGroup",
      "rds:DescribeDBSubnetGroups",
      "rds:AddTagsToResource",
      "rds:ListTagsForResource",
      "rds:DescribeDBParameterGroups",
      "rds:CreateDBParameterGroup",
      "rds:DeleteDBParameterGroup",
    ]
    resources = ["*"]
  }

  # EC2 / VPC — VPC, subnets, security groups, route tables, VPC endpoints
  statement {
    effect = "Allow"
    actions = [
      "ec2:CreateVpc",
      "ec2:DeleteVpc",
      "ec2:ModifyVpcAttribute",
      "ec2:DescribeVpcs",
      "ec2:DescribeVpcAttribute",
      "ec2:CreateSubnet",
      "ec2:DeleteSubnet",
      "ec2:DescribeSubnets",
      "ec2:ModifySubnetAttribute",
      "ec2:CreateSecurityGroup",
      "ec2:DeleteSecurityGroup",
      "ec2:DescribeSecurityGroups",
      "ec2:AuthorizeSecurityGroupIngress",
      "ec2:RevokeSecurityGroupIngress",
      "ec2:AuthorizeSecurityGroupEgress",
      "ec2:RevokeSecurityGroupEgress",
      "ec2:CreateVpcEndpoint",
      "ec2:DeleteVpcEndpoints",
      "ec2:DescribeVpcEndpoints",
      "ec2:ModifyVpcEndpoint",
      "ec2:DescribeRouteTables",
      "ec2:CreateRouteTable",
      "ec2:DeleteRouteTable",
      "ec2:AssociateRouteTable",
      "ec2:DisassociateRouteTable",
      "ec2:CreateTags",
      "ec2:DeleteTags",
      "ec2:DescribeTags",
      "ec2:DescribeAvailabilityZones",
      "ec2:DescribeNetworkInterfaces",
      "ec2:CreateNetworkInterface",
      "ec2:DeleteNetworkInterface",
      "ec2:DescribePrefixLists",
    ]
    resources = ["*"]
  }
}

# Create the Managed IAM Policy
resource "aws_iam_policy" "lambda_manager_policy" {
  name        = "LambdaManagementPolicy"
  description = "Permissions to manage Lambda, RDS, S3, VPC, and supporting resources"
  policy      = data.aws_iam_policy_document.lambda_management_permissions.json
}

# Attach the Policy to the IAM User
resource "aws_iam_user_policy_attachment" "attach_lambda_policy" {
  user       = aws_iam_user.lambda_manager.name
  policy_arn = aws_iam_policy.lambda_manager_policy.arn
}
