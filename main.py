from string import Template
from datetime import datetime
import workflow_report as wr
import create_catchall as cc
import remove_workflows as rem
import logging
import sys
import requests
import openpyxl
from traceback import print_exc


def initialize_logger():
    logger = logging.getLogger()
    logging.basicConfig(level=logging.INFO,
                        filename=f'cleanup_{datetime.now().strftime("%Y-%m-%d_%H%M%S")}.log',
                        filemode='a')
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    logger.addHandler(console)

    return logger


def get_nr_account_ids(endpoint, headers):

    # response['data']['actor']['accounts'] (list of accounts)
    # account keys: 'id', 'name'
    nr_gql_accounts_query = Template("""
    {
      actor {
        accounts {
          id
          name
        }
      }
    }
    """)

    accounts_query_fmtd = nr_gql_accounts_query.substitute({})
    nr_response = requests.post(endpoint,
                                headers=headers,
                                json={'query': accounts_query_fmtd}).json()
    # logger.info(f'New Relic API response:\n{type(nr_response)}')

    return nr_response


def generate_report(accounts, logger):
    for account in accounts['data']['actor']['accounts']:
        client_name = account['name']
        account_id = account['id']
        logger.info(f'{client_name}: {account_id}')

        client_name_sliced = client_name[:30]

        process_result = wr.generate_workflow_report(client_name_sliced, account_id, logger)

        if process_result == 0:
            logger.info(f'\n{client_name} processed successfully.\n')

    workbook = openpyxl.load_workbook('Workflow Report.xlsx')
    workbook._sheets.sort(key=lambda ws: ws.title)
    workbook.save('Workflow Report sorted.xlsx')

    return


def process_client(endpoint, headers, client_name, account_id, logger):

    workflows_not_disabled = []

    try:

        # Get all destination IDs from an account and find the ID for '2W Platform API'
        destination_id = cc.get_destination_id(endpoint, headers, account_id, logger)

        # Create a new channel for '2W Platform API' destination
        channel_id = cc.create_channel(endpoint, headers, destination_id, account_id, logger)

        # Get all workflows that currently use the '2W Platform API' webhook except any with 'Platform' in the name;
        #   return a list of policy IDs & list of workflow IDs
        policy_ids_list, create_catchall, workflow_ids_list, workflows_to_check = cc.get_policy_ids(endpoint, headers,
                                                                                                    client_name,
                                                                                                    account_id,
                                                                                                    logger)

        # Create a new workflow called 'MCS Platform' & associate appropriate policies
        if create_catchall:
            process_code = cc.create_workflow(endpoint, headers, account_id, channel_id, policy_ids_list, logger)
            if process_code < 1:
                workflows_not_disabled = cc.disable_workflows(endpoint, headers, account_id, workflow_ids_list, logger)
        else:
            logger.info(f'\nA Platform catchall workflow already exists for {client_name}. Skipping workflow creation.')

        return workflows_to_check, workflows_not_disabled

    except Exception:
        logger.warning('There was an error:')
        logger.warning(print_exc())
        sys.exit(1)


def clean_up_client(endpoint, headers, account_id, logger):
    workflows_not_removed = []
    destinations_not_removed = []
    rem.remove_disabled_workflows(endpoint, headers, account_id, logger)
    logger.info('.....\n\n')
    rem.remove_destinations(endpoint, headers, account_id, logger)

    return


def create_catchall_workflow():
    logger = initialize_logger()
    logger.info('Starting the workflow and destination removal process...')

    endpoint = 'https://api.newrelic.com/graphql'
    headers = {
        'Content-Type': 'application/json',
        'API-Key': '',
    }

    manual_workflow_checks = []
    manual_workflow_disables = []

    # Get list of all New Relic account numbers
    accounts = get_nr_account_ids(endpoint, headers)

    # Generate an Excel report of all NR workflows, if needed
    # generate_report(accounts, logger)

    # For testing purposes only
    # 3720977 2W-MCS-Tooling-Test
    # Test policy: 4569885
    # 2621186 2W-MCS-2ndWatch

    # 2W-MCS-Development, 2W-MCS-Internal-IT, 2W-MCS-Sandboxes, 2W-MCS-SiriusPoint-AWS, 2W-MCS-Tooling-Test,
    # 2W-MCS-Sysco-Azure, 2W-MCS-Sysco-GCP, 2W-MCS-AutoNation, 2nd Watch Partner,
    # 2W-MCS-PrudentPublishing (duplicate?), 2W-MCS-TitleMax, 2W-PRO-Development
    account_exclude_list = [2804528, 3719648, 2631905, 3498029, 3720977, 3563046, 3563050,
                            2726097, 2563179, 3589554, 2623152, 2824352]

    accounts_list = accounts['data']['actor']['accounts']
    accounts_sorted = sorted(accounts_list, key=lambda x: x['name'])

    # batch testing
    # accounts_sorted = [{"id": 3720977, "name": "2W-MCS-Tooling-Test"}]

    # {"id": 2709553, "name": "2W-MCS-BadgerMeter"},
    # {"id": 2709554, "name": "2W-MCS-Cargill"},
    # {"id": 3719690, "name": "2W-MCS-CKE"},
    # {"id": 2622938, "name": "2W-MCS-Coaction"},
    # {"id": 3084223, "name": "2W-MCS-CrateAndBarrel"},
    # {"id": 2621186, "name": "2W-MCS-2ndWatch"}

    for account in accounts_sorted:
        account_id = account['id']
        client_name = account['name']

        # Create catchall workflow and disable individual workflows using Platform API
        # if account_id not in account_exclude_list:
        #     logger.info(f'\n-----\nProcessing {client_name} in NR account {account_id}...\n-----\n')
        #     workflows_to_check, workflows_not_disabled = process_client(endpoint, headers, client_name,
        #                                                                 account_id, logger)
        #     if workflows_to_check:
        #         for workflow in workflows_to_check:
        #             manual_workflow_checks.append(workflow)
        #     if workflows_not_disabled:
        #         for wf_dis in workflows_not_disabled:
        #             manual_workflow_disables.append(wf_dis)
        # else:
        #     logger.info(f'{client_name} in excluded accounts list; skipping account.\n')

        if account_id not in account_exclude_list:
            logger.info(f'\n-----\nProcessing {client_name} in NR account {account_id}...\n-----\n')
            clean_up_client(endpoint, headers, account_id, logger)
        else:
            logger.info(f'\n-----\n{client_name} in excluded accounts list; skipping account.\n-----\n')

    # Post-processing message for creating/disabling Platform workflows
    # logger.info('\nPlatform workflow process complete for all accounts.\nManually check the following workflows:')
    # for manual_workflow in manual_workflow_checks:
    #     logger.info(f'   {manual_workflow}')
    # logger.info('\nManually locate and disable the following workflows:')
    # for man_dis in manual_workflow_disables:
    #     logger.info(f'   {man_dis}')


create_catchall_workflow()
