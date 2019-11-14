from errbot import BotPlugin, botcmd
from kubernetes import client, config, watch


class K8sPlugin(BotPlugin):

    POD_MONITOR_VERBOSITY = "all"
    POD_MONITOR_SUBSCRIBERS = []
    NAMESPACE_MONITOR_VERBOSITY = "all"
    NAMESPACE_MONITOR_SUBSCRIBERS = []

    def activate(self):
        super().activate()
        self.start_poller(15, self.pod_watcher)
        self.start_poller(15, self.namespace_watcher)

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

    @botcmd
    def list_pods(self, msg, args):
        config.load_kube_config()
        v1 = client.CoreV1Api()
        yield("Listing pods with their IPs:")
        ret = v1.list_pod_for_all_namespaces(watch=False)
        for i in ret.items:
            yield("%s\t%s\t%s" % (i.status.pod_ip,
                                  i.metadata.namespace,
                                  i.metadata.name))
