from typing import Dict, List

from fabfed.util.constants import Constants
from fabfed.exceptions import StitchPortNotFound
from collections import namedtuple

MEMBER_OF = 'member-of'
STITCH_PORT = 'stitch-port'
GROUP = 'group'
PRODUCER_FOR = 'producer-for'
CONSUMER_FOR = 'consumer-for'


class ProviderPolicy:
    def __init__(self, *, type, stitch_ports, groups):
        self.type = type
        self.stitch_ports = stitch_ports

        for group in groups:
            if CONSUMER_FOR not in group:
                group[CONSUMER_FOR] = []
            if PRODUCER_FOR not in group:
                group[PRODUCER_FOR] = []

        self.groups = groups

    def __str__(self) -> str:
        lst = ["stitch_ports=" + str(self.stitch_ports), "groups=" + str(self.groups)]
        return str(lst)

    def __repr__(self) -> str:
        return self.__str__()


StitchInfo = namedtuple("StitchInfo", "stitch_port producer consumer producer_group consumer_group")


def parse_policy(policy) -> Dict[str, ProviderPolicy]:
    for k, v in policy.items():
        stitch_ports = v[STITCH_PORT] if STITCH_PORT in v else []

        for stitch_port in stitch_ports:
            if 'preference' not in stitch_port:
                stitch_port['preference'] = 0

        groups = v[GROUP] if GROUP in v else []

        for g in groups:
            g[Constants.PROVIDER] = k

        policy[k] = ProviderPolicy(type=k, stitch_ports=stitch_ports, groups=groups)

    return policy


def load_policy(*, policy_file=None, content=None) -> Dict[str, ProviderPolicy]:
    import os
    import yaml

    if content:
        policy = yaml.safe_load(content)
        return parse_policy(policy)

    if not policy_file:
        policy_file = os.path.join(os.path.dirname(__file__), 'policy.yaml')

    with open(policy_file, 'r') as fp:
        policy = yaml.load(fp, Loader=yaml.FullLoader)
    return parse_policy(policy)


def find_stitch_port_for_group(policy: Dict[str, ProviderPolicy], group: str, providers: List[str]) -> List[StitchInfo]:
    provider1 = providers[0]
    provider2 = providers[1]
    stitch_infos = []

    for g in policy[provider1].groups:
        temp = provider2 + "/" + group

        if temp in g[CONSUMER_FOR]:  # provider1's group is a consumer, find provider2's groups that are producers
            for producer_group in policy[provider2].groups:
                if provider1 + "/" + group in producer_group[PRODUCER_FOR]:
                    for stitch_port in policy[provider2].stitch_ports:
                        if group in stitch_port[MEMBER_OF]:
                            stitch_info = StitchInfo(stitch_port=stitch_port,
                                                     producer=producer_group[Constants.PROVIDER],
                                                     consumer=g[Constants.PROVIDER],
                                                     producer_group=producer_group,
                                                     consumer_group=g)
                            stitch_infos.append(stitch_info)

        if temp in g[PRODUCER_FOR]:   # provider2's group is a producer find provider2's groups that are consumers
            for consumer_group in policy[provider2].groups:
                if provider1 + "/" + group in consumer_group[CONSUMER_FOR]:
                    for stitch_port in policy[provider1].stitch_ports:
                        if group in stitch_port[MEMBER_OF]:
                            stitch_info = StitchInfo(stitch_port=stitch_port,
                                                     producer=g[Constants.PROVIDER],
                                                     consumer=consumer_group[Constants.PROVIDER],
                                                     producer_group=g,
                                                     consumer_group=consumer_group)
                            stitch_infos.append(stitch_info)

    return stitch_infos


def check_options(k, v, adict):
    temp = adict.get('option')

    if temp:
        assert isinstance(temp, dict), "option must be a dictionary"

        if temp.get(k):
            if isinstance(v, str) and v == temp.get(k):
                return True, {(k, v)}

            if isinstance(v, list):
                for v_pair in v:
                    aset = set(v_pair.items())

                    if isinstance(temp.get(k), list):
                        for t_pair in temp.get(k):
                            bset = set(t_pair.items())

                            if aset.issubset(bset):
                                return True, aset

    return False, None


