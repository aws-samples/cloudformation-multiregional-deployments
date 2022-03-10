#!/usr/bin/env python3
from os import PathLike, mkdir, path
from posix import listdir
from typing import Any, Mapping, List
from json import dumps, loads
from aws_cdk import (
  core,
  aws_cloudformation as cf,
  aws_iam as iam,
  aws_lambda as lambda_,
  aws_stepfunctions as sf,
  aws_stepfunctions_tasks as sft,
  custom_resources as cr,
)

root_directory = path.dirname(__file__)
job_definition_directory = path.join(root_directory,'job-definitions')
bin_directory = path.join(root_directory, "bin")
cdkout_directory = path.join(root_directory,"cdk.out")

if not path.exists(cdkout_directory):
  mkdir(cdkout_directory)

class JobDefinitionStep:
  '''
  Represents an individual deployment step.
  '''
  def __init__(self, file_name:str, props:Mapping[str,Any]) -> None:
    assert not file_name is None, "JobDefinitionStep init called without fileName"
    assert not props is None, "JobDefinitionStep init called without props"
    self.__props = props
    self.__file_name = file_name

  @property
  def file_name(self)->str:
    '''
    Gets the name of the file that declares this JobDefinitionStep.
    '''
    return self.__file_name

  @property
  def template_path(self)->str:
    '''
    Gets the name of the AWS CloudFormation template implementing this step.
    '''
    return self.assert_get_property('templatePath')

  @property
  def stack_name(self)->str:
    '''
    Gets the desired Cfn Stack Name for this step.
    '''
    return self.assert_get_property('stackName')

  @property
  def region_name(self)->str:
    '''
    Gets the target region to deploy this step.
    '''
    return self.assert_get_property('regionName') 

  @property
  def parameters(self)->Mapping[str,str]:
    '''
    Gets the parameter set for this JobDefinitionSteps Cfn Stack.
    '''
    if not "parameters" in self.__props:
      return {}
    return self.__props['parameters']

  def to_inputRequest(self)->Mapping[str,Mapping[str,Any]]:
    '''
    Encodes this JobDefinitionStep for the Step Function's orchestration.
    '''
    return {
      "inputRequest":{
        "template_path": self.template_path,
        "stack_name": self.stack_name,
        "region_name": self.region_name,
        "parameters": self.parameters
      }
    }

  def assert_get_property(self, property_name:str)->Any:
    '''
    Confirm the property exists and return it. 
    '''
    assert property_name in self.__props, "File {file} is missing property {property} in {struct}".format(
      file=self.file_name,
      property = property_name,
      struct = str(self.__props)
    )

    return self.__props[property_name]

class JobDefinition:
  '''
  Represents the job definition file containing JobDefinitionStep(s). 
  '''
  def __init__(self, fileName:PathLike) -> None:
    assert not fileName is None, "Missing fileName"
    self.__file_name = fileName

    if not path.exists(fileName):
      print('The specified file does not exit - %s' % fileName)
      raise FileNotFoundError(fileName)

    with open(fileName,'r') as f:
      self.__props = loads(f.read())

  @property
  def file_name(self)->str:
    '''
    Gets the file that declares this resource.
    '''
    return self.__file_name

  @property
  def module_name(self)->str:
    '''
    Gets the name of this deployment module set.
    '''
    return self.assert_get_property('moduleName')

  @property
  def timeout(self)->str:
    '''
    Gets the module deployment timeout (in seconds)
    '''
    if not 'timeout' in self.__props:
      return "3600"
    return str(self.__props['timeout'])

  @property
  def description(self)->str:
    '''
    Gets a user-friendly description of this module.
    '''
    if not 'description' in self.__props:
      return "Creates the %s environment" % self.module_name
    return self.__props['description']
  
  @property
  def stacks(self)->List[JobDefinitionStep]:
    '''
    Gets an ordered list of stacks to deploy.
    '''
    stacks = self.assert_get_property('stacks')
    return [JobDefinitionStep(self.file_name, x) for x in stacks]

  def assert_get_property(self,property_name:str)->Any:
    '''
    Confirms the property exists and returns it.
    '''
    assert property_name in self.__props, "File {file} is missing property '{property_name}' - {struct}".format(
      file=self.file_name,
      property_name=property_name,
      struct=str(self.__props))
    
    return self.__props[property_name]

