from string import Template
import requests


def create_channel(destination_id, account_id, logger):
    # key = 'payload'
    channel_payload = """
        {\n\"alert_level\": \"{{#if issueClosedAt}}closed{{else if 
        issueAcknowledgedAt}}acknowledged{{else}}open{{/if}}-{{escape accumulations.conditionName.[0]}}\",
        \n\"current_state\": \"{{#if issueClosedAt}}closed{{else if issueAcknowledgedAt}}acknowledged{{else}}open{{
        /if}}\",\n\"description\": {\n\"account_id\": {{nrAccountId}},\n\"account_name\": \"{{accumulations.tag.account.[
        0]}}\",\n\"condition_id\": {{accumulations.conditionFamilyId.[0]}},\n\"condition_name\": \"{{escape 
        accumulations.conditionName.[0]}}\",\n\"current_state\": \"{{#if issueClosedAt}}closed{{else if 
        issueAcknowledgedAt}}acknowledged{{else}}open{{/if}}\",\n\"details\": \"{{escape issueTitle}}\",\n\"event_type\": 
        \"INCIDENT\",\n\"incident_acknowledge_url\": \"<a href={{issuePageUrl}}>{{issuePageUrl}}</a>\",\n\"incident_id\": 
        {{#if labels.nrIncidentId}}{{labels.nrIncidentId.[0]}}{{else}}-1{{/if}},\n\"incident_url\": \"{{issuePageUrl}}\",
        \n\"owner\": \"{{owner}}\",\n\"policy_name\": \"{{escape accumulations.policyName.[0]}}\",\n\"policy_url\": \"{{
        policyUrl}}\",\n\"runbook_url\": \"<a href={{accumulations.runbookUrl.[0]}}>{{accumulations.runbookUrl.[
        0]}}</a>\",\n\"severity\": \"{{#eq 'HIGH' priority}}WARNING{{else}}{{priority}}{{/eq}}\",\n\"timestamp\": {{
        updatedAt}}\n  },\n\"details\": \"{{escape issueTitle}}\",\n\"metric\": \"{{escape accumulations.policyName.[
        0]}}\",\n\"severity\": \"{{#eq 'HIGH' priority}}WARNING{{else}}{{priority}}{{/eq}}\",\n\"targets\": [\n { 
        \n\"id\": \"{{labels.targetId.[0]}}\",\n\"name\": \"{{#if accumulations.targetName}}{{escape 
        accumulations.targetName.[0]}}{{else if entitiesData.entities}}{{escape entitiesData.entities.[0].name}}{{
        else}}N/A{{/if}}\",\n\"link\": \"{{issuePageUrl}}\",\n\"product\": \"{{accumulations.conditionProduct.[0]}}\",
        \n\"type\": \"{{#if entitiesData.types.[0]}}{{entitiesData.types.[0]}}{{else}}N/A{{/if}}\",\n\"labels\": { {{
        #each accumulations.rawTag}}\"{{escape @key}}\": {{#if this.[0]}}{{json this.[0]}}{{else}}\"empty\"{{/if}}{{
        #unless @last}},{{/unless}}{{/each}}\n } \n} \n ],\n\"timestamp\": {{updatedAt}}\n}
        """

    nr_gql_create_channel = Template("""
        mutation {
          aiNotificationsCreateChannel(accountId: $account_id, channel: {
            type: WEBHOOK,
            name: "2W Platform API",
            destinationId: $destination_id,
            product: IITL,
            properties: [
              {
              key:"payload",
              value: "$payload"
              },
              {
              key:"headers",
              value:"{\"x-api-key\":\"09b99595-8aef-45f7-99af-54e823a59895\"}"
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

    workflow_query_fmtd = nr_gql_create_channel.substitute({'account_id': account_id})
    nr_response = requests.post(nr_endpoint,
                                headers=nr_headers,
                                json={'query': workflow_query_fmtd}).json()

    return


def create_catchall_workflow(client_name, account_id, logger):

    # TODO: get all workflow IDs from an account and find the ID for '2W Platform API'
    platform_destination_id = ''
    nr_endpoint = 'https://api.newrelic.com/graphql'
    nr_headers = {
        'Content-Type': 'application/json',
        'API-Key': 'NRAK-7DVT82DILPFIAXSZZ6CLPKYB8YU',
    }

    nr_gql_destinations_query = Template("""
    {
      actor {
        account(id: $account_id) {
          aiNotifications {
            destinations(filters: {name: "2W Platform API"}) {
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

    destinations_query_fmtd = nr_gql_destinations_query.substitute({'account_id': account_id})
    nr_response = requests.post(nr_endpoint,
                                headers=nr_headers,
                                json={'query': destinations_query_fmtd}).json()

    destinations_list = nr_response['data']['actor']['account']['aiNotifications']['destinations']['entities']
    if destinations_list:
        platform_destination_id = destinations_list[0]['id']

    # TODO: get all policy IDs that currently use the '2W Platform API' webhook in a workflow except any named
    #  'Platform Catchall'

    # TODO: create a new channel for '2W Platform API' destination

    channel_id = create_channel(platform_destination_id, account_id, logger)

    return 0
