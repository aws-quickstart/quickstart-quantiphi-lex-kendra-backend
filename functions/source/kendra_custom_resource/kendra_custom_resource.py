"""
Python script for Lambda backed custom resource to create/delete:
Kendra Index
Data source for Kendra Index
FAQ for Kendra Index
"""
import os
import logging
import boto3
import time
from botocore import exceptions as botocore_exceptions
from boto3 import exceptions as boto3_exceptions
from crhelper import CfnResource

logger = logging.getLogger(__name__)
helper = CfnResource(json_logging=False, log_level='DEBUG',
                     boto_level='CRITICAL', sleep_on_delete=120)

try:
    kendra_client = boto3.client('kendra', os.environ['AWS_REGION'])
    cloudformation_client = boto3.client('cloudformation', os.environ['AWS_REGION'])
except (botocore_exceptions.BotoCoreError, botocore_exceptions.ClientError,
        boto3_exceptions.Boto3Error) as exception:
    helper.init_failure(exception)


def check_required_properties(dictionary, key):
    """
    Check if a key is present in dictionary,
    otherwise raise KeyError stating "key is a required property"
    :param dictionary: Dictionary
    :param key: Key
    :return: None or KeyError
    """
    if key not in dictionary:
        raise KeyError(key + " is a required property")


def create_kendra_index(resource_properties):
    """
    Creates Kendra Index
    :param resource_properties: Dictionary of resources properties.
                                IndexName, Edition and IndexRoleArn are mandatory.
    :return: Kendra Index Id
    """
    kwargs = {
        'Name': resource_properties['IndexName'],
        'Edition': resource_properties['Edition'],
        'RoleArn': resource_properties['IndexRoleArn']
    }
    if 'IndexDescription' in resource_properties:
        kwargs['Description'] = resource_properties['IndexDescription']
    else:
        kwargs['Description'] = "Kendra Index for Chat bot created using Lex"
    response_kendra = kendra_client.create_index(**kwargs)
    logger.info('IndexID: %s', str(response_kendra['Id']))
    return response_kendra['Id']


@helper.create
def create(event, _):
    """
    Helper function for resource creation.
    Populates Data with Kendra Index Id so poll_create helper can refer to it.
    Raises Exception if required resource properties are missing.
    Any exception raised is displayed in CloudFormation console.
    :param event: Event body
    :param _: Context (unused)
    :return: None
    """
    logger.info("Got Create")

    if 'ResourceProperties' not in event:
        raise ValueError("Please provide resource properties")
    required_properties = ['IndexName',
                           'Edition',
                           'IndexRoleArn',
                           'DataSourceName',
                           'KendraS3Bucket',
                           'DataSourceRoleArn',
                           'FAQName',
                           'FAQRoleArn',
                           'FAQFileKey']
    for resource_property in required_properties:
        check_required_properties(event['ResourceProperties'], resource_property)

    kendra_index_id = create_kendra_index(event['ResourceProperties'])

    # To add response data update the helper.Data dict
    # If poll is enabled data is placed into poll event as event['CrHelperData']
    helper.Data['KendraIndexId'] = kendra_index_id


def delete_kendra_index(kendra_index_id):
    """
    Deletes Kendra index and associated Data Sources/FAQs
    :param kendra_index_id: Kendra Index Id
    :return: None
    """
    kendra_client.delete_index(Id=kendra_index_id)


@helper.update
def update(*_):
    """
    Helper function for resource updates.
    Updates are not supported for Kendra custom resource.
    :param _: Unused
    :return: None
    """
    cft_response = cloudformation_client.describe_stacks(
        StackName=helper.StackId
    )
    stack_status = cft_response['Stacks'][0]['StackStatus']
    if stack_status == 'UPDATE_IN_PROGRESS':
        raise Exception("Updates are not supported for Kendra Custom Resource")
    return helper.PhysicalResourceId  # Return if update rollback is in progress


@helper.delete
def delete(event, _):
    """
    Helper function for resource deletion.
    Should not fail if the underlying resources are already deleted.
    :param event: Event body
    :param _: Context (Unused)
    :return: None
    """
    logger.info("Got Delete")
    delete_kendra_index(event['PhysicalResourceId'])


