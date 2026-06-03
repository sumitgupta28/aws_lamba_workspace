## follow below Bash commands to create lambda function and test it

```bash
export AWS_PROFILE=user-creation
terraform init
terraform apply -auto-approve
```

### use below command to delete the user

```bash
terraform destroy -auto-approve
```