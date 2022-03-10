import boto3
from json import dumps

def function_main(event:dict, context:dict)->dict:
  '''
  Checks the status of a CloudFormation stack.

  Known Status:
    'CREATE_IN_PROGRESS'|'CREATE_FAILED'|'CREATE_COMPLETE'|
    'ROLLBACK_IN_PROGRESS'|'ROLLBACK_FAILED'|'ROLLBACK_COMPLETE'|
    'DELETE_IN_PROGRESS'|'DELETE_FAILED'|'DELETE_COMPLETE'|
    'UPDATE_IN_PROGRESS'|'UPDATE_COMPLETE_CLEANUP_IN_PROGRESS'|
    'UPDATE_COMPLETE'|'UPDATE_FAILED'|'UPDATE_ROLLBACK_IN_PROGRESS'|
    'UPDATE_ROLLBACK_FAILED'|'UPDATE_ROLLBACK_COMPLETE_CLEANUP_IN_PROGRESS'|
    'UPDATE_ROLLBACK_COMPLETE'|'REVIEW_IN_PROGRESS'|
    'IMPORT_IN_PROGRESS'|'IMPORT_COMPLETE'|'IMPORT_ROLLBACK_IN_PROGRESS'|'IMPORT_ROLLBACK_FAILED'|'IMPORT_ROLLBACK_COMPLETE',

  https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudformation.html#CloudFormation.Client.describe_stacks
  '''
  print(dumps(event))

  assert 'region_name' in event, "missing region_name"
  assert 'stack_name' in event, "missing stack_name"

  region_name:str = event['region_name']
  stack_name:str = event['stack_name']

  client = boto3.client('cloudformation',region_name=region_name)
  try:
    response = client.describe_stacks(
      StackName=stack_name,
    )
  except Exception as error:
    print(str(error))
    raise error

  status = [x['StackStatus'] for x in response['Stacks']]
  if len(status) == 0:
    return {'status': 'CREATE_NOT_STARTED' }
  if len(status) == 1:
    return {'status': status[0] }
  else:
    raise NotImplementedError('This is not expected...')

if __name__ == '__main__':
  '''
  Debug the local run...
  '''
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