class Functions(core.Construct):
  '''
  Creates the deployment Step Function's backing Lambda functions.
  '''
  def __init__(self, scope: core.Construct, id:str)->None:
    super().__init__(scope,id)
    
    self.preaction_function = lambda_.Function(self,'Preaction',
      function_name='Prepare-Stack',
      code = Functions.get_lambda_code("preaction"),
      timeout=core.Duration.minutes(1),
      tracing= lambda_.Tracing.ACTIVE,
      runtime= lambda_.Runtime.PYTHON_3_9,
      handler='index.function_main')

    self.launch_function = lambda_.Function(self,'Launch',
      function_name='Create-Stack_Task',
      code = Functions.get_lambda_code("launch"),
      timeout=core.Duration.minutes(1),
      tracing= lambda_.Tracing.ACTIVE,
      runtime= lambda_.Runtime.PYTHON_3_9,
      handler='index.function_main')

    self.monitor_function = lambda_.Function(self,'Monitor',
      function_name='Get-StackStatus_Task',
      code = Functions.get_lambda_code("monitor"),
      timeout=core.Duration.minutes(1),
      tracing= lambda_.Tracing.ACTIVE,
      runtime= lambda_.Runtime.PYTHON_3_9,
      handler='index.function_main')

    self.complete_functon = lambda_.Function(self,'Complete',
      function_name='Signal-Complete_Task',
      code = Functions.get_lambda_code("complete"),
      timeout=core.Duration.minutes(1),
      tracing= lambda_.Tracing.ACTIVE,
      runtime= lambda_.Runtime.PYTHON_3_9,
      handler='index.function_main')

    '''
    Grant any permissions necessary here.
    '''
    for fn in [self.launch_function, self.monitor_function]:
      fn.role.add_managed_policy(
        iam.ManagedPolicy.from_aws_managed_policy_name('AWSCloudFormationFullAccess'))

    for fn in [self.launch_function, self.monitor_function, self.complete_functon]:
      self.monitor_function.role.add_managed_policy(
        iam.ManagedPolicy.from_aws_managed_policy_name('AWSXRayDaemonWriteAccess'))

    self.launch_function.role.add_managed_policy(
      iam.ManagedPolicy.from_aws_managed_policy_name('AdministratorAccess'))

    self.preaction_function.role.add_managed_policy(
      iam.ManagedPolicy.from_aws_managed_policy_name('AdministratorAccess'))

  @staticmethod 
  def get_lambda_code(lambda_name:str)-> lambda_.Code:
    '''
    Gets the correct package for rootdir\\src\\name.
    '''
    fileName = path.join(bin_directory,lambda_name+'.zip')
    if path.exists(fileName):
      return lambda_.Code.from_asset(fileName)

    fileName = path.join(root_directory,"src",lambda_name, "index.py")
    if path.exists(fileName):
      with open(fileName, "r") as f:
        return lambda_.Code.from_inline(f.read())
    
    raise FileNotFoundError("Unable to find lambda_code for %s" % lambda_name)

class DeploymentWorkflow(core.Construct):
  '''
  Represents the AWS Step Function that orchestrates the deployment.
  '''
  def __init__(self, scope: core.Construct, id: str) -> None:
    super().__init__(scope, id)

    self.functions = Functions(self,'Functions')

    before_creation = sft.LambdaInvoke(self,'Before-StackCreation',
      lambda_function= self.functions.preaction_function,
      input_path='$.inputRequest',
      result_path='$.preaction')

    create_stack = sft.LambdaInvoke(self,'Create-Stack',
      lambda_function= self.functions.launch_function,
      input_path='$.inputRequest',
      result_path='$.createStack')

    monitor_stack = sft.LambdaInvoke(self,'Get-StackStatus',
      lambda_function= self.functions.monitor_function,
      input_path='$.inputRequest',
      result_path='$.monitor')

    create_stack.next(monitor_stack)

    delay = sf.Wait(self,'Sleep',time= sf.WaitTime.duration(core.Duration.seconds(30)))
    delay.next(monitor_stack)

    complete_job = sft.LambdaInvoke(self,'Signal-Completion',
      lambda_function= self.functions.complete_functon,
      result_path='$.signal',
      input_path='$.inputRequest')

    set_error_info = sf.Pass(self,'Set-ErrorInfo',
      parameters={
        'inputRequest.$': '$.inputRequest',
        'inputRequest.error.$':'$.monitor.Payload',
        'is_error': True
      })

    set_error_info.next(complete_job)

    check_complete = sf.Choice(self,'Assess-Status')
    check_complete.when(
      sf.Condition.or_(
        sf.Condition.string_equals("$.monitor.Payload.status", 'CREATE_COMPLETE'),
        sf.Condition.string_equals("$.monitor.Payload.status", 'UPDATE_COMPLETE')),
      complete_job)
    check_complete.when(
      sf.Condition.or_(        
        sf.Condition.string_equals('$.monitor.Payload.status','ROLLBACK_FAILED'),
        sf.Condition.string_equals('$.monitor.Payload.status','ROLLBACK_IN_PROGRESS'),
        sf.Condition.string_equals('$.monitor.Payload.status','ROLLBACK_COMPLETE'),
        sf.Condition.string_equals('$.monitor.Payload.status','UPDATE_ROLLBACK_COMPLETE'),
        sf.Condition.string_equals('$.monitor.Payload.status','UPDATE_ROLLBACK_FAILED'),
        sf.Condition.string_equals('$.monitor.Payload.status','CREATE_FAILED'),
        sf.Condition.string_equals('$.monitor.Payload.status','UPDATE_FAILED')), 
      set_error_info)
    check_complete.otherwise(delay)

    monitor_stack.next(check_complete)

    '''
    Bubble up any error info
    '''
    terminal_state= sf.Succeed(self,'Ready')
    is_success = sf.Choice(self,'Is-Success')
    is_success.when(
      sf.Condition.is_not_present('$.is_error'),
      terminal_state)
    is_success.when(
      sf.Condition.boolean_equals('$.is_error',True),
      sf.Fail(self,'Stack-Error',
        error='Failed to create stack.  Please see $.inputRequest.error for details.'))
    is_success.otherwise(terminal_state)
    complete_job.next(is_success)

    '''
    Wrap the whole job in an iterator to support multiple stacks.
    '''
    stack_list = sf.Map(self,'Enumerate-Stacks',
      input_path='$.stacks',
      max_concurrency=1)
    stack_list.iterator(before_creation)
    before_creation.next(create_stack)

    self.state_machine = sf.StateMachine(self,'StateMachine',
      state_machine_name='Cfn-MultiRegion-Orchestrator',
      tracing_enabled=True,
      definition=stack_list)

