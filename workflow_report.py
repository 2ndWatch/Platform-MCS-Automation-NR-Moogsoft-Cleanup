from UliPlot.XLSX import auto_adjust_xlsx_column_width as adjust
import pandas as pd
from string import Template
import requests


def do_keep_disable_workflow(workflow, logger):
    keep_workflow = True
    disable_workflow = False
    destinations = workflow['destinationConfigurations']
    destinations_set = set()
    set_to_compare = {
        'WEBHOOK - 2W Platform API',
        'WEBHOOK - Moogsoft_Ingestion_QA_tf',
        'WEBHOOK - Moogsoft_Ingestion_tf',
        'SLACK - mcs-tooling-nr-migration-test',
        'WEBHOOK - OpsRamp-ProSight',
        'WEBHOOK - OpsRamp',
        'WEBHOOK - MoogCloud',
        'WEBHOOK - MoogCloud',
        'WEBHOOK - Moog Prod AWS',
        'WEBHOOK - Moog Prod Azure',
        'WEBHOOK - Moogsoft Ingestion',
        'WEBHOOK - MS_NewRelic-OpsRamp_Ticket'
    }

    if workflow['name'] == 'Platform Catchall':
        return keep_workflow, disable_workflow

    for destination in destinations:
        destination_string = f'{destination["type"]} - {destination["name"]}'
        # logger.info(f'      Destination: {destination_string}')
        destinations_set.add(destination_string)
        if destination["type"] == 'WEBHOOK' and destination["name"] == '2W Platform API':
            disable_workflow = True
        if destinations_set.issubset(set_to_compare):
            keep_workflow = False
            disable_workflow = True
    logger.info(f'      {len(destinations_set)} destinations: {destinations_set}')

    return keep_workflow, disable_workflow


def generate_workflow_report(client_name, account_id, logger):
    logger.info(f'Processing workflows for {client_name}...')

    # create a dataframe with column headings
    client_df = pd.DataFrame(columns=['Name', 'ID', 'Disable?', 'Keep?', 'Created At', 'Last Run', 'Destination 1',
                                      'Destination 2', 'Destination 3', 'Destination 4', 'Destination 5'])

    # query workflow API and put all workflows for client into a dataframe
    nr_endpoint = 'https://api.newrelic.com/graphql'
    nr_headers = {
        'Content-Type': 'application/json',
        'API-Key': 'NRAK-7DVT82DILPFIAXSZZ6CLPKYB8YU',
    }
    nr_gql_workflow_query = Template("""
    {
      actor {
        account(id: $account_id) {
          aiWorkflows {
            workflows {
              entities {
                id
                name
                createdAt
                lastRun
                destinationConfigurations {
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

    workflow_query_fmtd = nr_gql_workflow_query.substitute({'account_id': account_id})
    nr_response = requests.post(nr_endpoint,
                                headers=nr_headers,
                                json={'query': workflow_query_fmtd}).json()
    # logger.debug(f'New Relic API response:\n{nr_response}')
    try:
        workflows_list = nr_response['data']['actor']['account']['aiWorkflows']['workflows']['entities']

        logger.info(f'{len(workflows_list)} workflows found:')

        # evaluate destinations
        if workflows_list:
            for workflow in workflows_list:
                workflow_name = workflow['name']
                workflow_id = workflow['id']
                workflow_created = workflow['createdAt']
                workflow_last_run = workflow['lastRun']
                workflow_destinations = workflow['destinationConfigurations']

                logger.info(f'   Workflow: {workflow["name"]}')
                keep_workflow, disable_workflow = do_keep_disable_workflow(workflow, logger)
                logger.info(f'         Keep workflow: {keep_workflow}')
                logger.info(f'         Disable workflow: {disable_workflow}')

                # 'Name', 'ID', 'Disable?', 'Keep?', 'Created At', 'Last Run'
                row = [workflow_name, workflow_id, disable_workflow, keep_workflow, workflow_created, workflow_last_run]
                for destination in workflow_destinations:
                    row.append(f'{destination["type"]} - {destination["name"]}')
                for _ in range(5 - len(workflow_destinations)):
                    row.append('-')
                # logger.info(f'            Row: {row}')
                # logger.info(f'            Row length: {len(row)}')

                client_df.loc[len(client_df)] = row

            # logger.info(client_df.head(2))

            # write client dataframe as sheet to 'Workflow Report.xlsx' with sheet_name=client_name
            try:
                with pd.ExcelWriter('Workflow Report.xlsx', mode='a', if_sheet_exists='replace') as writer:
                    client_df.to_excel(writer, sheet_name=client_name, index=False)
                    adjust(client_df, writer, sheet_name=client_name, margin=3, index=False)
            except FileNotFoundError:
                with pd.ExcelWriter('Workflow Report.xlsx') as writer:
                    client_df.to_excel(writer, sheet_name=client_name, index=False)
                    adjust(client_df, writer, sheet_name=client_name, margin=3, index=False)

        # handle clients with no workflows
        else:
            logger.info(f'   {client_name} does not have any workflows; skipping client.\n')
            return 2

    except TypeError:
        logger.info(f'   New Relic returned an unusual response for {client_name}; skipping client. \n')
        return 1

    return 0
