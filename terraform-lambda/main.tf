terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region  = var.aws_region
  profile = "lambda_manager_profile"
}

# -----------------------------------------------------------------------
# Random password for RDS (stored in Terraform state)
# -----------------------------------------------------------------------

resource "random_password" "db_password" {
  length  = 20
  special = false
}

# -----------------------------------------------------------------------
# VPC — two private subnets in different AZs (no NAT gateway needed;
# S3 access goes through the free Gateway VPC Endpoint below)
# -----------------------------------------------------------------------

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "${var.function_name}-vpc"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_subnet" "private_a" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]

  tags = {
    Name        = "${var.function_name}-private-a"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_subnet" "private_b" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = data.aws_availability_zones.available.names[1]

  tags = {
    Name        = "${var.function_name}-private-b"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# Route table for private subnets (used by S3 Gateway Endpoint)
resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name        = "${var.function_name}-private-rt"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_route_table_association" "private_a" {
  subnet_id      = aws_subnet.private_a.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "private_b" {
  subnet_id      = aws_subnet.private_b.id
  route_table_id = aws_route_table.private.id
}

# Internet Gateway — required for publicly_accessible RDS
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name        = "${var.function_name}-igw"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# Public subnets for the RDS instance
resource "aws_subnet" "public_a" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.3.0/24"
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true

  tags = {
    Name        = "${var.function_name}-public-a"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_subnet" "public_b" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.4.0/24"
  availability_zone       = data.aws_availability_zones.available.names[1]
  map_public_ip_on_launch = true

  tags = {
    Name        = "${var.function_name}-public-b"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# Route table for public subnets — default route to IGW
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name        = "${var.function_name}-public-rt"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_route" "public_internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.main.id
}

resource "aws_route_table_association" "public_a" {
  subnet_id      = aws_subnet.public_a.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "public_b" {
  subnet_id      = aws_subnet.public_b.id
  route_table_id = aws_route_table.public.id
}

# S3 Gateway VPC Endpoint — free; allows Lambda in the VPC to reach S3
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]

  tags = {
    Name        = "${var.function_name}-s3-endpoint"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# -----------------------------------------------------------------------
# Security Groups
# -----------------------------------------------------------------------

resource "aws_security_group" "lambda" {
  name        = "${var.function_name}-lambda-sg"
  description = "Lambda function egress to RDS and S3 endpoint"
  vpc_id      = aws_vpc.main.id

  egress {
    description     = "PostgreSQL to RDS"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.rds.id]
  }

  egress {
    description = "HTTPS for S3 VPC endpoint"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.function_name}-lambda-sg"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_security_group" "rds" {
  name        = "${var.function_name}-rds-sg"
  description = "RDS ingress from Lambda only"
  vpc_id      = aws_vpc.main.id

  tags = {
    Name        = "${var.function_name}-rds-sg"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_security_group_rule" "rds_from_lambda" {
  type                     = "ingress"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  security_group_id        = aws_security_group.rds.id
  source_security_group_id = aws_security_group.lambda.id
  description              = "PostgreSQL from Lambda"
}

resource "aws_security_group_rule" "rds_from_internet" {
  type              = "ingress"
  from_port         = 5432
  to_port           = 5432
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.rds.id
  description       = "PostgreSQL from internet"
}

# -----------------------------------------------------------------------
# RDS PostgreSQL — free tier: db.t3.micro, 20 GB gp2, single-AZ
# -----------------------------------------------------------------------

resource "aws_db_subnet_group" "main" {
  name       = "${var.function_name}-db-subnet-group"
  subnet_ids = [aws_subnet.public_a.id, aws_subnet.public_b.id]

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_db_instance" "postgres" {
  identifier        = "${var.function_name}-db"
  engine            = "postgres"
  engine_version    = "15"
  instance_class    = "db.t3.micro"
  allocated_storage = 20
  storage_type      = "gp2"

  db_name  = var.db_name
  username = var.db_username
  password = random_password.db_password.result

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  multi_az               = false
  publicly_accessible    = true
  skip_final_snapshot    = true
  deletion_protection    = false

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# -----------------------------------------------------------------------
# S3 bucket for CSV uploads
# -----------------------------------------------------------------------

resource "aws_s3_bucket" "csv_uploads" {
  bucket_prefix = "${var.function_name}-csv-"

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# -----------------------------------------------------------------------
# S3 bucket for processed CSV files (moved here after successful DB ingestion)
# -----------------------------------------------------------------------

resource "aws_s3_bucket" "csv_processed" {
  bucket_prefix = "${var.function_name}-processed-"

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

# -----------------------------------------------------------------------
# IAM: Lambda Execution Role
# -----------------------------------------------------------------------

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda_exec" {
  name               = "${var.function_name}-exec-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_iam_role_policy_attachment" "lambda_basic_exec" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Required for Lambda to create/manage ENIs when running inside a VPC
resource "aws_iam_role_policy_attachment" "lambda_vpc_access" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

data "aws_iam_policy_document" "lambda_s3_read" {
  statement {
    sid     = "IncomingBucket"
    effect  = "Allow"
    actions = ["s3:GetObject", "s3:ListBucket", "s3:DeleteObject"]
    resources = [
      aws_s3_bucket.csv_uploads.arn,
      "${aws_s3_bucket.csv_uploads.arn}/*",
    ]
  }

  statement {
    sid     = "ProcessedBucket"
    effect  = "Allow"
    actions = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
    resources = [
      aws_s3_bucket.csv_processed.arn,
      "${aws_s3_bucket.csv_processed.arn}/*",
    ]
  }
}

resource "aws_iam_role_policy" "lambda_s3_read" {
  name   = "${var.function_name}-s3-read"
  role   = aws_iam_role.lambda_exec.id
  policy = data.aws_iam_policy_document.lambda_s3_read.json
}

# -----------------------------------------------------------------------
# Lambda Layer — psycopg2 dependency
# -----------------------------------------------------------------------

resource "aws_lambda_layer_version" "psycopg2" {
  layer_name          = "${var.function_name}-psycopg2"
  filename            = "${path.module}/layer.zip"
  source_code_hash    = filebase64sha256("${path.module}/layer.zip")
  compatible_runtimes = ["python3.12"]
}

# -----------------------------------------------------------------------
# Lambda Function
# -----------------------------------------------------------------------

resource "aws_lambda_function" "csv_to_rds" {
  function_name    = var.function_name
  filename         = "${path.module}/lambda.zip"
  source_code_hash = filebase64sha256("${path.module}/lambda.zip")

  role    = aws_iam_role.lambda_exec.arn
  handler = "handler.lambda_handler"
  runtime = "python3.12"

  timeout     = 60
  memory_size = 128
  layers      = [aws_lambda_layer_version.psycopg2.arn]

  vpc_config {
    subnet_ids         = [aws_subnet.private_a.id, aws_subnet.private_b.id]
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      DB_HOST          = aws_db_instance.postgres.address
      DB_PORT          = "5432"
      DB_NAME          = var.db_name
      DB_USER          = var.db_username
      DB_PASSWORD      = random_password.db_password.result
      ENVIRONMENT      = var.environment
      PROCESSED_BUCKET = aws_s3_bucket.csv_processed.bucket
    }
  }

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_exec,
    aws_iam_role_policy_attachment.lambda_vpc_access,
  ]
}

# Allow S3 to invoke the Lambda function
resource "aws_lambda_permission" "s3_invoke" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.csv_to_rds.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.csv_uploads.arn
}

# S3 event notification — triggers Lambda on any *.csv upload
resource "aws_s3_bucket_notification" "csv_trigger" {
  bucket = aws_s3_bucket.csv_uploads.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.csv_to_rds.arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".csv"
  }

  depends_on = [aws_lambda_permission.s3_invoke]
}
