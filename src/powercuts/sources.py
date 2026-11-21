import json

FEEDS = {
    "nged": {
        "name": "National Grid Electricity Distribution",
        "url": "https://connecteddata.nationalgrid.co.uk/dataset/d6672e1e-c684-4cea-bb78-c7e5248b62a2/resource/a1365982-4e05-463c-8304-8323a2ba0ccd/download/live_detailed_power_cuts.csv",
        "extension": "csv",
    },
    "ssen": {
        "name": "Scottish and Southern Electricity Networks",
        "url": "https://external.distribution.prd.ssen.co.uk/opendataportal-prd/v4/api/getallfaults",
        "extension": "json",
    },
    "npg": {
        "name": "Northern Powergrid",
        "url": "https://northernpowergrid.opendatasoft.com/api/explore/v2.1/catalog/datasets/live-power-cuts-data/exports/json",
        "extension": "json",
    },
    "spen": {
        "name": "SP Energy Networks",
        "url": "https://spenergynetworks.opendatasoft.com/api/explore/v2.1/catalog/datasets/distribution-network-live-outages/exports/json",
        "extension": "json",
        "api_key_env": "SPEN_API_KEY",
    },
    "ukpn": {
        "name": "UK Power Networks",
        "url": "https://ukpowernetworks.opendatasoft.com/api/explore/v2.1/catalog/datasets/ukpn-live-faults/exports/json",
        "extension": "json",
        "api_key_env": "UKPN_API_KEY",
    },
    "enwl": {
        "name": "Electricity North West",
        "url": "https://electricitynorthwest.opendatasoft.com/api/explore/v2.1/catalog/datasets/live_incidents/exports/json",
        "extension": "json",
        "api_key_env": "ENWL_API_KEY",
    }
}