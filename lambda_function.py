import json
import base64

image_mirrors = {
  'gcr.io/': 'asia.gcr.io/',
  'k8s.gcr.io/': 'asia.gcr.io/google-containers/'
}

def handler(event, context):
  request_body = json.loads(event['body'])
  json_patch = []

  # get initContainers from request and replace image path with JSON Patch
  initContainers = dict_get(request_body, 'request.object.spec.initContainers')
  if initContainers:
    json_patch += image_patch(initContainers, '/spec/initContainers')

  # get containters from request and replace image path with JSON Patch
  containers = dict_get(request_body, 'request.object.spec.containers')
  if containers:
    json_patch += image_patch(containers, '/spec/containers')

  print(json.dumps(json_patch))
  # set response body
  patch_b64 = base64.b64encode(json.dumps(json_patch))
  response_body = {
    'response': {
      'allowed': True,
      'patch': patch_b64,
      'patchType': 'JSONPatch'
    }
  }
  
  return {
    'body': json.dumps(response_body),
    'headers': {
      'Content-Type': 'application/json'
    },
    'statusCode': 200
  }

def dict_get(dictionary, keys, default=None):
  return reduce(lambda d, key: d.get(key, default) if isinstance(d, dict) else default, keys.split("."), dictionary)

def image_patch(containers, path_prefix):
  json_patch = []
  for idx, container in enumerate(containers):
    image = container['image']
    for orig_image, mirror_image in image_mirrors.iteritems():
      if image.startswith(orig_image):
        image = mirror_image + image[len(orig_image):]
        json_patch.append({'op': 'replace', 'path': '%s/%d/image' % (path_prefix, idx), 'value': image})
  return json_patch