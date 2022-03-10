# Gaining more control over Multi-Regional AWS CloudFormation deployments.

AWS Immersion Days use a tool called Event Engine, which only supports deploying templates into a single region.  This project works around that limitation by creating a deployment Stepfunction and then executing CloudFormation cross region.  There is also support for dependencies (e.g., configure a primary region before secondary).

## How is the project organized

- **Infrastructure as Code**. The [app.py](app.py) declares all resources for deploying the Deployer service.
- **Supporting Lambda**.  The [src](src) folder declares the Lambda functions that support the Deployment State Machine. 

## How do I start my build window

User must first install [AWS CDK in Python](https://docs.aws.amazon.com/cdk/latest/guide/work-with-cdk-python.html).  Your specific workstation might require specifying **python3**** and **pip3** explicitly.  Running  **python --version** should confirm the local version is 3.x -- not 2.x! 

```sh
apt-get -y update && apt-get -y install --no-install-recommends npm
npm install -g aws-cdk
python3 -m pip install --upgrade pip
pip3 install -r ./requirements.txt
```

Next setup AWS [programmatic access](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html) via the CLI.

```sh
pip3/ install awscli
aws configure
```

Optionally, developers with [Docker](https://www.docker.com/) can use the [predefined image](Dockerfile).

```sh
# Build the image
docker build -t cdk-deployer .

# Launch an interactive terminal
MOUNT_AWS_CREDS=-v ~/.aws:/root/.aws
MOUNT_GIT_SRC=-v `pwd`:/files 
docker run -it $MOUNT_AWS_CREDS $MOUNT_GIT_SRC -w /files --entrypoint bash cdk-deployer
```

## How do I deploy these resources

1. Create an Amazon S3 bucket in the **Deployer's region**

```sh
export REGION=us-west-1
S3_ASSET_BUCKET=yournamehere-$REGION
aws s3 --region $REGION mb s3://$S3_ASSET_BUCKET
```

2. Export the deployment environment variables

```sh
export S3_ASSET_BUCKET=yournamehere-$REGION

# No trailing slash!!
export S3_ASSET_PREFIX=deployment/example
```

3. Run the deployment script

```sh
./deploy.sh
```

4. [Create a stack set](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-getting-started-create.html) with the **EventEngine.template.json** output.

```sh
aws cloudformation create-stack --stack-name DR-Deployer --region $REGION --template-url s3://$S3_ASSET_BUCKET/$S3_ASSET_PREFIX/EventEngine.template.json
```

## Is second deployment faster

Optionally, yes.  During `deploy.sh` it needs to convert the compress the Lambda functions into `.zip` files.  Afterward, you can reuse that content via the below command.

```sh
# https://docs.aws.amazon.com/cdk/latest/guide/environments.html
export CDK_DEFAULT_REGION=us-west-1
cdk deploy -a ./app.py 
```
