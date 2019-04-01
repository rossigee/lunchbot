# Lunchbot

Steve and I go to lunch every Friday. We take it in turns to pay the bill.

Steve and I are forgetful, and can never remember who paid last week.

The rest is code.

# Build/installation/configure

Build:

```
docker build . -t rossigee/lunchbot && \
  docker push rossigee/lunchbot
```

Configure (for K8S deployment):

```
cp k8s-deployment.yml.example k8s-deployment.yml
vi k8s-deployment.yml
# Set your Discord token etc.
```

Deploy (to your K8S cluster):

```
kubectl apply -f k8s-deployment.yml
```
