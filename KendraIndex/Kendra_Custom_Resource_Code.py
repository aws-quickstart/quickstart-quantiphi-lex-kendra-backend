import boto3
import logging
import json
import os
import requests
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)

client = boto3.client('kendra','us-east-1')
client_lambda = boto3.client('lambda','us-east-1')
client_ssm = boto3.client('ssm','us-east-1')
client_lex = boto3.client('lex-models','us-east-1')

def sendResponse(event, context, responseStatus):
    responseBody = {
        'Status': responseStatus,
        'Reason': 'See the details in CloudWatch Log Stream: ' \
            + context.log_stream_name,
        'PhysicalResourceId': context.log_stream_name,
        'StackId': event['StackId'],
        'RequestId': event['RequestId'],
        'LogicalResourceId': event['LogicalResourceId'],
        }
    print ('RESPONSE BODY:n' + json.dumps(responseBody))
    try:
        req = requests.put(event['ResponseURL'],
                           data=json.dumps(responseBody))
        if req.status_code != 200:
            print (req.text)
            raise Exception('Received non 200 response while sending response to CFN.'
                            )
        return
    except requests.exceptions.RequestException as e:
        print (req.text)
        print (e)
        raise

def handler(event, context):
    responseData = {}
    if event['RequestType'] == 'Delete':
        try:            
            response_ssm_id = client_ssm.get_parameter(
                Name='/dev/index/kendraindexid'
            )
            response = client.delete_index(
                Id= response_ssm_id['Parameter']['Value']
            )
            # response_bot = client_lex.get_bot(
            #     name=os.environ['BotName'],
            #     versionOrAlias='$LATEST'
            # )
            # response_del_intent = []
            # for i in response_bot['intents']:
            #     response_del_intent.append(client_lex.delete_intent(
            #         name=i['intentName']
            #     ))
            responseStatus = 'SUCCESS'
            sendResponse(event, context, responseStatus)
        except Exception as e:
            logger.info('Deletion Error')
            logger.info(e)
            responseStatus = 'SUCCESS'
            sendResponse(event,context, responseStatus)
        return

    print("Received event: " + json.dumps(event, indent=2))
    try:
        response_kendra = client.create_index(
            Name = os.environ['KendraIndexName'],
            Edition= os.environ['Edition'],
            RoleArn= os.environ['RoleARN'],
            Description='Kendra Index for Chat bot created using Lex',
            Tags=[
            {
               'Key': 'Name',
               'Value': 'Sarvesh'
            },
            {
               'Key': 'Email',
               'Value': 'sarvesh.virkud@quantiphi.com'
            }
            ]
        )
        time.sleep(5)
        responseData['IndexID'] = response_kendra['Id']
        logger.info('IndexID:'+response_kendra['Id'])

        response = client_ssm.put_parameter(
            Name='/dev/index/kendraindexid',
            Description='Index ID for Kendra',
            Value=response_kendra['Id'],
            Type='String',
            Overwrite=True
        )
        logger.info('Parameter Store Success')
        time.sleep(800)
        responseStatus = 'SUCCESS'
        sendResponse(event, context, responseStatus)
    except Exception as e:
        logger.info('Index Creation Error')
        logger.info(e)
        responseStatus = 'FAILED'
        sendResponse(event,context, responseStatus)