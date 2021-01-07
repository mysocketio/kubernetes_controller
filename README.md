# kubernetes_controller
Kubernetes controller for Mysocket.io
For details, also see this blog https://www.mysocket.io/post/global-load-balancing-with-kubernetes-and-mysocket

Make sure to update line 14,15 and 16 of mysocketd.yaml with the correct mysocket credentials. 

Then deploy the controller:

```kubectl apply -f mysocketd.yaml```

After the controller is installed, simply add the following annotation to your _Service_ to make it globably available via mysocket.io
```
kind: Service
metadata:
  annotations:
    mysocket.io/enabled: "true"
```

keep an eye on the contoller log files:

```kubectl logs -n mysocket -f <mysocketd-pod>```

Things to keep in mind:
This is an MVP, it currently has the following know limitations:

1) only one contoller pod is running at a time. 
2) the controller only picks up RSA keys for now
