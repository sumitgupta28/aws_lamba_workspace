variable "aws_region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "us-east-1"
}

variable "function_name" {
  description = "Name of the Lambda function."
  type        = string
  default     = "hello-world"
}

variable "environment" {
  description = "Deployment environment tag (dev, staging, prod)."
  type        = string
  default     = "dev"
}
