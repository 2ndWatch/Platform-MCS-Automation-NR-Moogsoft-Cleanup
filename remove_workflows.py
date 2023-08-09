from string import Template
import requests


def remove_disabled_workflows(endpoint, headers, account_id, logger):
    logger.info('Discovering workflows...')

    nrql_workflow_query = Template("""
        {
          actor {
            account(id: $account_id) {
              aiWorkflows {
                workflows {
                  entities {
                    id
                    name
                    workflowEnabled
                  }
                }
              }
            }
          }
        }
        """)

    workflow_query_fmtd = nrql_workflow_query.substitute({'account_id': account_id})
    nr_response = requests.post(endpoint,
                                headers=headers,
                                json={'query': workflow_query_fmtd}).json()

    workflows_list = nr_response['data']['actor']['account']['aiWorkflows']['workflows']['entities']

    workflows_to_remove = []

    for wf in workflows_list:
        if wf['workflowEnabled']:
            logger.info(f'   Enabled workflow: {wf["name"]}')
            continue
        else:
            logger.info(f' * Disabled workflow found: {wf["name"]} | {wf["id"]}')
            workflows_to_remove.append(wf['id'])

    logger.info(f'\nThere are {len(workflows_list)} workflows in this account. {len(workflows_to_remove)} workflows '
                f'are disabled and can be removed.')

    logger.info('\nRemoving disabled workflows...')

    workflows_removed = 0
    workflows_not_removed = []

    nrql_remove_workflow = Template("""
    mutation {
        aiWorkflowsDeleteWorkflow(accountId: $account_id, id: "$workflow_id", deleteChannels: true) {
        id
        errors {
          type
          description
        }
      }
    }
    """)

    for workflow_id in workflows_to_remove:
        remove_workflow_fmtd = nrql_remove_workflow.substitute({'account_id': account_id,
                                                                'workflow_id': workflow_id})
        nr_response = requests.post(endpoint,
                                    headers=headers,
                                    json={'query': remove_workflow_fmtd}).json()

        if nr_response['data']['aiWorkflowsDeleteWorkflow']['id']:
            logger.info(f'   Workflow {workflow_id} removed and channels deleted.')
            workflows_removed += 1
        else:
            logger.info(f'   Something went wrong trying to delete workflow {workflow_id}:\n'
                        f'      {nr_response["data"]["aiWorkflowsDeleteWorkflow"]["errors"]}')
            workflows_not_removed.append(workflow_id)

    logger.info(f'\n{workflows_removed} workflows removed.\nManually check the following workflows which were not '
                f'removed:\n   {workflows_not_removed}\n\n')

    return


def remove_destinations(endpoint, headers, account_id, logger):
    logger.info(f'Discovering Moogsoft destinations...')

    nrql_destinations_query = Template("""
        {
          actor {
            account(id: $account_id) {
              aiNotifications {
                destinations {
                  entities {
                    id
                    name
                  }
                }
              }
            }
          }
        }
        """)

    destinations_query_fmtd = nrql_destinations_query.substitute({'account_id': account_id})
    nr_response = requests.post(endpoint,
                                headers=headers,
                                json={'query': destinations_query_fmtd}).json()

    destinations_list = nr_response['data']['actor']['account']['aiNotifications']['destinations']['entities']

    destinations = []
    destinations_to_remove = []

    for dest in destinations_list:
        destinations.append(dest['name'])

        if 'Moog' in dest['name'] or 'moog' in dest['name']:
            destinations_to_remove.append(dest['id'])
            logger.info(f' * Moogsoft destination found: {dest["name"]} | {dest["id"]}')
        else:
            logger.info(f'   Other destination: {dest["name"]}')

    logger.info(f'\nThere are {len(destinations)} destinations in this account. {len(destinations_to_remove)} '
                f'Moogsoft destinations can be removed.')

    logger.info('\nDeleting Moogsoft destinations...')

    destinations_removed = 0
    destinations_not_removed = []

    nrql_delete_destination = Template("""
    mutation DeleteDestinations {
      aiNotificationsDeleteDestination(
        accountId: $account_id
        destinationId: "$destination_id"
      ) {
        ids
        error {
          type
          details
          description
        }
      }
    }
    """)

    for destination_id in destinations_to_remove:
        delete_destination_fmtd = nrql_delete_destination.substitute({'account_id': account_id,
                                                                      'destination_id': destination_id})
        nr_response = requests.post(endpoint,
                                    headers=headers,
                                    json={'query': delete_destination_fmtd}).json()

        if nr_response['data']['aiNotificationsDeleteDestination']['ids']:
            logger.info(f'   Destination {destination_id} deleted.')
            destinations_removed += 1
        else:
            logger.info(f'   Something went wrong trying to delete destination {destination_id}:\n'
                        f'      {nr_response["data"]["aiNotificationsDeleteDestination"]["error"]}')
            destinations_not_removed.append(destination_id)

    logger.info(f'\n{destinations_removed} destinations deleted.\nManually check the following destinations which '
                f'were not deleted:\n   {destinations_not_removed}\n\n')

    return
