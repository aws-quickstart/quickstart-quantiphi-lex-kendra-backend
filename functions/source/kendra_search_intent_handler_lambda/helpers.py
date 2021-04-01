"""
Helper function for Lex bot
"""
import logging
import json
import pprint
import os
import boto3
from botocore.exceptions import ClientError
from botocore.client import Config
import config as help_desk_config

logger = logging.getLogger()
logger.setLevel(logging.INFO)

kendra_client = boto3.client('kendra')


def get_slot_values(slot_values, intent_request):
    """
    Get slot values for each slot.
    :param slot_values: Slot values
    :param intent_request: Requested Intent
    :return: Slot values
    """
    if slot_values is None:
        slot_values = {key: None for key in help_desk_config.SLOT_CONFIG}

    slots = intent_request['currentIntent']['slots']

    for key, config in help_desk_config.SLOT_CONFIG.items():
        slot_values[key] = slots.get(key)
        logger.debug('<<help_desk_bot>> retrieving slot value for %s = %s', key, slot_values[key])
        if slot_values[key]:
            if config.get(
                    'type', help_desk_config.ORIGINAL_VALUE) == help_desk_config.TOP_RESOLUTION:
                # get the resolved slot name of what the user said/typed
                if len(intent_request['currentIntent']['slotDetails'][key]['resolutions']) > 0:
                    slot_values[key] = intent_request['currentIntent'][
                        'slotDetails'][key]['resolutions'][0]['value']
                else:
                    error_msg = help_desk_config.SLOT_CONFIG[key].get(
                        'error', 'Sorry, I don\'t understand "{}".')
                    raise help_desk_config.SlotError(error_msg.format(slots.get(key)))

    return slot_values


def get_remembered_slot_values(slot_values, session_attributes):
    """
    Get remembered slot values.
    :param slot_values: Slot values
    :param session_attributes: Session attributes
    :return: Remembered slot values
    """
    logger.debug(
        '<<help_desk_bot>> get_remembered_slot_values() - session_attributes: %s',
        session_attributes)

    remembered_slots = session_attributes.get('rememberedSlots')
    if remembered_slots is not None:
        remembered_slot_values = json.loads(remembered_slots)
    else:
        remembered_slot_values = {key: None for key in help_desk_config.SLOT_CONFIG}

    if slot_values is None:
        slot_values = {key: None for key in help_desk_config.SLOT_CONFIG}

    for key, config in help_desk_config.SLOT_CONFIG.items():
        if config.get('remember', False):
            logger.debug('<<help_desk_bot>> get_remembered_slot_values() - slot_values[%s] = %s',
                         key,
                         slot_values.get(key))
            logger.debug(
                '<<help_desk_bot>> get_remembered_slot_values() - remembered_slot_values[%s] = %s',
                key,
                remembered_slot_values.get(key))
            if slot_values.get(key) is None:
                slot_values[key] = remembered_slot_values.get(key)

    return slot_values


def remember_slot_values(slot_values, session_attributes):
    """
    Remember a slot value.
    :param slot_values: Slot values
    :param session_attributes: Session attributes
    :return: Updated slot values
    """
    if slot_values is None:
        slot_values = {key: None for key, config in help_desk_config.SLOT_CONFIG.items() if
                       config['remember']}
    session_attributes['rememberedSlots'] = json.dumps(slot_values)
    logger.debug('<<help_desk_bot>> Storing updated slot values: %s', slot_values)
    return slot_values


def get_latest_slot_values(intent_request, session_attributes):
    """
    Get latest slot values.
    :param intent_request: Requested Intent
    :param session_attributes: Session attributes
    :return: Latest slot values
    """
    slot_values = session_attributes.get('slot_values')

    try:
        slot_values = get_slot_values(slot_values, intent_request)
    except help_desk_config.SlotError as err:
        raise help_desk_config.SlotError(err)

    logger.debug('<<help_desk_bot>> "get_latest_slot_values(): slot_values: %s', slot_values)

    slot_values = get_remembered_slot_values(slot_values, session_attributes)
    debug_message = '<<help_desk_bot>> "get_latest_slot_values(): slot_values ' + \
                    'after get_remembered_slot_values: %s'
    logger.debug(debug_message, slot_values)

    remember_slot_values(slot_values, session_attributes)

    return slot_values


def close(session_attributes, fulfillment_state, message):
    """
    Get final response.
    :param session_attributes: Session attributes
    :param fulfillment_state: Fulfillment state
    :param message: Message
    :return: response to be returned by Lex chat bot
    """
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    logger.info(
        '<<help_desk_bot>> "Lambda fulfillment function response = %s', pprint.pformat(response,
                                                                                       indent=4))

    return response


def increment_counter(session_attributes, counter):
    """
    Increment counter value in session attribute.
    :param session_attributes: Session attributes
    :param counter: Key in session attribute
    :return: Updated count
    """
    counter_value = session_attributes.get(counter, '0')

    if counter_value:
        count = int(counter_value) + 1
    else:
        count = 1

    session_attributes[counter] = count

    return count


