from string import Template
import requests
import json


def get_destination_id(endpoint, headers, account_id, logger):
    destination_id = ''

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

    if destinations_list:
        for destination in destinations_list:
            if 'Platform' in destination['name']:
                destination_id = destination['id']
                logger.info(f'Platform API destination ID: {destination_id}\n')

    return destination_id


def create_channel(endpoint, headers, destination_id, account_id, logger):
    channel_id = ''

    api_key = json.dumps("{\"x-api-key\":\"09b99595-8aef-45f7-99af-54e823a59895\"}")
    destination_id = json.dumps(destination_id)
    payload = json.dumps("{\n\"alert_level\": \"{{#if issueClosedAt}}closed{{else if issueAcknowledgedAt}}acknowledged{{else}}open{{/if}}-{{escape accumulations.conditionName.[0]}}\",\n\"current_state\": \"{{#if issueClosedAt}}closed{{else if issueAcknowledgedAt}}acknowledged{{else}}open{{/if}}\",\n\"description\": {\n\"account_id\": {{nrAccountId}},\n\"account_name\": \"{{accumulations.tag.account.[0]}}\",\n\"condition_id\": {{accumulations.conditionFamilyId.[0]}},\n\"condition_name\": \"{{escape accumulations.conditionName.[0]}}\",\n\"current_state\": \"{{#if issueClosedAt}}closed{{else if issueAcknowledgedAt}}acknowledged{{else}}open{{/if}}\",\n\"details\": \"{{escape issueTitle}}\",\n\"event_type\": \"INCIDENT\",\n\"incident_acknowledge_url\": \"<a href={{issuePageUrl}}>{{issuePageUrl}}</a>\",\n\"incident_id\": {{#if labels.nrIncidentId}}{{labels.nrIncidentId.[0]}}{{else}}-1{{/if}},\n\"incident_url\": \"{{issuePageUrl}}\",\n\"owner\": \"{{owner}}\",\n\"policy_name\": \"{{escape accumulations.policyName.[0]}}\",\n\"policy_url\": \"{{policyUrl}}\",\n\"runbook_url\": \"<a href={{accumulations.runbookUrl.[0]}}>{{accumulations.runbookUrl.[0]}}</a>\",\n\"severity\": \"{{#eq 'HIGH' priority}}WARNING{{else}}{{priority}}{{/eq}}\",\n\"timestamp\": {{updatedAt}}\n  },\n\"details\": \"{{escape issueTitle}}\",\n\"metric\": \"{{escape accumulations.policyName.[0]}}\",\n\"severity\": \"{{#eq 'HIGH' priority}}WARNING{{else}}{{priority}}{{/eq}}\",\n\"targets\": [\n { \n\"id\": \"{{labels.targetId.[0]}}\",\n\"name\": \"{{#if accumulations.targetName}}{{escape accumulations.targetName.[0]}}{{else if entitiesData.entities}}{{escape entitiesData.entities.[0].name}}{{else}}N/A{{/if}}\",\n\"link\": \"{{issuePageUrl}}\",\n\"product\": \"{{accumulations.conditionProduct.[0]}}\",\n\"type\": \"{{#if entitiesData.types.[0]}}{{entitiesData.types.[0]}}{{else}}N/A{{/if}}\",\n\"labels\": { {{#each accumulations.rawTag}}\"{{escape @key}}\": {{#if this.[0]}}{{json this.[0]}}{{else}}\"empty\"{{/if}}{{#unless @last}},{{/unless}}{{/each}}\n } \n} \n ],\n\"timestamp\": {{updatedAt}}\n}")

    nrql_create_channel = Template("""
        mutation {
          aiNotificationsCreateChannel(accountId: $account_id, channel: {
            type: WEBHOOK,
            name: "MCS Platform",
            destinationId: $destination_id,
            product: IINT,
            properties: [
              {
              key:"payload",
              value: $payload
              },
              {
              key:"headers",
              value: $api_key
              }
            ]
          }) {
            channel {
              id
            }
          }
        }
        """)

    create_channel_fmtd = nrql_create_channel.substitute({'account_id': account_id,
                                                          'destination_id': destination_id,
                                                          'payload': payload,
                                                          'api_key': api_key})
    nr_response = requests.post(endpoint,
                                headers=headers,
                                json={'query': create_channel_fmtd}).json()
    try:
        channel_id = nr_response['data']['aiNotificationsCreateChannel']['channel']['id']
        logger.info(f'Platform API channel created. ID: {channel_id}\n')
    except KeyError:
        logger.warning(nr_response)

    return channel_id


