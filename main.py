from string import Template
import workflow_report as wr
import create_catchall as cc
import logging
import sys
import requests
import openpyxl


def initialize_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

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
    # logger.debug(f'New Relic API response:\n{nr_response}')

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
    # 2W-MCS-PrudentPublishing (duplicate?), 2W-MCS-TitleMax, 2W-PRO-Development
    account_exclude_list = [2804528, 3719648, 2631905, 3498029, 3720977, 3563046, 3563050,
                            2726097, 2563179, 2978097, 3589554, 2623152, 2824352]

    account_id = 3498029
    client_name = '2W-MCS-Tooling-Test'
    logger.info(f'Creating catch-all workflow for {client_name} in NR account {account_id}...')
    process_result = cc.create_catchall_workflow(client_name, account_id, logger)


do_the_things()