def find_stitch_port(*, policy: Dict[str, ProviderPolicy], providers: List[str], site=None,
                     profile=None, options=None) -> StitchInfo or None:
    from fabfed.util.utils import get_logger

    logger = get_logger()
    stitch_infos = []

    for g in policy[providers[0]].groups:
        temp_stitch_infos = find_stitch_port_for_group(policy, g['name'], providers)
        stitch_infos.extend(temp_stitch_infos)

    stitch_infos.sort(key=lambda si: si.stitch_port['preference'], reverse=True)

    logger.info(f"Found {len(stitch_infos)} stitch ports")

    # Using the options first
    if options:
        for k, v in options.items():
            for stitch_info in stitch_infos:
                if k == 'port_name':
                    k = 'name'

                if stitch_info.stitch_port.get(k) == v:
                    logger.info(f"Using stitch port based on port: {k}={v} and providers={providers}:{stitch_info}")
                    return stitch_info

                ret, aset = check_options(k, v, stitch_info.stitch_port)

                if ret:
                    logger.info(
                        f"Using stitch port based on port: {aset} and providers={providers}:{stitch_info}")
                    return stitch_info

                for g in [stitch_info.consumer_group, stitch_info.producer_group]:
                    if k == 'group_name':
                        k = 'name'

                    if g.get(k) == v:
                        logger.info(
                            f"Using stitch port based on group: {k}={v} and providers={providers}:{stitch_info}")
                        return stitch_info

                    ret, aset = check_options(k, v, g)

                    if ret:
                        logger.info(
                            f"Using stitch port based on group: {aset} and providers={providers}:{stitch_info}")
                        return stitch_info
            logger.warning(f"No stitch port based on {k}={v}")

    if profile:
        for stitch_info in stitch_infos:
            for g in [stitch_info.consumer_group, stitch_info.producer_group]:
                if g.get(Constants.RES_PROFILE) == profile:
                    logger.info(f"Using stitch port based on profile={profile} and providers={providers}:{stitch_info}")
                    return stitch_info

    if site:
        for stitch_info in stitch_infos:
            if site == stitch_info.stitch_port['site']:
                logger.info(f"Using stitch port based on site={site} and providers={providers}:{stitch_info}")
                return stitch_info

        logger.warning(f"did not find a stitch port for site={site} and providers={providers}")

    stitch_info = stitch_infos[0] if stitch_infos else None

    if not stitch_info:
        raise StitchPortNotFound(f"did not find a stitch port for providers={providers}")

    if len(stitch_infos) > 1:
        logger.info(f"Using stitch port based on preference for providers={providers}:{stitch_info}")
    else:
        logger.info(f"Using stitch port for providers={providers}:{stitch_info}")

    return stitch_info


def find_profile(network, resources):
    profile = network.attributes.get(Constants.RES_PROFILE)

    # if not profile:
    #     for dep in [dep for dep in network.dependencies if dep.resource.is_network]:
    #         profile = dep.resource.attributes.get(Constants.RES_PROFILE)
    #
    #         if profile:
    #             break

    if not profile:
        for net in [resource for resource in resources if resource.is_network]:
            if [dep for dep in network.dependencies if dep.resource == net]:
                profile = net.attributes.get(Constants.RES_PROFILE)

                if profile:
                    break
    return profile


def find_site(network, resources):
    site = network.attributes.get(Constants.RES_SITE)

    if not site:
        for dep in network.dependencies:
            if dep.resource.is_node:
                site = dep.resource.attributes.get(Constants.RES_SITE)

                if site:
                    break

    if not site:
        for node in [resource for resource in resources if resource.is_node]:
            if [dep for dep in node.dependencies if dep.resource == network]:
                site = node.attributes.get(Constants.RES_SITE)

                if site:
                    break
    return site


def handle_stitch_info(config, policy, resources):
    has_stitch_with = False

    for network in [resource for resource in resources if resource.is_network]:
        if Constants.NETWORK_STITCH_WITH in network.attributes:
            has_stitch_with = True
            dependency_info = network.attributes[Constants.NETWORK_STITCH_WITH]
            dependencies = network.dependencies
            network_dependency = None

            for ed in dependencies:
                if ed.key == Constants.NETWORK_STITCH_WITH and ed.resource.label == dependency_info.resource.label:
                    network_dependency = ed
                    break

            assert network_dependency is not None, "should never happen"
            assert network_dependency.is_external, "only network stitching across providers is supported"
            other_network = network_dependency.resource
            assert other_network.is_network, "only network stitching is supported"

            site = find_site(network, resources)
            profile = find_profile(network, resources)
            options = network.attributes.get(Constants.NETWORK_STITCH_OPTION, list())

            stitch_info = find_stitch_port(policy=policy,
                                           providers=[network.provider.type, other_network.provider.type],
                                           site=site,
                                           profile=profile,
                                           options=options)
            network.attributes.pop(Constants.NETWORK_STITCH_WITH)

            from fabfed.util.config_models import DependencyInfo

            if network.provider.type == stitch_info.consumer:
                network.attributes[Constants.RES_STITCH_INTERFACE] = DependencyInfo(resource=other_network,
                                                                                    attribute='')
            else:
                other_network.attributes[Constants.RES_STITCH_INTERFACE] = DependencyInfo(resource=network,
                                                                                          attribute='')

            network.attributes[Constants.RES_STITCH_INFO] = stitch_info
            other_network.attributes[Constants.RES_STITCH_INFO] = stitch_info

    if has_stitch_with:
        for resource in resources:
            resource.dependencies.clear()

        from fabfed.util.resource_dependency_helper import ResourceDependencyEvaluator, order_resources

        dependency_evaluator = ResourceDependencyEvaluator(resources, config.get_provider_config())
        dependency_map = dependency_evaluator.evaluate()
        resources = order_resources(dependency_map)

    return resources
