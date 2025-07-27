import requests
from django.conf import settings

HUBSPOT_API_BASE_URL = 'https://api.hubapi.com/crm/'


def get_hubspot_api_key():
    key = getattr(settings, "HUBSPOT_API_KEY", None)
    if not key:
        raise RuntimeError("HUBSPOT_API_KEY is not set in settings.")
    return key


def get_hubspot_headers():
    return {
        "Authorization": f"Bearer {get_hubspot_api_key()}",
        "Content-Type": "application/json",
    }


def get_all_deals():
    all_deals_data = []
    params = {"limit": 100, "archived": "false"}

    while True:
        deal_url = HUBSPOT_API_BASE_URL + "v4/objects/deals"
        response = requests.get(deal_url, headers=get_hubspot_headers(), params=params)

        if response.status_code != 200:
            print(f"Error: {response.status_code}: {response.text}")
            break

        data = response.json()
        all_deals_data.extend(data.get("results", []))

        next_page_info = data.get("paging", {}).get("next")
        if not next_page_info:
            break
        params["after"] = next_page_info["after"]

    return all_deals_data


def get_company_ids_from_deal_id(deal_ids):
    """Fetch associated companies for a list of deal IDs using HubSpot API batch requests."""
    if not deal_ids:
        return []

    url = f"{HUBSPOT_API_BASE_URL}v4/associations/deals/companies/batch/read"

    payload = {"inputs": [{"id": deal_id} for deal_id in deal_ids]}

    try:
        response = requests.post(url, headers=get_hubspot_headers(), json=payload)
        response.raise_for_status()  # Raises an error for HTTP status codes 4xx/5xx
        json_response = response.json()

    except requests.exceptions.RequestException as e:
        print(f"Error fetching company associations: {e}")
        return []

    deal_id_to_company_id = {}

    for result in json_response.get("results", []):
        deal_id = result['from']['id']
        company_ids = []
        for company in result['to']:
            company_ids.append(company['toObjectId'])
        deal_id_to_company_id[deal_id] = company_ids

    return deal_id_to_company_id


def get_contacts_from_deal_id(deal_ids):
    if not deal_ids:
        return []

    url = f"{HUBSPOT_API_BASE_URL}v4/associations/deals/contacts/batch/read"

    payload = {"inputs": [{"id": deal_id} for deal_id in deal_ids]}

    try:
        response = requests.post(url, headers=get_hubspot_headers(), json=payload)
        response.raise_for_status()
        json_response = response.json()

    except requests.exceptions.RequestException as e:
        print(f"Error fetching contact associations: {e}")
        return []

    deal_id_to_contact_id = {}

    for result in json_response.get("results", []):
        deal_id = result['from']['id']
        contact_ids = []
        for contact in result['to']:
            contact_ids.append(contact['toObjectId'])
        deal_id_to_contact_id[deal_id] = contact_ids

    return deal_id_to_contact_id


def extract_ids(deal_to_other_ids):
    if not deal_to_other_ids:
        return []
    deal_ids = deal_to_other_ids.keys()
    key_list = []
    for deal_id in deal_ids:
        key_list.extend(deal_to_other_ids[deal_id])
    return key_list


def get_company_info_from_company_ids(company_ids):
    if not company_ids:
        return

    companies_set = set(company_ids)

    url = f"{HUBSPOT_API_BASE_URL}v3/objects/companies/batch/read"

    payload = {
        "properties": [
            "name",
            "description",
        ],
        "inputs": [{"id": company_id} for company_id in company_ids],
    }

    companies_data = {}

    response = requests.post(url, headers=get_hubspot_headers(), json=payload)
    response.raise_for_status()
    json_response = response.json()

    for result in json_response["results"]:
        companies_data[result["id"]] = {
            "name": result['properties']["name"],
            "description": result['properties']['description'],
        }

    return companies_data


def get_contact_info_from_contact_ids(contact_ids):
    if not contact_ids:
        return

    contacts = set(contact_ids)

    url = f"{HUBSPOT_API_BASE_URL}v3/objects/contacts/batch/read"

    payload = {
        "properties": [
            "firstname",
            "lastname",
            "email"
        ],
        "inputs": [{"id": company_id} for company_id in contact_ids],
    }

    contacts_data = {}

    response = requests.post(url, headers=get_hubspot_headers(), json=payload)
    response.raise_for_status()
    json_response = response.json()

    for result in json_response["results"]:
        contacts_data[result["id"]] = {
            "first_name": result['properties']["firstname"],
            "last_name": result['properties']['lastname'],
            "email": result['properties']['email'],
        }

    return contacts_data


def update_deal_stage(deal_id, new_stage, order):
    """Updates the dealstage for a specific deal in HubSpot."""
    url = f"{HUBSPOT_API_BASE_URL}v3/objects/deals/{deal_id}"

    payload = {
        "properties": {
            "dealstage": new_stage.API_id
        }
    }

    try:
        response = requests.patch(url, headers=get_hubspot_headers(), json=payload)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"Error updating deal stage: {e}")
        return None

def update_stages(pipeline_id):
    from Tracker.models import ExternalAPIOrderIdentifier
    url = f"{HUBSPOT_API_BASE_URL}v3/pipelines/deals/{pipeline_id}/stages"
    try:
        response = requests.get(url, headers=get_hubspot_headers())
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error updating stages: {e}")
        return None
    results_json = response.json()
    for result in results_json["results"]:
        ExternalAPIOrderIdentifier.objects.update_or_create(
            API_id=result["id"],
            defaults={
                "stage_name": result["label"]
            }
        )