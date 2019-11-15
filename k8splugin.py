from errbot import BotPlugin, botcmd
from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException

import yaml


class K8sPlugin(BotPlugin):

    POD_MONITOR_VERBOSITY = "all"
    POD_MONITOR_SUBSCRIBERS = []
    NAMESPACE_MONITOR_VERBOSITY = "all"
    NAMESPACE_MONITOR_SUBSCRIBERS = []

    def activate(self):
        super().activate()
        self.start_pollers()

    def callback_stream(self, stream):
        self.send(stream.identifier, "File request from: " + str(stream.identifier))
        stream.accept()
        self.send(stream.identifier, "Content:" + str(stream.fsource.read()))

    def start_pollers(self):
        self.start_poller(15, self.pod_watcher)
        self.start_poller(15, self.namespace_watcher)

    def stop_pollers(self):
        self.stop_poller(self.pod_watcher)
        self.stop_poller(self.namespace_watcher)

    @botcmd
    def start_watchers(self, msg, args):
        yield "Starting pod and namespace watchers..."
        self.start_pollers()

    @botcmd
    def stop_watchers(self, msg, args):
        yield "Stopping pod and namespace watchers..."
        self.stop_pollers()

    def namespace_watcher(self):
        config.load_kube_config()
        v1 = client.CoreV1Api()
        w = watch.Watch()
        for event in w.stream(v1.list_namespace):
            for sub in self.NAMESPACE_MONITOR_SUBSCRIBERS:
                send_to = self.build_identifier(sub)
                self.send(send_to, "Event: %s %s" % (event['type'],
                                                     event['object'].metadata.name))

    def pod_watcher(self):
        config.load_kube_config()
        v1 = client.CoreV1Api()
        w = watch.Watch()
        for event in w.stream(v1.list_pod_for_all_namespaces):
            for sub in self.POD_MONITOR_SUBSCRIBERS:
                send_to = self.build_identifier(sub)
                self.send(send_to, "Event: %s %s %s" % (event['type'],
                                                        event['object'].kind,
                                                        event['object'].metadata.name))

    @botcmd(split_args_with=None)
    def pod_monitoring_verbosity(self, msg, args):
        if len(args) != 1 or args[0] not in ["all", "warn", "error"]:
            yield "Can't understand, sorry!"
            return
        level = args[0]
        yield f"Set verbosity level for pod monitoring to {level}"
        self.POD_MONITOR_VERBOSITY = level

    @botcmd(split_args_with=None)
    def namespace_monitoring_verbosity(self, msg, args):
        if len(args) != 1 or args[0] not in ["all", "warn", "error"]:
            yield "Can't understand, sorry!"
            return
        level = args[0]
        yield f"Set verbosity level for namespace monitoring to {level}"
        self.NAMESPACE_MONITOR_VERBOSITY = level

    @botcmd(split_args_with=None)
    def monitor_namespaces(self, msg, args):
        if len(args) != 1 or args[0] not in ["start", "stop"]:
            yield "Can't understand, sorry!"
            return

        person = msg.frm.person
        action = args[0]

        if action == "start":
            if person in self.NAMESPACE_MONITOR_SUBSCRIBERS:
                yield f"Hey {person}, you are already monitoring the namespaces"
            else:
                yield f"Ok, {person}, I'll send you all infos about your namespaces"
                self.NAMESPACE_MONITOR_SUBSCRIBERS.append(person)
        elif action == "stop":
            if person not in self.NAMESPACE_MONITOR_SUBSCRIBERS:
                yield f"Hey {person}, you are not monitoring the namespaces"
            else:
                yield f"Ok then, you will stop receiving info from namespaces"
                self.NAMESPACE_MONITOR_SUBSCRIBERS.remove(person)

    @botcmd(split_args_with=None)
    def monitor_pods(self, msg, args):
        if len(args) != 1 or args[0] not in ["start", "stop"]:
            yield "Can't understand, sorry!"
            return

        person = msg.frm.person
        action = args[0]

        if action == "start":
            if person in self.POD_MONITOR_SUBSCRIBERS:
                yield f"Hey {person}, you are already monitoring the pods"
            else:
                yield f"Ok, {person}, I'll send you all infos about your pods"
                self.POD_MONITOR_SUBSCRIBERS.append(person)
        elif action == "stop":
            if person not in self.POD_MONITOR_SUBSCRIBERS:
                yield f"Hey {person}, you are not monitoring the pods"
            else:
                yield f"Ok then, you will stop receiving info from pods"
                self.POD_MONITOR_SUBSCRIBERS.remove(person)

    @botcmd
    def monitor_status(self, msg, args):
        person = msg.frm.person
        monitoring = []
        if person in self.POD_MONITOR_SUBSCRIBERS:
            monitoring.append("Pods")
        if person in self.NAMESPACE_MONITOR_SUBSCRIBERS:
            monitoring.append("Namespaces")
        if not monitoring:
            monitoring.append("Nothing... cuen")
        yield "You are currently monitoring:"
        for item in monitoring:
            yield  f"* {item}"

    @botcmd(split_args_with=None)
    def list_pods(self, msg, args):
        """
        List pods from all namespaces from a given context (if passed) or
        from all contexts.
        """
        if args:
            context = args[0]
            contexts, _ = config.list_kube_config_contexts()
            contexts = [context['name'] for context in contexts]
            if context not in contexts:
                yield f"Invalid context name ({context}), listing pods from all contexts."
                context = None
            else:
                yield f"Ok, will use context {context}"
        else:
            context = None

        config.load_kube_config(context=context)
        v1 = client.CoreV1Api()
        yield "Listing pods with their IPs:"
        ret = v1.list_pod_for_all_namespaces(watch=False)
        for i in ret.items:
            yield("* %s [Namespace: %s, IP: %s]" % (i.metadata.name,
                                                    i.metadata.namespace,
                                                    i.status.pod_ip))

    @botcmd(split_args_with=None)
    def list_namespaces(self, msg, args):
        """
        List namespaces from a given context (if passed) or from all contexts.
        """
        if args:
            context = args[0]
            contexts, _ = config.list_kube_config_contexts()
            contexts = [context['name'] for context in contexts]
            if context not in contexts:
                yield f"Invalid context name ({context}), listing pods from all contexts."
                context = None
            else:
                yield f"Ok, will use context {context}"
        else:
            context = None

        config.load_kube_config(context=context)
        v1 = client.CoreV1Api()
        yield "Listing namespaces:"
        ret = v1.list_namespace()
        for i in ret.items:
            yield("%s [%s]" % (i.metadata.name, i.status._phase))

    @botcmd
    def list_contexts(self, msg, args):
        contexts, _ = config.list_kube_config_contexts()
        if not contexts:
            yield "No context was found :("
            return
        yield "Here are the contexts:"
        for context in contexts:
            name = context["name"]
            cluster = context["context"]["cluster"]
            user = context["context"]["user"]
            yield f"* {name} (Cluster: {cluster} / User: {user})"

    @botcmd(split_args_with=None)
    def delete_pod(self, msg, args):
        """
        Delete a pod. You need to pass the pode name and can (but don't need
        to) pass the namespace name.
        Use: delete pod [pod_name] [namespace_name]
        """
        v1 = client.CoreV1Api()
        all_pods = v1.list_pod_for_all_namespaces(watch=False)
        pods_info = {}
        for info in all_pods.items:
            pods_info.setdefault(info.metadata.name, [])
            pods_info[info.metadata.name].append(info.metadata.namespace)

        if not args:
            yield "Arguments are missing. Try again!"
            return
        elif len(args) == 2:
            pod_name = args[0]
            ns_name = args[1]
        else:
            pod_name = args[0]
            ns_name = None

        if pod_name not in pods_info:
            yield "Invalid pod name, sorry!"
            return
        elif not ns_name and len(pods_info[pod_name]) > 1:
            yield "We found pods in different namespaces with this name... You will need to specify the namespace in the command!"
            return
        elif ns_name and pods_info[pod_name][0] != ns_name:
            yield "The namespace you passed doesn't match the namespace from the pod (%s != %s). Aborting to avoid problems." % (pods_info[pod_name], ns_name)
            return

        if len(pods_info[pod_name]) == 1:
            ns_name = pods_info[pod_name][0]

        try:
            delete_options = client.V1DeleteOptions()
            api_response = v1.delete_namespaced_pod(name=pod_name,
                                                    namespace=ns_name,
                                                    body=delete_options)
            yield api_response
        except ApiException as e:
            yield "Exception when trying to delete pod: %s" % e

    @botcmd(split_args_with=None)
    def delete_namespace(self, msg, args):
        """
        Delete a namespace.
        """
        v1 = client.CoreV1Api()
        namespaces = v1.list_namespace(watch=False)

        if not args:
            yield "Arguments are missing. Try again!"
            return
        else:
            namespace_name = args[0]

        if namespace_name not in [ns.metadata.name for ns in namespaces.items]:
            yield "Invalid namespace, sorry!"
            return

        try:
            delete_options = client.V1DeleteOptions()
            api_response = v1.delete_namespace(name=namespace_name,
                                               body=delete_options)
            yield api_response
        except ApiException as e:
            yield "Exception when trying to delete namespace: %s" % e
