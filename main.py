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


def nr_function(logger):
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

    # response['data']['actor']['account']['aiNotifications']['destinations'] (list of destinations)
    # destination keys: 'id', 'name'
    # 'id' if 'Moogsoft' (case-insensitive) in 'name'
    nr_gql_destinations_query = Template("""
    {
      actor {
        account(id: $account_id) {
          aiNotifications {
            destinations(filters: {type: WEBHOOK}) {
              entities {
                name
                id
              }
            }
          }
        }
      }
    }
    """)

    # response['data']['actor']['account']['alerts']['policiesSearch']['policies'] (list of policies)
    # policy keys: 'id', 'name'
    nr_gql_policies_query = Template("""
    {
      actor {
        account(id: 2621186) {
          alerts {
            policiesSearch {
              policies {
                id
                name
              }
            }
          }
        }
      }
    }
    """)

    # response['data']['actor']['account']['aiWorkflows']['workflows']['entities'] (list of workflow entities)
    # entity keys: 'id', 'name', 'workflowEnabled', 'destinationConfigurations'
    # destinationConfigurations keys: 'channelId', 'name', 'type'
    nr_gql_workflows_query = Template("""
    {
      actor {
        account(id: 2621186) {
          aiWorkflows {
            workflows {
              entities {
                id
                name
                workflowEnabled
                lastRun
                destinationConfigurations {
                  channelId
                  name
                  type
                }
              }
            }
          }
        }
      }
    }
    """)

    # TODO: get list of account numbers in NR
    # TODO: for each account, get list of policies
    # TODO: for each account, get list of workflows
    # TODO: for each workflow, if it has a 2W Platform destination, collect policy name (should be in workflow name)
    #  and id
    # TODO: create catchall workflow with 2W Platform destination that includes all policies frm list in previous step
    # TODO: disable all individual workflows with 2W Platform destination

    # --- end automation for now ---

    # TODO: will need to manually go in and remove Moogsoft destination from any still-active workflows
    # TODO: if disabling individual workflows has no impact on monitoring, then go back and delete those workflows
    # TODO: once Moogsoft destinations are no longer used by any workflows, the destinations can be deleted

    accounts_query_fmtd = nr_gql_accounts_query.substitute({})
    nr_response = requests.post(nr_endpoint,
                                headers=nr_headers,
                                json={'query': accounts_query_fmtd}).json()
    # logger.debug(f'New Relic API response:\n{nr_response}')

    return nr_response


def do_the_things():
    logger = initialize_logger()

    # accounts = nr_function(logger)

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

    # 2621186 2W-MCS-2ndWatch
    # process_result = wr.generate_workflow_report('2W-MCS-2ndWatch', 2621186, logger)


do_the_things()
