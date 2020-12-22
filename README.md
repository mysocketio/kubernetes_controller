# kubernetes_controller
Kubernetes controller for Mysocket.io

Make sure to update line 14,15 and 16 of mysocketd.yaml with the correct mysocket credentials. 

Then deploy the controller:

```kubectl apply -f mysocketd.yaml```


Things to keep in mind:
This is an MVP, it currently has the following know limitations:

1) only one contoller pod is running at a time. 
2) the controller only picks up RSA keys for now