def get_policy_ids(endpoint, headers, client_name, account_id, logger):
    workflow_count = 0
    create_catchall = True
    policy_ids_set = set()
    workflow_ids_set = set()
    workflows_to_check = []

    non_critical_destinations = ['Moogsoft_Ingestion_QA_tf',
                                 'Moogsoft_Ingestion_tf',
                                 '2W Platform API',
                                 'MCS Platform',
                                 'mcs-tooling-nr-migration-test']

    # If needed because we want to send all policy alerts to Platform, instead of only the ones that are currently
    # sending alerts
    # policies_query = Template("""
    # {
    #   actor {
    #     account(id: $account_id) {
    #       alerts {
    #         policiesSearch {
    #           policies {
    #             id
    #             name
    #           }
    #         }
    #       }
    #     }
    #   }
    # }
    # """)
    #
    # policies_query_fmtd = policies_query.substitute({'account_id': account_id})
    # policies_response = requests.post(endpoint,
    #                                   headers=headers,
    #                                   json={'query': policies_query_fmtd}).json()
    #
    # policies_count = len(policies_response['data']['actor']['account']['alerts']['policiesSearch']['policies'])
    # logger.info(f'There are {policies_count} alert policies for this account.')

    workflows_query = Template("""
    {
      actor {
        account(id: $account_id) {
          aiWorkflows {
            workflows {
              entities {
                id
                name
                destinationConfigurations {
                  name
                  type
                  notificationTriggers
                }
                issuesFilter {
                  predicates {
                    attribute
                    operator
                    values
                  }
                }
              }
            }
          }
        }
      }
    }
    """)

    workflows_query_fmtd = workflows_query.substitute({'account_id': account_id})
    workflows_response = requests.post(endpoint,
                                       headers=headers,
                                       json={'query': workflows_query_fmtd}).json()

    for workflow in workflows_response['data']['actor']['account']['aiWorkflows']['workflows']['entities']:
        workflow_count += 1
        workflow_name = workflow['name']
        goes_to_platform = False
        destination_names = []

        if 'Platform' in workflow_name:
            logger.warning('A Platform catchall workflow already exists for this account.')
            create_catchall = False
            continue
        else:
            for destination in workflow['destinationConfigurations']:
                destination_name = destination['name']
                destination_names.append(destination_name)

                if 'Platform' in destination_name:
                    goes_to_platform = True
                    if workflow['issuesFilter']['predicates']:
                        for predicate in workflow['issuesFilter']['predicates']:
                            if predicate['attribute'] == 'labels.policyIds':
                                values = predicate['values']
                                for value in values:
                                    # Add to set of policy IDs to be added to catchall workflow
                                    policy_ids_set.add(value)

        # Evaluate whether workflow should be disabled
        subtract = 0
        for name in destination_names:
            if name in non_critical_destinations or 'Moog' in name or 'moog' in name or 'OpsRamp' in name:
                subtract += 1
            else:
                continue

        critical_destinations = len(destination_names) - subtract
        if (goes_to_platform and critical_destinations == 0) or critical_destinations == 0:
            logger.info(f'Workflow ({workflow_name}) can be safely disabled:\n   Goes to Platform? {goes_to_platform}'
                        f'\n   Destination names: {destination_names}')
            # Add to set of workflow IDs to be disabled after catchall creation
            workflow_ids_set.add(workflow['id'])
        else:
            logger.info(f'Workflow ({workflow_name}) should be manually checked:\n   Goes to Platform? '
                        f'{goes_to_platform}\n   Destination names: {destination_names}')
            workflows_to_check.append(f'{client_name} {account_id}: {workflow_name}')

    policy_ids_list = list(policy_ids_set)
    workflow_ids_list = list(workflow_ids_set)
    logger.info(f'\n{len(policy_ids_list)} policy IDs sending alerts to Platform: {policy_ids_list}')
    logger.info(f'Create catchall for {client_name}? {create_catchall}')
    if create_catchall:
        logger.info(f'\nThere are {workflow_count} workflows:')
        logger.info(f'   There are {len(workflow_ids_list)} workflows to disable: {workflow_ids_list}')
        logger.info(f'   There are {len(workflows_to_check)} workflows to manually check:')
        for wf in workflows_to_check:
            logger.info(f'      {wf}')

    return policy_ids_list, create_catchall, workflow_ids_list, workflows_to_check


