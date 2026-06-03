variable "aws_region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "us-east-1"
}

variable "function_name" {
  description = "Name of the Lambda function and resource name prefix."
  type        = string
  default     = "csv-to-rds"
}

variable "environment" {
  description = "Deployment environment tag (dev, staging, prod)."
  type        = string
  default     = "dev"
}

variable "db_name" {
  description = "PostgreSQL database name."
  type        = string
  default     = "csvdb"
}

variable "db_username" {
  description = "PostgreSQL master username."
  type        = string
  default     = "dbadmin"
}
