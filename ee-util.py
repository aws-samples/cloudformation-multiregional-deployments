#!/usr/bin/env python3
#########################################################
# Fix the parameters so the cloudformation template works with 
#   Event Engine.
#########################################################
from os import environ
from json import loads,dumps
from sys import stdin

def get_asset_bucket()->str:
  '''
  Determines what bucket to use.
  '''
  bucket = environ.get('TEMPLATE_ASSET_BUCKET')
  if not bucket is None:
    return bucket

  bucket = environ.get('S3_ASSET_BUCKET')
  if not bucket is None:
    return bucket

  raise ValueError('Missing env TEMPLATE_ASSET_BUCKET and S3_ASSET_BUCKET')

with open('cdk.out/CfnMultiRegionOrchestrator.template.json','rt') as f:
  content = loads(f.read()) #stdin.read())

parameters:dict = content['Parameters']
for key in parameters.keys():
  key:str = key
  if not key.startswith('AssetParameters'):
    continue

  if 'Bucket' in key:
    parameters[key]['Default'] = get_asset_bucket()
  elif 'ArtifactHash' in key:
    start=len('AssetParameters')
    end=key.index('ArtifactHash')
    parameters[key]['Default'] = key[start:end] 
  elif 'VersionKey' in key:
    start=len('AssetParameters')
    end=key.index('S3VersionKey')
    sha = key[start:end]
    parameters[key]['Default'] = '%s/||asset.%s.zip' % (environ.get('S3_ASSET_PREFIX'), sha)
  else:
    print('ignoring %s' % key)

with open('cdk.out/EventEngine.template.json', 'w') as f:
  f.write(dumps(content, indent=2))
