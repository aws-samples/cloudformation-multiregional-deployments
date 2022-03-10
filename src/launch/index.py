import boto3
import requests
from json import dumps

'''
Initialize AWS XRAY available.
'''
try:
  from aws_xray_sdk.core import patch_all, xray_recorder
  patch_all()
  XRAY_AVAILABLE=True
except:
  XRAY_AVAILABLE=False


def function_main(event:dict, context:dict)->dict:
  print(dumps(event))

  assert 'region_name' in event, "missing region_name"
  assert 'stack_name' in event, "missing stack_name"
  assert 'template_path' in event, "missing template_path"
  assert 'parameters' in event, "missing parameters"

  region_name:str = event['region_name']
  stack_name:str = event['stack_name']
  template_path:str = event['template_path']
  parameters:dict = event['parameters']

  '''
  Fetch the template
  '''
  template = requests.get(url=template_path).text
  print(template)

  client = boto3.client('cloudformation', region_name=region_name)
  try:
    client.create_stack(
      StackName=stack_name,
      TemplateBody=template,
      DisableRollback=False,
      Capabilities=[
        'CAPABILITY_IAM','CAPABILITY_NAMED_IAM','CAPABILITY_AUTO_EXPAND',
      ],
      Parameters=[{
        'ParameterKey':x, 
        'ParameterValue': parameters[x], 
        'UsePreviousValue': True,
      } for x in parameters.keys()])

    return {
      'status': 'Creating the stack %s' % stack_name
    }
  except client.exceptions.AlreadyExistsException as error:
    return {
      'status': 'Stack %s AlreadyExists; returning existing' % stack_name,
    }

if __name__ == '__main__':
  '''
  Debug the local run...
  '''
  if XRAY_AVAILABLE:
    xray_recorder.begin_segment('LocalDebug')

  function_main(
    event={
      "template_path": "https://disaster-recovery.wellarchitectedlabs.com/Reliability/Disaster%20Recovery/Workshop_1/US-East-1-Deployment/_index.en.files/BackupAndRestore.yaml",
      "stack_name": "DeployTest",
      "region_name": "us-east-1",
      "parameters":{
        'IsPrimary':'yes',
        'LatestAmiId': '/aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-gp2'
      }
    },
    context={
    })
