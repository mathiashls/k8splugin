from errbot import BotPlugin, botcmd
from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException


class K8sPlugin(BotPlugin):

    WATCHER_VERBOSITY = ["all", "error"]
    DEFAULT_CONFIG = {"namespace": "default",
                      "monitoring": [],
                      "verbosity": "all"}

    def activate(self):
        super().activate()
        with self.mutable("subscribers") as d:
            self.subscribers = d
        self.start_poller(15, self.pod_watcher)

    def callback_stream(self, stream):
        self.send(stream.identifier, "File request from: " + str(stream.identifier))
        stream.accept()
        self.send(stream.identifier, "Content:" + str(stream.fsource.read()))

    def pod_watcher(self):
        config.load_kube_config()
        v1 = client.CoreV1Api()
        w = watch.Watch()
        for event in w.stream(v1.list_pod_for_all_namespaces):
            pod_name = event['object'].metadata.name
            for sub in self.subscribers:
                with self.mutable(sub) as d:
                    if pod_name in d["monitoring"]:
                        send_to = self.build_identifier(sub)
                        self.send(send_to, "Event: %s %s %s (Status: %s)" % (event['type'],
                                                                             event['object'].kind,
                                                                             pod_name,
                                                                             event['object'].status.phase))

    def validate_config(self, user):
        send_to = self.build_identifier(user)
        if not self[user]:
            self.send(send_to, f"Creating default config for {user}")
            new_cfg = {"namespace": "default",
                       "monitoring": [],
                       "verbosity": "all"}
            self[user] = new_cfg

    @botcmd(split_args_with=None)
    def set_verbosity(self, msg, args):
        """
        Set the verbosity of the pod monitoring task.
        """
        person = msg.frm.person
        self.validate_config(person)

        if not args or args[0] not in ["all", "warn", "error"]:
            yield "Can't understand, sorry!"
            return
        level = args[0]
        yield f"Set {person} verbosity level for pod monitoring to {level}"
        with self.mutable(person) as d:
            d["verbosity"] = level

    @botcmd(split_args_with=None)
    def set_namespace(self, msg, args):
        """
        Set the namespace for the user.
        """
        person = msg.frm.person
        self.validate_config(person)

        config.load_kube_config()
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

        yield f"Set {person} namespace to {namespace_name}"
        with self.mutable(person) as d:
            d["namespace"] = namespace_name

    @botcmd
    def get_config(self, msg, args):
        """
        Get user config
        """
        person = msg.frm.person
        self.validate_config(person)
        ns = self[person]["namespace"]
        pods = self[person]["monitoring"]
        verb = self[person]["verbosity"]
        yield f""" User: {person}
        Namespace: {ns}
        Monitoring pods: {pods}
        Verbosity: {verb}
        """


    @botcmd(split_args_with=None)
    def monitor_pod(self, msg, args):
        """
        Start monitoring given pod.
        """
        person = msg.frm.person
        self.validate_config(person)

        if not args:
            yield "No pod name passed!"

        pod_name = args[0]
        v1 = client.CoreV1Api()
        all_pods = v1.list_pod_for_all_namespaces(watch=False)
        if pod_name not in [info.metadata.name for info in all_pods.items]:
            yield "Invalid pod name!"
            return

        yield f"{person} will start monitoring {pod_name}"
        with self.mutable(person) as d:
            d["monitoring"].append(pod_name)
            if person not in self.subscribers:
                self.subscribers.append(person)

        self["subscribers"] = self.subscribers

    @botcmd(split_args_with=None)
    def unmonitor_pod(self, msg, args):
        """
        Stop monitoring given pod.
        """
        person = msg.frm.person
        self.validate_config(person)

        if not args:
            yield "No pod name passed!"

        pod_name = args[0]

        yield f"{person} will stop monitoring {pod_name}"
        with self.mutable(person) as d:
            if pod_name in d["monitoring"]:
                d["monitoring"].remove(pod_name)
            if len(d["monitoring"]) == 0 and person in self.subscribers:
                self.subscribers.remove(person)

        self["subscribers"] = self.subscribers

    @botcmd
    def monitor_status(self, msg, args):
        """
        Output monitor info for the user.
        """
        person = msg.frm.person
        self.validate_config(person)

        with self.mutable(person) as d:
            monitoring = d["monitoring"]
            verbosity = d["verbosity"]
            yield f"Monitoring pods {monitoring} with verbosity {verbosity}"

    @botcmd(split_args_with=None)
    def list_pods(self, msg, args):
        """
        List pods from all namespaces from a given context (if passed) or
        from all contexts.
        """
        person = msg.frm.person
        self.validate_config(person)
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

        ns = self[person]["namespace"]
        config.load_kube_config(context=context)
        v1 = client.CoreV1Api()
        yield f"Listing pods from namespace {ns}"
        ret = v1.list_namespaced_pod(namespace=ns)
        for i in ret.items:
            yield "* %s" % (i.metadata.name)

    @botcmd(split_args_with=None)
    def list_all_pods(self, msg, args):
        """
        List pods from all namespaces from a given context (if passed) or
        from all contexts.
        """
        person = msg.frm.person
        self.validate_config(person)
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
        yield "Listing pods from all namespaces:"
        ret = v1.list_pod_for_all_namespaces(watch=False)
        for i in ret.items:
            yield("* %s [ns: %s]" % (i.metadata.name, i.metadata.namespace))

    @botcmd(split_args_with=None)
    def list_namespaces(self, msg, args):
        """
        List namespaces from a given context (if passed) or from all contexts.
        """
        person = msg.frm.person
        self.validate_config(person)
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
        """
        List all contexts from your Kubernetes clusters.
        """
        person = msg.frm.person
        self.validate_config(person)
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
        Delete a pod. You need to pass the pod name. If namespace is not
        passed, the namespace from user config will be used.
        Use: delete pod [pod_name] [namespace_name]
        """
        person = msg.frm.person
        self.validate_config(person)
        config.load_kube_config()
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
            try:
                pod_name = args[0]
                ns_name = self[person]["namespace"]
            except:
                yield f"No namespace passed and no namespace configured for user {person}"
                return

        if pod_name not in pods_info:
            yield "Invalid pod name, sorry!"
            return
        elif ns_name and pods_info[pod_name][0] != ns_name:
            yield "The namespace used doesn't match the namespace from the pod (%s != %s). Aborting to avoid problems." % (pods_info[pod_name], ns_name)
            return

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
        person = msg.frm.person
        self.validate_config(person)

        config.load_kube_config()
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

    @botcmd(split_args_with=None)
    def pod_status(self, msg, args):
        person = msg.frm.person
        self.validate_config(person)

        config.load_kube_config()
        v1 = client.CoreV1Api()

        try:
            pod = args[0]
            namespace = self[person]["namespace"]
            response = v1.read_namespaced_pod_status(pod, namespace)
            status = response.status.phase
            name = response.metadata.name
            namespace = response.metadata.namespace
            yield f"Pod {name} from namespace {namespace} is now {status}"

        except ApiException as error:
            yield f"Error trying to read pod status: {error}"