def check_kendra_index_status(kendra_index_id):
    """
    Checks status of kendra index.
    Raises an exception if Kendra Index is in an unexpected state.
    :param kendra_index_id: Kendra Index Id
    :return: True if index is Active, False otherwise
    """
    response = kendra_client.describe_index(Id=kendra_index_id)
    status = response['Status']
    logger.info(status)
    if status == 'DELETING':
        raise Exception("Kendra Index is in DELETING state")
    if status == 'FAILED':
        raise Exception("Kendra Index is in FAILED state with Error Message: "
                        + response['ErrorMessage'])
    return status == 'ACTIVE'


def create_kendra_data_source(kendra_index_id, resource_properties):
    """
    Creates Kendra data source.
    :param kendra_index_id: Kendra Index Id
    :param resource_properties: Dictionary of resources properties.
                                DataSourceName, KendraS3Bucket and DataSourceRoleArn are mandatory.
    :return: Data Source Id
    """
    data_source_kwargs = {
        'Name': resource_properties['DataSourceName'],
        'IndexId': kendra_index_id,
        'Type': 'S3',
        'Configuration': {
            'S3Configuration': {
                'BucketName': resource_properties['KendraS3Bucket'],
                'ExclusionPatterns': [
                    '*faq*',
                    '*FAQ*'
                ]
            },
        },
        'RoleArn': resource_properties['DataSourceRoleArn']
    }
    if 'IndexDescription' in resource_properties:
        data_source_kwargs['Description'] = resource_properties['IndexDescription']
    else:
        data_source_kwargs['Description'] = "Lex-Kendra-bot Data Source"
    
    try:
        response_data_source = kendra_client.create_data_source(**data_source_kwargs)
    except:
        time.sleep(15)
        response_data_source = kendra_client.create_data_source(**data_source_kwargs)
    logger.info('DataSourceId: %s', str(response_data_source['Id']))
    return response_data_source['Id']


def start_data_source_sync_job(kendra_index_id, data_source_id):
    """
    Starts Data Source Sync Job
    :param kendra_index_id: Kendra Index Id
    :param data_source_id: Data Source Id
    :return: Sync Execution Id
    """
    response_sync = kendra_client.start_data_source_sync_job(
        Id=data_source_id,
        IndexId=kendra_index_id
    )
    logger.info('ExecutionId: %s', str(response_sync['ExecutionId']))
    return response_sync['ExecutionId']


def create_kendra_faq(kendra_index_id, resource_properties):
    """
    Creates FAQ.
    :param kendra_index_id: Kendra Index Id
    :param resource_properties: Dictionary of resources properties.
                                FAQName, KendraS3Bucket, FAQFileKey and FAQRoleArn are mandatory.
    :return: FAQ Id
    """
    faq_kwargs = {
        'Name': resource_properties['FAQName'],
        'IndexId': kendra_index_id,
        'S3Path': {
            'Bucket': resource_properties['KendraS3Bucket'],
            'Key': resource_properties['FAQFileKey']
        },
        'RoleArn': resource_properties['FAQRoleArn']
    }
    if 'FAQDescription' in resource_properties:
        faq_kwargs['Description'] = resource_properties['FAQDescription']
    else:
        faq_kwargs['Description'] = "FAQs for COVID-19"
    response_faq = kendra_client.create_faq(**faq_kwargs)
    logger.info('FAQId: %s', str(response_faq['Id']))
    return response_faq['Id']


@helper.poll_create
def poll_create(event, _):
    """
    Helper function for resource creation, triggered every 2 minutes till resource is created.
    Populates Data with Data Source Id, Sync Execution Id and FAQ Id.
    Any exception raised is displayed in CloudFormation console.
    :param event: Event body
    :param _: Context (unused)
    :return: None if Index is still being created.
             Physical Resource (Kendra IndexId) upon successful completion.
    """
    logger.info("Got create poll")
    kendra_index_id = event['CrHelperData']['KendraIndexId']
    if not check_kendra_index_status(kendra_index_id):
        return None

    data_source_id = create_kendra_data_source(kendra_index_id, event['ResourceProperties'])
    helper.Data['DataSourceId'] = data_source_id

    helper.Data['SyncExecutionId'] = start_data_source_sync_job(kendra_index_id, data_source_id)

    helper.Data['FAQId'] = create_kendra_faq(kendra_index_id, event['ResourceProperties'])

    return kendra_index_id


def lambda_handler(event, context):
    """
    Base lambda handler.
    :param event: Event body passed to Lambda
    :param context: Context passed to Lambda
    :return: None
    """
    helper(event, context)
