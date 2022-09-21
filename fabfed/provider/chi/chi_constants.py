DEFAULT_NETWORK = "sharednet1"
DEFAULT_NETWORKS = [DEFAULT_NETWORK, "sharedwan1", "containernet1"]
DEFAULT_FLAVOR = "m1.medium"

DEFAULT_AUTH_URLS = dict(
    tacc='https://chi.tacc.chameleoncloud.org:5000/v3',
    uc='https://chi.uc.chameleoncloud.org:5000/v3',
    kvm='https://kvm.tacc.chameleoncloud.org:5000/v3',
    edge='https://chi.edge.chameleoncloud.org:5000/v3'
)

DEFAULT_CLIENT_IDS = dict(
    tacc='keystone-tacc-prod',
    uc='keystone-uc-prod',
    kvm='keystone-kvm-prod',
    edge='keystone-edge-prod'
)

DEFAULT_PROJECT_IDS = dict(
    tacc='a400724e818d40cbba1a5c6b5e714462',
    uc='ae76673270164b048b59d3bd30676721',
    kvm='a400724e818d40cbba1a5c6b5e714462',
    edge=None
)

DEFAULT_DISCOVERY_URL = "https://auth.chameleoncloud.org/auth/realms/chameleon/.well-known/openid-configuration"
