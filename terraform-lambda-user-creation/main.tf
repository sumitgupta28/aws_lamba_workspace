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
  statement {
    effect = "Allow"
    actions = [
      "lambda:*",
      "iam:PassRole",
      "iam:CreateRole",
      "iam:TagRole",
      "iam:GetRole",
      "iam:ListRolePolicies",
      "iam:ListAttachedRolePolicies",
      "iam:ListInstanceProfilesForRole",
      "iam:AttachRolePolicy",
      "iam:DetachRolePolicy",
      "iam:DeleteRole",
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "ApiGatewayV2:CreateApi",
      "ApiGatewayV2:GetApi",
      "ApiGatewayV2: DeleteApi",
      "apigateway:POST",
      "apigateway:GET",
      "apigateway:DELETE"
    ]
    resources = ["*"]
  }
}

# Create the Managed IAM Policy
resource "aws_iam_policy" "lambda_manager_policy" {
  name        = "LambdaManagementPolicy"
  description = "Provides full permissions to manage AWS Lambda functions"
  policy      = data.aws_iam_policy_document.lambda_management_permissions.json
}

# Attach the Policy to the IAM User
resource "aws_iam_user_policy_attachment" "attach_lambda_policy" {
  user       = aws_iam_user.lambda_manager.name
  policy_arn = aws_iam_policy.lambda_manager_policy.arn
}