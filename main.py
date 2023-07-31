from string import Template
from datetime import datetime
import workflow_report as wr
import create_catchall as cc
import logging
import sys
import requests
import openpyxl


def initialize_logger():
    logger = logging.getLogger()
    logging.basicConfig(level=logging.INFO,
                        filename=f'cleanup_{datetime.now().strftime("%Y-%m-%d_%H%M%S")}.log',
                        filemode='a')
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    logger.addHandler(console)

    return logger


def get_nr_account_ids(logger):
    nr_endpoint = 'https://api.newrelic.com/graphql'
    nr_headers = {
        'Content-Type': 'application/json',
        'API-Key': 'NRAK-7DVT82DILPFIAXSZZ6CLPKYB8YU',
    }

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
    nr_response = requests.post(nr_endpoint,
                                headers=nr_headers,
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


def create_catchall_workflow(client_name, account_id, logger):
    endpoint = 'https://api.newrelic.com/graphql'
    headers = {
        'Content-Type': 'application/json',
        'API-Key': 'NRAK-7DVT82DILPFIAXSZZ6CLPKYB8YU',
    }

    # Get all destination IDs from an account and find the ID for '2W Platform API'
    destination_id = cc.get_destination_id(endpoint, headers, account_id, logger)

    # Create a new channel for '2W Platform API' destination
    # channel_id = cc.create_channel(endpoint, headers, destination_id, account_id, logger)

    # Get all workflows that currently use the '2W Platform API' webhook except any with 'Platform' in the name;
    #   return a list of policy IDs & list of workflow IDs
    policy_ids_list, create_catchall, workflow_ids_list, workflows_to_check = cc.get_policy_ids(endpoint, headers,
                                                                                                client_name, account_id,
                                                                                                logger)

    # Create a new workflow called 'MCS Platform' & associate appropriate policies
    # workflow_id = cc.create_workflow(endpoint, headers, account_id, channel_id, policy_ids_list, logger)

    # TODO: disable appropriate policies
    # pass in workflow IDs

    return 0


def do_the_things():
    logger = initialize_logger()

    # Get list of all New Relic account numbers
    accounts = get_nr_account_ids(logger)

    # generate an Excel report of all NR workflows, if needed
    # generate_report(accounts, logger)

    # 3720977 2W-MCS-Tooling-Test
    # Test policy: 4569885
    # 2621186 2W-MCS-2ndWatch

    # 2W-MCS-Development, 2W-MCS-Internal-IT, 2W-MCS-Sandboxes, 2W-MCS-SiriusPoint-AWS, 2W-MCS-Tooling-Test,
    # 2W-MCS-Sysco-Azure, 2W-MCS-Sysco-GCP, 2W-MCS-AutoNation, 2nd Watch Partner, 2W-MCS-Cargill-IT,
    # 2W-MCS-PrudentPublishing (duplicate?), 2W-MCS-TitleMax, 2W-PRO-Development, USPlateGlass
    account_exclude_list = [2804528, 3719648, 2631905, 3498029, 3720977, 3563046, 3563050,
                            2726097, 2563179, 2978097, 3589554, 2623152, 2824352, 2726096]

    accounts_list = accounts['data']['actor']['accounts']
    # print(accounts_list)
    accounts_sorted = sorted(accounts_list, key=lambda x: x['name'])
    # print(accounts_sorted)

    for account in accounts_sorted:
        account_id = account['id']
        client_name = account['name']
        if account_id not in account_exclude_list:
            logger.info(f'Processing {client_name} in NR account {account_id}...')
            process_result = create_catchall_workflow(client_name, account_id, logger)
        else:
            logger.info(f'{client_name} in excluded accounts list; skipping account.\n')


do_the_things()
