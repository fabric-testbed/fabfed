from fabfed.util.constants import Constants

SENSE_PROFILE_UID = "service_profile_uuid"
SENSE_ALIAS = "alias"
SENSE_EDIT = "options"
SENSE_URI = 'uri'
# SENSE_ID = 'id'
SENSE_PATH = 'path'
SENSE_VLAN_TAG = 'vlan_tag'

SERVICE_INSTANCE_KEYS = ['intents', 'alias', 'referenceUUID', 'state', 'owner', 'lastState', 'timestamp', 'archived']

SENSE_CUSTOMER_ASN = "customer_asn"
SENSE_AMAZON_ASN = "amazon_asn"
SENSE_CUSTOMER_IP = "customer_ip"
SENSE_AMAZON_IP = "amazon_ip"
SENSE_AUTHKEY = "authkey"
SENSE_TO_HOSTED_CONN = "to_hosted_conn"

SENSE_AWS_PEERING_MAPPING = {
    Constants.RES_LOCAL_ASN: SENSE_AMAZON_ASN,
    Constants.RES_LOCAL_ADDRESS: SENSE_AMAZON_IP,

    Constants.RES_REMOTE_ASN: SENSE_CUSTOMER_ASN,
    Constants.RES_REMOTE_ADDRESS: SENSE_CUSTOMER_IP,

    Constants.RES_SECURITY: SENSE_AUTHKEY,

    Constants.RES_ID: SENSE_TO_HOSTED_CONN,
}