class CfnMultiRegionOrcheratorStack(core.Stack):
  '''
  Represents the Amazon CloudFormation Stack that contains the deployment tool.
  After deploying the Step Function, the Stack will also deploy every file under `job-definitions`.

  If there are multiple job-definitions files they will each run in parallel. Its declared steps run sequentially.
  '''
  def __init__(self, scope:core.Construct,id:str) -> None:
    super().__init__(scope,id)
    core.Tags.of(self).add('topology','blueprint:cfn-multiregion-orchestration')

    self.deploy_tool = DeploymentWorkflow(self,'Workflow')
    self.provision_everything()
    
  def provision_everything(self):
    '''
    Discovers all job-definitions within the `job-definitions` folder.
    
    Job Definitions launch in parallel and then sequentially process its steps.
    Customers can support more sophisticated deployment graphs with additional CfnWaitConditionHandle(s).
    '''
    for fileName in listdir(job_definition_directory):
      if not fileName.endswith(".json"):
        continue

      fileName = path.join(job_definition_directory, fileName)
      definition = JobDefinition(fileName)
      self.provision(definition)

  def provision(self,job_definition:JobDefinition)->None:
    '''
    Add executing the given JobDefinition during the deployment.
    '''
    wait_handle = cf.CfnWaitConditionHandle(self,'WaitHandle-'+job_definition.module_name)
    
    '''
    Convert the stack creation steps into this format for the step function.
    {
      "inputRequest": {
        "template_path": str
        "stack_name": str
        "region_name": str
        "wait_handle": str
        "parameters": {
          "foo": str,
          "bar": str
        }
      }
    }
    '''
    stacks:List[Mapping[str,Mapping[str,Any]]] = [x.to_inputRequest() for x in job_definition.stacks]
    for stack in stacks:
      stack['inputRequest']['wait_handle'] = wait_handle.ref

    input={
      'stacks': stacks
    }

    '''
    Write the transformed file for troubleshooting
    '''
    with open(path.join(cdkout_directory,path.basename(job_definition.file_name)), "wt") as f:
      f.write(dumps(input,indent=2))

    '''
    AwsSdkCall expects JavaScript naming conventions. 
    https://docs.aws.amazon.com/AWSJavaScriptSDK/latest/AWS/StepFunctions.html#startExecution-property
    '''
    _ = cr.AwsCustomResource(self,'Launch_'+job_definition.module_name,
      policy= cr.AwsCustomResourcePolicy.from_sdk_calls(
        resources=cr.AwsCustomResourcePolicy.ANY_RESOURCE),
      on_create= cr.AwsSdkCall(
        service='StepFunctions',
        action='startExecution',
        physical_resource_id= cr.PhysicalResourceId.of('CreateStack_'+job_definition.module_name),
        parameters={
          'stateMachineArn': self.deploy_tool.state_machine.state_machine_arn,
          'input': input,
        }),
      on_update= cr.AwsSdkCall(
        service='StepFunctions',
        action='startExecution',
        physical_resource_id= cr.PhysicalResourceId.of('CreateStack_'+job_definition.module_name),
        parameters={
          'stateMachineArn': self.deploy_tool.state_machine.state_machine_arn,
          'input': dumps(input),
        })
      )

    core.CfnWaitCondition(self,'WaitCondition_'+job_definition.module_name,
      handle=wait_handle.ref,
      count= len(stacks),
      timeout=job_definition.timeout)

'''
Finally synthize all resources.
'''
app = core.App()
CfnMultiRegionOrcheratorStack(app,'CfnMultiRegionOrchestrator')
app.synth()