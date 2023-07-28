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


def do_the_things():
    logger = initialize_logger()

    # generate an Excel report of all NR workflows
    # accounts = get_nr_account_ids(logger)
    # for account in accounts['data']['actor']['accounts']:
    #     client_name = account['name']
    #     account_id = account['id']
    #     logger.info(f'{client_name}: {account_id}')
    #
    #     client_name_sliced = client_name[:30]
    #
    #     process_result = wr.generate_workflow_report(client_name_sliced, account_id, logger)
    #
    #     if process_result == 0:
    #         logger.info(f'\n{client_name} processed successfully.\n')
    #
    # workbook = openpyxl.load_workbook('Workflow Report.xlsx')
    # workbook._sheets.sort(key=lambda ws: ws.title)
    # workbook.save('Workflow Report sorted.xlsx')

    # 3720977 2W-MCS-Tooling-Test
    # Test policy: 4569885

    # 2621186 2W-MCS-2ndWatch
    process_result = cc.create_catchall_workflow('2W-MCS-Tooling-Test', 3720977, logger)


do_the_things()
