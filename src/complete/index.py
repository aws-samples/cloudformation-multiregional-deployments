import requests
from json import dumps
from requests.models import CaseInsensitiveDict

def function_main(event:dict, _:dict)->dict:
  '''
  Signals the WaitHandle that the step function is complete.

  https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-waitcondition.html
  '''
  print(dumps(event))

  assert 'stack_name' in event, "missing stack_name"
  assert 'wait_handle' in event, "missing wait_handle"
  
  stack_name = event['stack_name']
  wait_handle = event['wait_handle']
  
  status = 'SUCCESS'
  if 'error' in event:
    status='FAILURE'

  data = {
    "Status" : status,
    "Reason" : "Configuration Complete",
    "UniqueId" : stack_name,
    "Data" : "Application has completed configuration."
  }

  print(dumps(data))
  headers=CaseInsensitiveDict()
  headers['Accept'] = 'application/json'
  headers['Content-Type'] = 'application/json'

  result = requests.put(wait_handle,headers=headers, data=dumps(data))
  print(result)

if __name__ == '__main__':
  '''
  Debug the local run...
  '''
  function_main(
    event={
      "template_path": "https://ee-assets-prod-us-east-1.s3.amazonaws.com/modules/630039b9022d4b46bb6cbad2e3899733/v1/PilotLightDR.yaml",
      "stack_name": "Pilot-Primary23",
      "region_name": "us-west-1",
      "parameters": {
        "IsPrimary": "yes"
      },
      "wait_handle": "https://cloudformation-waitcondition-us-east-1.s3.amazonaws.com/arn%3Aaws%3Acloudformation%3Aus-east-1%3A581361757134%3Astack/DrDeployer/de66a350-17e9-11ec-b9d0-1210cfc0f859/WaitHandlePilotLight?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20210923T175050Z&X-Amz-SignedHeaders=host&X-Amz-Expires=86399&X-Amz-Credential=AKIAIIT3CWAIMJYUTISA%2F20210923%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Signature=bb04cf3fc93f5becf7ae78e4f103f107f4b978b26c2c1fa78905fc0d0cd536cb"
    },
    context={
    })