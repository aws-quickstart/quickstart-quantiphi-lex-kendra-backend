"""
Generates Lex Bot response by triggering intent handler according to the intent passed.
"""

import logging
import json
import helpers
import config

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, _):
    """
    Lambda function handler. Triggers applicable intent handler and returns Lex bot response.
    :param event: Event body
    :param _: Context (not used)
    :return: Lex bot response
    """
    logger.info('<help_desk_bot>> Lex event info = %s', json.dumps(event))

    session_attributes = event.get('sessionAttributes', None)

    if session_attributes is None:
        session_attributes = {}

    logger.debug('<<help_desk_bot> lambda_handler: session_attributes = %s',
                 json.dumps(session_attributes))

    current_intent = event.get('currentIntent', None)
    if current_intent is None:
        response_string = 'Sorry, I didn\'t understand. Could you please repeat?'
        return helpers.close(session_attributes, 'Fulfilled',
                             {'contentType': 'CustomPayload', 'content': response_string})
    intent_name = current_intent.get('name', None)
    if intent_name is None:
        response_string = 'Sorry, I didn\'t understand. Could you please repeat?'
        return helpers.close(session_attributes, 'Fulfilled',
                             {'contentType': 'CustomPayload', 'content': response_string})

    # see HANDLERS dict at bottom
    if HANDLERS.get(intent_name, False):
        return HANDLERS[intent_name]['handler'](event, session_attributes)
        # dispatch to the event handler
    response_string = "The intent " + intent_name + " is not yet supported."
    return helpers.close(session_attributes, 'Fulfilled',
                         {'contentType': 'CustomPayload', 'content': response_string})


def kendra_search_intent_handler(intent_request, session_attributes):
    """
    Fallback intent handler. Generates response by querying Kendra index.
    :param intent_request: Request
    :param session_attributes: Session attributes
    :return: Response string
    """
    session_attributes['fallbackCount'] = '0'
    # fallbackCount = helpers.increment_counter(session_attributes, 'fallbackCount')

    try:
        slot_values = helpers.get_latest_slot_values(intent_request, session_attributes)
    except config.SlotError as err:
        return helpers.close(session_attributes, 'Fulfilled',
                             {'contentType': 'CustomPayload', 'content': str(err)})

    logger.debug('<<help_desk_bot>> kendra_search_intent_handler(): slot_values = %s',
                 json.dumps(slot_values))

    query_string = ""
    if intent_request.get('inputTranscript', None) is not None:
        query_string += intent_request['inputTranscript']

    logger.debug(
        '<<help_desk_bot>> kendra_search_intent_handler(): calling get_kendra_answer(query="%s")',
        query_string)

    kendra_response = helpers.get_kendra_answer(intent_request['kendraResponse'])
    if kendra_response is None:
        response = "Sorry, I was not able to understand your question. Could you please repeat?"
        return helpers.close(session_attributes,
                             'Fulfilled', {'contentType': 'CustomPayload', 'content': response})
    logger.debug(
        '<<help_desk_bot>> "kendra_search_intent_handler(): kendra_response = %s',
        str(kendra_response))
    return helpers.close(session_attributes, 'Fulfilled',
                         {'contentType': 'CustomPayload', 'content': kendra_response})


HANDLERS = {
    'Kendra_Search_Intent': {'handler': kendra_search_intent_handler}
}
