
var AWS = require('aws-sdk')
var CfnLambda = require('cfn-lambda')

var LexModelBuildingService = new AWS.LexModelBuildingService({
  apiVersion: '2017-04-19'
})


const numProperties = [
  'confirmationPrompt.maxAttempts',
  'followUpPrompt.prompt.maxAttempts',
  'slots.*.priority',
  'slots.*.valueElicitationPrompt.maxAttempts'
]

const Upsert = CfnLambda.SDKAlias({
  api: LexModelBuildingService,
  forceNums: numProperties,
  method: 'putIntent',
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
  getIntentAttrs(OldCfnRequestParams, function (err, attrs) {
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
  method: 'deleteIntent',
  keys: ['name'],
  ignoreErrorCodes: [404, 409]
})

// const Delete = function(){
//   console.log('Over-riding')
// }

const NoUpdate = function (PhysicalResourceId, CfnResourceProperties, reply) {
  getIntentAttrs(CfnResourceProperties, function (err, attrs) {
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

function getIntentAttrs (props, next) {
  const latestVersion = '$LATEST'
  const IntentParams = {
    name: props.name,
    version: latestVersion
  }
  LexModelBuildingService.getIntent(IntentParams, function (err, IntentData) {
    if (err) {
      return next(err.code + ': ' + err.message)
    }
    const IntentReplyAttrs = {
      checksum: IntentData.checksum,
      version: latestVersion
    }
    console.log('Intent attributes: %j', IntentReplyAttrs)
    next(null, IntentReplyAttrs)
  })
}
