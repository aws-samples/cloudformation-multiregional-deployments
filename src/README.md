# Amazon Lambda functions source code.

The solution uses an Amazon Step Function and various Lambda functions to orchestrate the multiple deployments.

## What does each function do

- The [PreActions function](preaction) executes before deploying each stack within the JobDefinition.
- The [Launch Template](launch) initiates the call to CloudFormation's [Create Stack API](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_CreateStack.html).
- The [Monitor Execution](monitor) use the [DescribeStacks API](https://docs.aws.amazon.com/AWSCloudFormation/latest/APIReference/API_DescribeStacks.html) to retrieve the stack progress.
- The [Report Completion](complete) forwards success and failure notifications to the orchestration stacks
