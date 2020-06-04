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
client_sqs = boto3.client('sqs',os.environ['AWS_REGION'])
client_ssm = boto3.client('ssm',os.environ['AWS_REGION'])
s3 = boto3.client('s3',os.environ['AWS_REGION'])

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

def linkDataSource(indexID, event, context):
    try:
        response_data_source = client.create_data_source(
            Name= os.environ['DataSourceName'],
            IndexId=indexID,
            Type='S3',
            Configuration={
                'S3Configuration': {
                    'BucketName': os.environ['KendraS3Bucket'],
                    'ExclusionPatterns': [
                        '*faq*',
                        '*FAQ*'
                    ]
                },
            },
            Description='Lex-Kendra-bot Data Source',
            RoleArn=os.environ['RoleARN']
        )
        logger.info('DataSourceID:'+response_data_source['Id'])
        response_sync = client.start_data_source_sync_job(
            Id=response_data_source['Id'],
            IndexId=indexID
        )
        time.sleep(20)
        response_faq = client.create_faq(
            IndexId=indexID,
            Name=os.environ['FAQName'],
            Description='FAQs for COVID-19',
            S3Path={
                'Bucket': os.environ['KendraS3Bucket'],
                'Key': os.environ['FAQFileKey']
            },
            RoleArn=os.environ['RoleARN']
        )
        logger.info('FAQID:'+response_faq['Id'])
        time.sleep(5)
        response = client_ssm.put_parameter(
            Name='/dev/index/kendra-data-source-id',
            Description='Data Source ID for Kendra Index',
            Value=response_data_source['Id'],
            Type='String',
            Overwrite=True
        )

        response = client_ssm.put_parameter(
            Name='/dev/index/kendra-faq-id',
            Description='FAQ ID for Kendra Index',
            Value=response_faq['Id'],
            Type='String',
            Overwrite=True
        )
        logger.info('DataSync Completed')
        responseStatus = 'SUCCESS'
        sendResponse(event, context, responseStatus)
    except Exception as e:
        logger.info('DataSync Failed')
        logger.info(e)
        responseStatus = 'FAILED'
        sendResponse(event,context, responseStatus)

def handler(event, context):
    if 'RequestType' in event and event['RequestType'] == 'Delete':
        try:
            response_ssm_index_id = client_ssm.get_parameter(
                Name='/dev/index/kendraindexid'
            )

            response_ssm_datasource_id = client_ssm.get_parameter(
                Name='/dev/index/kendra-data-source-id'
            )

            response_ssm_faq_id = client_ssm.get_parameter(
                Name='/dev/index/kendra-faq-id'
            )

            response_data_source = client.delete_data_source(
                Id = response_ssm_datasource_id['Parameter']['Value'],
                IndexId = response_ssm_index_id['Parameter']['Value']
            )

            response = client.delete_faq(
                Id= response_ssm_faq_id['Parameter']['Value'],
                IndexId = response_ssm_index_id['Parameter']['Value']
            )

            responseStatus = 'SUCCESS'
            sendResponse(event, context, responseStatus)
        except Exception as e:
            logger.info('Deletion Error')
            logger.info(e)
            responseStatus = 'SUCCESS'
            sendResponse(event,context, responseStatus)
        return
    
    elif 'RequestType' in event and event['RequestType'] == 'Create': 
        print("Received event CFT: " + json.dumps(event, indent=2))
        try:
            response_ssm_id = client_ssm.get_parameter(
                Name='/dev/index/kendraindexid'
            )
            IndexID = response_ssm_id['Parameter']['Value']

            response_kendra = client.describe_index(
                Id=IndexID
            )

            if response_kendra['Status'] == 'CREATING':
                time.sleep(720)
                logger.info('Sleep Completed')
                response_s3 = s3.list_objects(
                    Bucket= os.environ['S3CodeBucket'],
                    Prefix='status_sync_count'
                )
                time.sleep(20)
                logger.info(response_s3)
                if 'Contents' in response_s3 and len(response_s3['Contents']) > 0:
                    status_sync = s3.get_object(Bucket=os.environ['S3CodeBucket'],Key='status_sync_count.json')
                    logger.info('status_sync-'+status_sync)
                    serializedObject = status_sync['Body'].read()
                    logger.info('SerializedOb-'+serializedObject)
                    myData = json.loads(serializedObject)
                    logger.info('Data-'+myData)
                    if myData["counter"] > 4:
                        responseStatus = 'FAILED'
                        sendResponse(event,context, responseStatus)
                    myData["counter"] = myData["counter"] + 1
                    serializedMyData = json.dumps(myData)
                    s3.put_object(Bucket=os.environ['S3CodeBucket'], Key='status_sync_count.json', Body = serializedMyData)
                    logger.info('Status File Updated')
                elif 'Contents' not in response_s3:
                    myData = {'counter': 1}
                    serializedMyData = json.dumps(myData)
                    s3.put_object(Bucket=os.environ['S3CodeBucket'], Key='status_sync_count.json', Body = serializedMyData)
                    logger.info('Status file Created')
                
                response_lambda = client_lambda.invoke(
                    FunctionName='KendraDataSyncOperationsFunctiontest',
                    Payload=json.dumps(event)
                )
            elif response_kendra['Status'] == 'ACTIVE':
                response = s3.delete_object(
                    Bucket=os.environ['S3CodeBucket'],
                    Key='status_sync_count.json'
                )
                linkDataSource(IndexID, event, context)
        except Exception as e:
            logger.info('Creation Error')
            logger.info(e)
            responseStatus = 'FAILED'
            sendResponse(event,context, responseStatus)