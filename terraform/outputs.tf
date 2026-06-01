output "lambda_function_name" {
  description = "Deployed Lambda function name."
  value       = aws_lambda_function.hello_world.function_name
}

output "lambda_function_arn" {
  description = "ARN of the deployed Lambda function."
  value       = aws_lambda_function.hello_world.arn
}

output "api_gateway_url" {
  description = "Base URL for the HTTP API."
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "invoke_url" {
  description = "Direct curl-ready URL for the hello endpoint."
  value       = "${aws_apigatewayv2_stage.default.invoke_url}/hello"
}
