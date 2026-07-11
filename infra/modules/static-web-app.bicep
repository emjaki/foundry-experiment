@description('Static Web App for the NCC compliance UI')
param location string = 'eastus2'
param namePrefix string
param tags object = {}
param repositoryUrl string = ''
param branch string = 'main'

var swaName = '${namePrefix}-swa'

resource staticWebApp 'Microsoft.Web/staticSites@2023-12-01' = {
  name: swaName
  location: location
  tags: tags
  sku: {
    name: 'Standard'
    tier: 'Standard'
  }
  properties: {
    repositoryUrl: empty(repositoryUrl) ? null : repositoryUrl
    branch: branch
    buildProperties: {
      appLocation: 'web'
      apiLocation: ''
      outputLocation: ''
    }
    stagingEnvironmentPolicy: 'Enabled'
  }
}

output staticWebAppName string = staticWebApp.name
output staticWebAppDefaultHostname string = staticWebApp.properties.defaultHostname