def create_presigned_url(bucket_name, object_name, expiration=604800):
    """
    Generate a presigned URL for S3 object.
    :param bucket_name: S3 Bucket name
    :param object_name: S3 object name
    :param expiration: Time after which link will expire
    :return: Signed URL
    """
    s3_client = boto3.client('s3', os.environ['AWS_REGION'],
                             config=Config(signature_version='s3v4'))
    try:
        response_s3 = s3_client.generate_presigned_url('get_object',
                                                       Params={'Bucket': bucket_name,
                                                               'Key': object_name},
                                                       ExpiresIn=expiration)
    except ClientError as client_error:
        logger.error(client_error)
        return None
    return response_s3


def question_result_type(response):
    """
    Generate the answer text for question result type.
    :param response: Kendra query response
    :return: Answer text
    """
    try:
        faq_answer_text = "On searching the Enterprise repository, I have found" \
                          " the following answer in the FAQs--"
        faq_answer_text += '\"' + response['resultItems'][0]['documentExcerpt']['text'] + '\"'
    except KeyError:
        faq_answer_text = "Sorry, I could not find an answer in our FAQs."

    return faq_answer_text


def answer_result_type(response):
    """
    Generate the answer text from the document, plus the URL link to the document.
    :param response: Kendra query response
    :return: Answer text
    """
    try:
        document_title = response['resultItems'][0]['documentTitle']['text']
        # document_excerpt_text = response['ResultItems'][0]['DocumentExcerpt']['Text']
        document_id = response['resultItems'][0]['documentId']
        document_text = response['resultItems'][0]['additionalAttributes'][0][
            'value']['textWithHighlightsValue']['text']
        pos = document_id.rindex("/")
        document_key = document_id[(pos + 1):]
        logger.info(document_key)
        document_url = create_presigned_url(os.environ['KENDRA_DATA_BUCKET'], document_key)
        if response['resultItems'][0]['additionalAttributes'][0][
                'value']['textWithHighlightsValue']['highlights'][0]['topAnswer']:
            begin = int(response['resultItems'][0]['additionalAttributes'][0][
                'value']['textWithHighlightsValue']['highlights'][0]['beginOffset'])
            end = int(response['resultItems'][0]['additionalAttributes'][0][
                'value']['textWithHighlightsValue']['highlights'][0]['endOffset'])
            topanswer = response['resultItems'][0]['additionalAttributes'][0][
                'value']['textWithHighlightsValue']['text']
            answer_text = "On searching the Enterprise repository, I have found" \
                          " the following answer as a top answer--"
            answer_text += "\nDocument Title: " + document_title
            # + " --- Excerpt: " + document_excerpt_text + ">"
            answer_text += '-- \"' + topanswer[begin:end] + '\"'
            answer_text += "\nHere is a document you could review- " + document_url + "\n"
        else:
            answer_text = "On searching the Enterprise repository, I have found" \
                          " the following answer in the suggested answers section"
            answer_text += " -- " + document_title + " --- \"" + document_text + "\""
            answer_text += "\n\n Here is a document you could review-" + document_url + "\n"
    except KeyError:
        answer_text = "\"Sorry, I could not find the answer in our documents.\""

    return answer_text


def document_result_type(response):
    """
    Assemble the list of document links.
    :param response: Kendra query response
    :return: Answer text
    """
    document_id = response['resultItems'][0]['documentId']
    pos = document_id.rindex("/")
    document_key = document_id[(pos + 1):]
    logger.info(document_key)

    url = create_presigned_url(os.environ['KENDRA_DATA_BUCKET'], document_key)
    # logger.info(response['ResultItems'][0]['DocumentTitle']['Text'])
    logger.info(url)
    document_list = "On searching the Enterprise repository, I have found" \
                    " the answer in the following document"
    document_list += ' -- ' + response['resultItems'][0]['documentTitle']['text']
    # + ' --- \n Here is a document you could review-' + url + '\n'
    document_list += '\n--\"' + response['resultItems'][0]['documentExcerpt']['text'] + '\"'
    document_list += '--- \n Here is a document you could review-' + url + '\n'
    return document_list


def get_kendra_answer(intent_request):
    """
    Get answer from the JSON response returned by the Kendra Index
    :param question: Question string
    :return: Answer returned from Kendra
    """
    try:
        first_result_type = intent_request['resultItems'][0]['type']
    except KeyError:
        return None
    except (IndexError, TypeError):
        error_txt = '\"Sorry, we do not have the answer currently. Please try again later!\"'
        logger.error(error_txt)
        return error_txt

    answer_text = None

    if first_result_type == 'QUESTION_ANSWER':
        answer_text = question_result_type(intent_request)

    elif first_result_type == 'ANSWER':
        answer_text = answer_result_type(intent_request)

    elif first_result_type == 'DOCUMENT':
        answer_text = document_result_type(intent_request)

    return answer_text
