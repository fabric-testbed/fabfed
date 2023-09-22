from ipaddress import IPv4Network, IPv6Network 

DEFAULT_RENEWAL_IN_DAYS = 14
DEFAULT_OC_HOST = 'orchestrator.fabric-testbed.net'
DEFAULT_CM_HOST = 'cm.fabric-testbed.net'
DEFAULT_BASTION_HOST = 'bastion-1.fabric-testbed.net'

FABRIC_OC_HOST = "oc-host"
FABRIC_CM_HOST = "cm-host"
FABRIC_TOKEN_LOCATION = "token-location"
FABRIC_BASTION_HOST = "bastion-host"
FABRIC_BASTION_USER_NAME = "bastion-user-name"
FABRIC_BASTION_KEY_LOCATION = "bastion-key-location"

FABRIC_RANDOM = "FABRIC.RANDOM"
FABRIC_PROJECT_ID = "project_id"

FABRIC_SLICE_PRIVATE_KEY_LOCATION = "slice-private-key-location"
FABRIC_SLICE_PUBLIC_KEY_LOCATION = "slice-public-key-location"

FABRIC_IPV4_NET_IFACE_NAME = "v4_net_iface"
FABRIC_IPV6_NET_IFACE_NAME = "v6_net_iface"
FABRIC_IPV4_NET_NAME = "v4_net"
FABRIC_IPV6_NET_NAME = "v6_net"
FABRIC_STITCH_NET_NAME = "stitch_net"
FABRIC_STITCH_NET_IFACE_NAME = "stitch_net_iface"

# RFC1918 FABRIC subnet
FABRIC_PRIVATE_IPV4_SUBNET = IPv4Network('10.128.0.0/10')
# FABRIC public ipv4 subnet
FABRIC_PUBLIC_IPV4_SUBNET = IPv4Network('23.134.232.0/22')
# FABRIC public ipv6 subnet
FABRIC_PUBLIC_IPV6_SUBNET = IPv6Network('2602:FCFB::0/40')

INCLUDE_FABNETS = True  # TODO This should be customizable

FABRIC_SLEEP_AFTER_SUBMIT_OK = 120  # In seconds
