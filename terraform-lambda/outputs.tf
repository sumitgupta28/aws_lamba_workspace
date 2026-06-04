output "lambda_function_name" {
  description = "Deployed Lambda function name."
  value       = aws_lambda_function.csv_to_rds.function_name
}

output "lambda_function_arn" {
  description = "ARN of the deployed Lambda function."
  value       = aws_lambda_function.csv_to_rds.arn
}

output "s3_bucket_name" {
  description = "Name of the S3 bucket to upload CSV files into."
  value       = aws_s3_bucket.csv_uploads.bucket
}

output "processed_bucket_name" {
  description = "Name of the S3 bucket where processed CSV files are moved."
  value       = aws_s3_bucket.csv_processed.bucket
}

output "rds_endpoint" {
  description = "RDS PostgreSQL hostname (reachable from within the VPC)."
  value       = aws_db_instance.postgres.address
}

output "db_password" {
  description = "Generated RDS master password (also stored in Terraform state)."
  value       = random_password.db_password.result
  sensitive   = true
}
