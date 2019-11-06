from errbot import BotPlugin, botcmd
from kubernetes import client, config

class K8sPlugin(BotPlugin):

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
