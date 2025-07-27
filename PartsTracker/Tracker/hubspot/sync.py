from django.core.exceptions import ObjectDoesNotExist

from Tracker.hubspot.api import (get_all_deals, get_contacts_from_deal_id, get_company_ids_from_deal_id, extract_ids,
                                 get_company_info_from_company_ids, get_contact_info_from_contact_ids,
                                 update_stages)
from Tracker.models import Orders, Companies, User, ExternalAPIOrderIdentifier
from django.conf import settings


def sync_all_deals():
    deals_data = get_all_deals()
    if not deals_data:
        return "Failed to retrieve all deals from HubSpot."

    result = []

    deal_id_list = []
    deal_ids = {}
    for deal in deals_data:
        deal_ids[deal['id']] = {}
        deal_id_list.append(deal['id'])

    deal_ids_to_contacts_ids = get_contacts_from_deal_id(deal_id_list)
    deal_ids_to_companies_ids = get_company_ids_from_deal_id(deal_id_list)

    contact_ids = extract_ids(deal_ids_to_contacts_ids)
    company_ids = extract_ids(deal_ids_to_companies_ids)

    contact_dictionary = get_contact_info_from_contact_ids(contact_ids)
    company_dictionary = get_company_info_from_company_ids(company_ids)

    update_stages(deal["properties"]["pipeline"])

    for deal in deals_data:
        try:
            current_gate = ExternalAPIOrderIdentifier.objects.get(API_id=deal["properties"]["dealstage"])
        except ObjectDoesNotExist:
            current_gate = None  # or handle it however you want

        if getattr(settings, "HUBSPOT_DEBUG"):
            if deal["properties"]["dealname"] == "Ghost Pepper":
                customers = []
                companies = []
                if deal["id"] in deal_ids_to_companies_ids.keys():
                    company = Companies.objects.update_or_create(
                        name=str(deal_ids_to_companies_ids[deal["id"]][-1]),
                        defaults={}
                    )
                if deal["id"] in deal_ids_to_contacts_ids.keys():
                    for id in deal_ids_to_contacts_ids[deal["id"]]:
                        customer_information = contact_dictionary[str(id)]
                        customer = User.objects.update_or_create(
                            email = customer_information["email"],
                            defaults={
                                "first_name": customer_information["first_name"],
                                "last_name": customer_information["last_name"],
                                "username": customer_information["email"]
                            }
                        )
                        customers.append(customer)
                obj, created = Orders.objects.update_or_create(
                    hubspot_deal_id=deal["id"],
                    defaults={
                        "name": deal["properties"]["dealname"],
                        "company_id": companies[-1] if companies else None,
                        "customer_id": customers[-1] if customers else None,
                        "current_hubspot_gate": current_gate,
                        "archived": deal["archived"]
                    }
                )
                result.append(deal["properties"]["dealname"])
        else:
            customers = []
            companies = []
            if deal["id"] in deal_ids_to_companies_ids.keys():
                company = Companies.objects.update_or_create(
                    name=str(deal_ids_to_companies_ids[deal["id"]][-1]),
                    defaults={}
                )
            if deal["id"] in deal_ids_to_contacts_ids.keys():
                for id in deal_ids_to_contacts_ids[deal["id"]]:
                    customer_information = contact_dictionary[str(id)]
                    customer = User.objects.update_or_create(
                        email=customer_information["email"],
                        defaults={
                            "first_name": customer_information["first_name"],
                            "last_name": customer_information["last_name"],
                            "username": customer_information["email"]
                        }
                    )
                    customers.append(customer)
            obj, created = Orders.objects.update_or_create(
                hubspot_deal_id=deal["id"],
                defaults={
                    "name": deal["properties"]["dealname"],
                    "company_id": companies[-1] if companies else None,
                    "customer_id": customers[-1] if customers else None,
                    "current_hubspot_gate": current_gate,
                    "archived": deal["archived"]
                }
            )
            result.append(deal["properties"]["dealname"])
    return result
