targetScope = 'resourceGroup'

@description('Azure region for deployed resources')
param location string = resourceGroup().location

@description('Short name prefix, e.g. ncccomp-dev')
param namePrefix string

@description('Existing Microsoft Foundry (Cognitive Services) resource ID')
param foundryResourceId string

@description('Container image for the API tier')
param containerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

@description('Optional tags applied to all resources')
param tags object = {
  project: 'foundry-experiment'
  environment: 'dev'
}

module storage 'modules/storage.bicep' = {
  name: 'storage'
  params: {
    location: location
    namePrefix: namePrefix
    tags: tags
  }
}

module containerApp 'modules/container-app.bicep' = {
  name: 'container-app'
  params: {
    location: location
    namePrefix: namePrefix
    tags: tags
    containerImage: containerImage
    storageAccountName: storage.outputs.storageAccountName
    foundryResourceId: foundryResourceId
  }
}

module staticWebApp 'modules/static-web-app.bicep' = {
  name: 'static-web-app'
  params: {
    location: location
    namePrefix: namePrefix
    tags: tags
  }
}

output storageAccountName string = storage.outputs.storageAccountName
output blobEndpoint string = storage.outputs.blobEndpoint
output apiFqdn string = containerApp.outputs.containerAppFqdn
output staticWebAppHostname string = staticWebApp.outputs.staticWebAppDefaultHostname
output foundryResourceId string = foundryResourceId
