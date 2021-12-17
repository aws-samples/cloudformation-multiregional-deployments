import boto3
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

  region_name:str = event['region_name']
  stack_name:str = event['stack_name']

  '''
  Find the default VPC
  '''
  ec2_client = boto3.client('ec2', region_name=region_name)
  try:
    response = ec2_client.describe_vpcs(Filters=[
      {
        'Name':'is-default',
        'Values': ['true']
      }
    ])
  except Exception as error:
    print('Unable to describe_vpcs()')
    raise error

  '''
  Persist the setting into SSM
  '''
  param_value = [vpc['VpcId'] for vpc in response['Vpcs'] if vpc['IsDefault']]
  if not len(param_value) == 1:
    print('Unexpected default vpc count %d' % len(param_value))
    raise ValueError('Unexpected default vpc count')
  else:
    param_value = param_value[0]
  
  ssm = boto3.client('ssm', region_name=region_name)
  param_name = '/deployer/%s/default-vpc' % stack_name 
  
  try:
    response = ssm.put_parameter(
      Name=param_name,
      Description='Specifies the default vpc for the stack deployment.',
      Overwrite=True,
      Type='String',
      Value=param_value)
  except Exception as error:
    print('Unable to put_parameter(%s) = %s' % (param_name, param_value))
    raise error

if __name__ == '__main__':
  '''
  Debug the local run...
  '''
  if XRAY_AVAILABLE:
    xray_recorder.begin_segment('LocalDebug')

  function_main(
    event={
      "template_path": "https://disaster-recovery.wellarchitectedlabs.com/Reliability/Disaster%20Recovery/Workshop_1/US-East-1-Deployment/_index.en.files/BackupAndRestore.yaml",
      "stack_name": "Debug",
      "region_name": "us-east-1",
      "wait_handle": "http://google.com",
      "parameters": {}
    },
    context={
    })
