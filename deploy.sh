#!/bin/bash
###############################################
#  Cross Region CloudFormation for Event Engine
#
#  2021-09-24 Nate Bachmeier - Created.
###############################################

if [ -z "$S3_ASSET_BUCKET" ]
then
  if [ -z "$1" ]
  then
    echo "Usage: $0 the-bucket-name"
    exit 1
  fi
  
  export S3_ASSET_BUCKET=$1
fi

# No trailing slashs!
if [ -z "$S3_ASSET_PREFIX" ]
then
  export S3_ASSET_PREFIX=cfn-multiregional-orchestration
fi

# EventEngine requires we use the replicated bucket
export TEMPLATE_ASSET_BUCKET=`echo ${S3_ASSET_BUCKET/us-east-1/us-west-1}`

echo ==========================
echo Initializing Deployment
echo ==========================
echo "Asset Upload Bucket:  ${S3_ASSET_BUCKET}"
echo "........with prefix:  ${S3_ASSET_PREFIX}"
echo "Deployment Bucket  :  ${TEMPLATE_ASSET_BUCKET}"

mkdir -p packages
mkdir -p bin/
rm -f bin/*.zip

function make_pkg {
echo ==========================
echo Making $1.zip
echo ==========================
pip install -t packages/$1 -r src/$1/requirements.txt
pushd packages/$1
zip -r ../../bin/$1.zip .
popd
echo "adding custom python sources"
pushd src/$1
zip -g ../../bin/$1.zip *.py
popd
}

make_pkg preaction
make_pkg launch
make_pkg monitor
make_pkg complete

echo ==========================
echo Synthesize the code
echo ==========================

##aws s3 rm --recursive s3://$S3_ASSET_BUCKET/$S3_ASSET_PREFIX/
rm -rf cdk.out/*
cdk synth --app ./app.py

echo ==========================
echo Zip codegen components 
echo ==========================
for f in `ls cdk.out/ | grep asset | grep -v .zip`
do
pushd cdk.out/$f
zip -r ../$f.zip *
popd
done

echo ==========================
echo Fix the parameters for Event Engine 
echo ==========================
./ee-util.py
cat cdk.out/EventEngine.template.json | jq '.Parameters'

echo ==========================
echo Finally, upload everything
echo ==========================

if [ -z "$CI_JOB_TOKEN" ]
then
echo aws s3 cp --recursive cdk.out/ s3://$S3_ASSET_BUCKET/$S3_ASSET_PREFIX/
aws s3 cp --recursive cdk.out/ s3://$S3_ASSET_BUCKET/$S3_ASSET_PREFIX/
else
pushd cdk.out
zip -r ../deployer.zip .
popd
version=`date +%Y.%m.%d`
curl --header "JOB-TOKEN: $CI_JOB_TOKEN" --upload-file ./deployer.zip "${CI_API_V4_URL}/projects/${CI_PROJECT_ID}/packages/generic/${CI_COMMIT_BRANCH}/${version}/deployer.zip"
fi
