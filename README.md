# Kubernetes Plugin
Kubernetes utilities through an Errbot plugin!

The K8s Plugin is a tool created to be used with the Errbot backend. It allows
you to interact with your Kubernetes environment using your chat tool.

Tested on:
* Slack backend


## Commands available
* delete namespace - Delete a namespace.
* delete pod - Delete a pod. You need to pass the pode name and can (but don't need
* list contexts - List all contexts from your Kubernetes clusters.
* list namespaces - List namespaces from a given context (if passed) or from all contexts.
* list pods - List pods from all namespaces from a given context (if passed) or
* monitor namespaces - Start or stop monitoring namespaces for this users.
* monitor pods - Start or stop monitoring pods for this users.
* monitor status - Output the monitor tasks the user are signed to.
* namespace monitoring verbosity - Set the verbosity of the namespace monitoring task.
* pod monitoring verbosity - Set the verbosity of the pod monitoring task.
* start watchers - Start Pod and Namespace monitoring tasks.
* stop watchers - Stop Pod and Namespace monitoring tasks.

## User config

Each bot user will have it's own config. The available config parameters can be
checked bellow.

```
"@username": {
    "namespace": "default",
    "monitoring": ["pod1", "pod2"]
    "verbosity": "error"
}
```

* The `namespace` value set in the config will be used by all commands from the
 bot, if a specific namespace is not passed by the user with the command.
