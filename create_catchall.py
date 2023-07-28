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
                logger.info(f'Platform API destination ID: {destination_id}')

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
            name: "alex actual final test",
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
              name
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
        logger.info(f'Platform API orphan channel ID: {channel_id}')
    except KeyError:
        logger.warning(nr_response)

    return channel_id


def get_policy_ids(endpoint, headers, account_id, logger):
    policy_ids_list = []

    workflows_query = Template("""
    {
      actor {
        account(id: $account_id) {
          aiWorkflows {
            workflows(filters: {destinationType: WEBHOOK}) {
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
    nr_response = requests.post(endpoint,
                                headers=headers,
                                json={'query': workflows_query_fmtd}).json()

    for workflow in nr_response['data']['actor']['account']['aiWorkflows']['workflows']['entities']:
        goes_to_platform = False
        for destination in workflow['destinationConfigurations']:
            if 'Platform' in destination['name']:
                logger.info(f'Workflow {workflow["name"]} is sending alerts to Platform.')
                goes_to_platform = True

            if goes_to_platform:
                if workflow['issuesFilter']['predicates']:
                    for predicate in workflow['issuesFilter']['predicates']:
                        if predicate['attribute'] == 'labels.policyIds':
                            values = predicate['values']
                            for value in values:
                                policy_ids_list.append(value)

        # TODO: insert logic to determine if a workflow needs to be disabled
        # TODO: have some way to separate out anything needing a manual check in case logic somehow misses

    logger.info(f'Policy IDs sending alerts to Platform: {policy_ids_list}')

    return policy_ids_list


def create_workflow(endpoint, headers, account_id, channel_id, policy_ids_list, logger):
    workflow_id = ''

    channel_id = json.dumps(channel_id)
    # test_policy_ids = json.dumps(['4569885'])

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
          name: "alex test 3", 
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
        logger.info(f'Platform API workflow ID: {workflow_id}')
    except KeyError:
        logger.warning(nr_response)

    return workflow_id


def create_catchall_workflow(client_name, account_id, logger):
    endpoint = 'https://api.newrelic.com/graphql'
    headers = {
        'Content-Type': 'application/json',
        'API-Key': 'NRAK-7DVT82DILPFIAXSZZ6CLPKYB8YU',
    }

    # get all destination IDs from an account and find the ID for '2W Platform API'
    destination_id = get_destination_id(endpoint, headers, account_id, logger)

    # TODO: create a new channel for '2W Platform API' destination
    # channel_id = create_channel(endpoint, headers, destination_id, account_id, logger)

    # TODO: get all workflows that currently use the '2W Platform API' webhook except any with 'Platform' in the name;
    #   return a list of policy IDs & list of workflow IDs
    policy_ids_list = get_policy_ids(endpoint, headers, account_id, logger)

    # TODO: create a new workflow called 'MCS Platform' & associate policies
    # workflow_id = create_workflow(endpoint, headers, account_id, channel_id, policy_ids_list, logger)

    # TODO: disable appropriate policies
    # pass in workflow IDs

    return 0
