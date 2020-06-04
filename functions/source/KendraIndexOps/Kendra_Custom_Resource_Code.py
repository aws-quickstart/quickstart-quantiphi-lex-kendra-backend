import boto3
import logging
import json
import os
import requests
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)

client = boto3.client('kendra',os.environ['AWS_REGION'])
client_lambda = boto3.client('lambda',os.environ['AWS_REGION'])
client_ssm = boto3.client('ssm',os.environ['AWS_REGION'])
client_lex = boto3.client('lex-models',os.environ['AWS_REGION'])

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
            Description='Kendra Index for Chat bot created using Lex'
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
        time.sleep(780)
        responseStatus = 'SUCCESS'
        sendResponse(event, context, responseStatus)
    except Exception as e:
        logger.info('Index Creation Error')
        logger.info(e)
        responseStatus = 'FAILED'
        sendResponse(event,context, responseStatus)