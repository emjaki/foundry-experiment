@description('Container Apps environment and API app')
param location string
param namePrefix string
param tags object = {}
param containerImage string
param storageAccountName string
param foundryResourceId string

var environmentName = '${namePrefix}-cae'
var appName = '${namePrefix}-api'

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${namePrefix}-logs'
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: environmentName
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

resource apiApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: appName
  location: location
  tags: tags
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
      }
      secrets: []
    }
    template: {
      containers: [
        {
          name: 'api'
          image: containerImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'ARTIFACTS_DIR'
              value: '/artifacts'
            }
            {
              name: 'USE_MOCK_EXTRACTION'
              value: 'false'
            }
            {
              name: 'USE_MOCK_KNOWLEDGE'
              value: 'false'
            }
            {
              name: 'DEFAULT_RULE_PACK'
              value: 'ncc-accessibility-v1'
            }
            {
              name: 'STORAGE_ACCOUNT_NAME'
              value: storageAccountName
            }
            {
              name: 'FOUNDRY_RESOURCE_ID'
              value: foundryResourceId
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

output containerAppFqdn string = apiApp.properties.configuration.ingress.fqdn
output logAnalyticsWorkspaceId string = logAnalytics.id