def create_workflow(endpoint, headers, account_id, channel_id, policy_ids_list, logger):

    channel_id = json.dumps(channel_id)
    # test_policy_ids = json.dumps(['4569885'])
    policy_ids_list = json.dumps(policy_ids_list)

    nrql_create_workflow = Template("""
    mutation {
      aiWorkflowsCreateWorkflow(
        accountId: $account_id
        createWorkflowData: {
          destinationConfigurations: {
            channelId: $channel_id, 
            notificationTriggers: [ACTIVATED, ACKNOWLEDGED, CLOSED]
          }, 
          mutingRulesHandling: DONT_NOTIFY_FULLY_MUTED_ISSUES, 
          name: "MCS Platform", 
          workflowEnabled: true, 
          destinationsEnabled: true,
          issuesFilter: {
            type: FILTER,
            predicates: [
              {
                attribute: "labels.policyIds",
                operator: EXACTLY_MATCHES,
                values: $policy_ids_list
              },
              {
                attribute: "priority",
                operator: EQUAL,
                values: [
                  "CRITICAL"
                ]
              }
            ]
          }
        }
      ) {
        workflow {
          id
          name
        }
      }
    }
    """)

    create_workflow_fmtd = nrql_create_workflow.substitute({'account_id': account_id,
                                                            'channel_id': channel_id,
                                                            'policy_ids_list': policy_ids_list})
    nr_response = requests.post(endpoint,
                                headers=headers,
                                json={'query': create_workflow_fmtd}).json()

    try:
        workflow_id = nr_response['data']['aiWorkflowsCreateWorkflow']['workflow']['id']
        logger.info(f'\nMCS Platform workflow successfully created. ID: {workflow_id}')
        return 0
    except KeyError:
        logger.warning(nr_response)
        return 1


def disable_workflows(endpoint, headers, account_id, workflow_ids_list, logger):
    logger.info(f'\nDisabling {len(workflow_ids_list)} existing workflows...')
    nrql_disable_workflow = Template("""
        mutation {
          aiWorkflowsUpdateWorkflow(
            accountId: $account_id
            updateWorkflowData: {id: "$workflow_id", workflowEnabled: false}
          ) {
            workflow {
              id
            }
          }
        }
        """)

    for workflow_id in workflow_ids_list:
        disable_workflow_fmtd = nrql_disable_workflow.substitute({'account_id': account_id,
                                                                  'workflow_id': workflow_id})
        nr_response = requests.post(endpoint,
                                    headers=headers,
                                    json={'query': disable_workflow_fmtd}).json()

        try:
            workflow_id = nr_response['data']['aiWorkflowsUpdateWorkflow']['workflow']['id']
            logger.info(f'  Workflow ID {workflow_id} successfully disabled.')
        except KeyError:
            logger.warning(nr_response)
            return 1

    return 0
