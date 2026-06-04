provider "aws" {
  region = "us-east-1"
  profile = "user-creation"
  skip_metadata_api_check     = true
  skip_region_validation      = true
  skip_credentials_validation = true
  skip_requesting_account_id  = true
}
