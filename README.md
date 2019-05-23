# Amazon API Gateway Mutating Webhook For K8S
This demo project is intend to illustrate how to use [Amazon API Gateway](https://aws.amazon.com/api-gateway/) and [AWS Lambda](https://aws.amazon.com/lambda/) to setup a HTTP service, then been integrated with Kubernetes as [admission webhooks](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/) to receive admission requests and mutate or validate Kubernetes resources dynamically. Particularly this project will setup a mutating webhook to modify the docker image path in K8S Pod after the deployment been submitted to K8S API server and before it been persisted in etcd.

## Use cases
- The same k8s cluster need to be deployed and use different docker registry, for example k8s cluster deployed in AWS Oregon and Singapore region, and use ECR registry in local region.
- Due to firewall or security restriction, public registry cannot be accessed and need to modify the image path to access other mirror repositories.

## How it works
![](./images/solution-diagram.png)
The most famous use case of k8s mutating webhook is the [istio sidecar injector](https://istio.io/docs/reference/commands/sidecar-injector/), you may also reference [K8S documentation](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/) or [3rd-party blog](https://medium.com/dowjones/how-did-that-sidecar-get-there-4dcd73f1a0a4) to get understand how k8s admission works.

This project will setup the API Gateway with Lambda to receive the admission request from k8s API server, you may get k8s Pod spec from "body" object of request payload json object:
```json
{
    "kind": "AdmissionReview",
    "request": {
        "kind": {
            "kind": "Pod",
            "version": "v1",
            "group": ""
        },
        "resource": {
            "resource": "pods",
            "version": "v1",
            "group": ""
        },
        "uid": "b06b6ec2-681d-11e9-a645-06b44ed6a042",
        "object": {
            "status": {},
            "spec": {
                "dnsPolicy": "ClusterFirst",
                "securityContext": {},
                "serviceAccountName": "default",
                "schedulerName": "default-scheduler",
                "serviceAccount": "default",
                "priority": 0,
                "terminationGracePeriodSeconds": 30,
                "restartPolicy": "Always",
                "containers": [
                    {
                        "name": "nginx",
                        "image": "gcr.io/nginx:latest",
                        "imagePullPolicy": "Always",
                        "ports": [
                            {
                                "protocol": "TCP",
                                "containerPort": 80
                            }
                        ],
                        "resources": {}
                    }
                ]
            },
            "metadata": {
            }
        },
        "namespace": "admission-test",
        "userInfo": {
            "username": "system:unsecured",
            "groups": [
                "system:masters",
                "system:authenticated"
            ]
        },
        "oldObject": null,
        "dryRun": false,
        "operation": "CREATE"
    },
    "apiVersion": "admission.k8s.io/v1beta1"
}
```
then the response of webhook(API Gateway with Lambda) is like this:
```json
{
    "body": {
    "response": {
        "allowed": "True",
        "patch": "patch_base64",
        "patchType": "JSONPatch"
    },
    "headers": {
      "Content-Type": "application/json"
    },
    "statusCode": 200
}
```
where the patch_base64 is base64 encoded of [JSON Patch](http://jsonpatch.com/), for example:
```json
[
    {
        "op": "replace",
        "path": "/spec/containers/0/image",
        "value": "xxxx.dkr.ecr.us-west-2.amazonaws.com/nginx:latest"
    }
]
```
JSON patch will be applied to the Pod spec and then persisted into etcd.

## How to deploy
### Prerequisites
- Ensure that the Kubernetes cluster is at least as new as v1.9.
- Ensure that MutatingAdmissionWebhook admission controllers are enabled.
- Ensure that the admissionregistration.k8s.io/v1beta1 API is enabled.

Amazon EKS has been enabled MutatingAdmissionWebhook.
### Steps to set up admission webhook with API Gateway and Lambda:
1. Deploy K8S cluster, you may use [eksctl](https://eksctl.io/) to setup EKS clusters with worker nodes as well.
2. Deploy webhook server, create new CloudFormation with template api-gateway.yaml
3. Create k8s MutatingWebhookConfiguration resource
    - Find APIGateWayURL from the CloudFormation outputs in previous step.
    - Modify mutating-webhook.yaml，replace <WEB-HOOK-URL> with the value of APIGateWayURL
    - Create K8S resource:
        ```bash
        $ kubectl apply -f mutating-webhook.yaml
        ```
4. Deploy sample k8s deployment
    ```bash
    $ kubectl apply -f ./nginx-gcr.yaml
    ```
5. Check the image path 
    ```bash
    $ kubectl get pod nginx-gcr-deployment-784bf76d96-hjmv4 -o=jsonpath='{.spec.containers[0].image}'
    asia.gcr.io/nginx
    ```
    you may noticed the image path has been changed from "gcr.io/nginx" to "asia.gcr.io/nginx"

## License Summary

This sample code is made available under the MIT-0 license. See the LICENSE file.
