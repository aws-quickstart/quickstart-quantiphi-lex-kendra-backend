
var AWS = require('aws-sdk')
var CfnLambda = require('cfn-lambda')

var LexModelBuildingService = new AWS.LexModelBuildingService({
  apiVersion: '2017-04-19'
})

const boolProperties = [
  'childDirected'
]

const numProperties = [
  'clarificationPrompt.maxAttempts',
  'idleSessionTTLInSeconds'
]

const Upsert = CfnLambda.SDKAlias({
  api: LexModelBuildingService,
  forceNums: numProperties,
  forceBools: boolProperties,
  method: 'putBot',
  returnPhysicalId: 'name',
  returnAttrs: [
    'version',
    'checksum'
  ]
})

const Update = function (RequestPhysicalID, CfnRequestParams, OldCfnRequestParams, reply) {
  const sameName = CfnRequestParams.name === OldCfnRequestParams.name
  function go () {
    Upsert(RequestPhysicalID, CfnRequestParams, OldCfnRequestParams, reply)
  }
  if (CfnRequestParams.checksum || !sameName) {
    return go()
  }
  getBotAttrs(OldCfnRequestParams, function (err, attrs) {
    if (err) {
      return reply(err)
    }
    console.log('Checksum value: %s', attrs.checksum)
    CfnRequestParams.checksum = attrs.checksum
    go()
  })
}

const Delete = CfnLambda.SDKAlias({
  api: LexModelBuildingService,
  method: 'deleteBot',
  keys: ['name'],
  ignoreErrorCodes: [404, 409]
})

const NoUpdate = function (PhysicalResourceId, CfnResourceProperties, reply) {
  getBotAttrs(CfnResourceProperties, function (err, attrs) {
    if (err) {
      return next(err)
    }
    reply(null, PhysicalResourceId, attrs)
  })
}

exports.handler = CfnLambda({
  Create: Upsert,
  Update: Update,
  Delete: Delete,
  NoUpdate: NoUpdate
})

function getBotAttrs (props, next) {
  const latestVersion = '$LATEST'
  const BotParams = {
    name: props.name,
    version: latestVersion
  }
  LexModelBuildingService.getBot(BotParams, function (err, BotData) {
    if (err) {
      return next(err.code + ': ' + err.message)
    }
    const BotReplyAttrs = {
      checksum: BotData.checksum,
      version: latestVersion
    }
    next(null, BotReplyAttrs)
  })
}
