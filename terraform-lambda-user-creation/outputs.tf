output "access_key_id" {
  description = "The AWS Access Key ID for the Lambda manager"
  value       = aws_iam_access_key.lambda_manager_key.id
}

output "secret_access_key" {
  description = "The AWS Secret Access Key"
  value       = aws_iam_access_key.lambda_manager_key.secret
  sensitive   = true
}

resource "local_file" "aws_credentials" {
  filename        = "${pathexpand("~")}/.aws/credentials"
  file_permission = "0600"
  content         = <<EOF

[lambda_manager_profile]
aws_access_key_id     = ${aws_iam_access_key.lambda_manager_key.id}
aws_secret_access_key = ${aws_iam_access_key.lambda_manager_key.secret}
region = us-east-1
output = json
EOF
}