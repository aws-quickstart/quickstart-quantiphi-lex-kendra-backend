import logging
import json
import helpers
import config

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info('<help_desk_bot>> Lex event info = ' + json.dumps(event))

    session_attributes = event.get('sessionAttributes', None)

    if session_attributes is None:
        session_attributes = {}

    logger.debug('<<help_desk_bot> lambda_handler: session_attributes = ' + json.dumps(session_attributes))
    
    currentIntent = event.get('currentIntent', None)
    if currentIntent is None:
        response_string = 'Sorry, I didn\'t understand. Could you please repeat?'
        return helpers.close(session_attributes, 'Fulfilled', {'contentType': 'CustomPayload','content': response_string})
    intentName = currentIntent.get('name', None)
    if intentName is None:
        response_string = 'Sorry, I didn\'t understand. Could you please repeat?'
        return helpers.close(session_attributes, 'Fulfilled', {'contentType': 'CustomPayload','content': response_string})

    # see HANDLERS dict at bottom
    if HANDLERS.get(intentName, False):
        return HANDLERS[intentName]['handler'](event, session_attributes)   # dispatch to the event handler
    else:
        response_string = "The intent " + intentName + " is not yet supported."
        return helpers.close(session_attributes, 'Fulfilled', {'contentType': 'CustomPayload','content': response_string})


# def make_appointment_intent_handler(intent_request, session_attributes):
#     session_attributes['fallbackCount'] = '0'

#     try:
#         slot_values = helpers.get_latest_slot_values(intent_request, session_attributes)
#     except config.SlotError as err:
#         return helpers.close(session_attributes, 'Fulfilled', {'contentType': 'CustomPayload','content': str(err)})   

#     logger.debug('<<help_desk_bot>> make_appointment_intent_handler(): slot_values = %s', json.dumps(slot_values))

#     if slot_values.get('time', None) is None:
#         response_string = "Please check the bot configuration for slot {time}."
#     elif slot_values.get('problem', None) is None:
#         response_string = "Please check the bot configuration for slot {problem}."
#     else:
#         response_string = "Got it, we'll see you then to take a look at your {}.".format(slot_values['problem'])

#     return helpers.close(session_attributes, 'Fulfilled', {'contentType': 'CustomPayload','content': response_string})   


# def check_appointment_intent_handler(intent_request, session_attributes):
#     session_attributes['fallbackCount'] = '0'

#     try:
#         slot_values = helpers.get_latest_slot_values(intent_request, session_attributes)
#     except config.SlotError as err:
#         return helpers.close(session_attributes, 'Fulfilled', {'contentType': 'CustomPayload','content': str(err)})   

#     logger.debug('<<help_desk_bot>> check_appointment_intent_handler(): slot_values = %s', json.dumps(slot_values))

#     if slot_values.get('time', None) is None:
#         response_string = "We don't have a time set up yet."
#     elif slot_values.get('problem', None) is None:
#         response_string = "We don't have a problem identified yet."
#     else:
#         response_string = "Hi, we will see you at {} today to fix your {}.".format(slot_values['time'], slot_values['problem'])

#     return helpers.close(session_attributes, 'Fulfilled', {'contentType': 'CustomPayload','content': response_string})   


# def hello_intent_handler(intent_request, session_attributes):
#     # clear out session attributes to start new
#     session_attributes = {}

#     response_string = "Hello! How can we help you today? You can ask a question or make an appointment with IT Support."
    
#     return helpers.close(session_attributes, 'Fulfilled', {'contentType': 'CustomPayload','content': response_string})   


# def goodbye_intent_handler(intent_request, session_attributes):
#     # clear out session attributes to start over
#     session_attributes = {}

    # response_string = "Thanks! Have a great rest of your day."

    # return helpers.close(session_attributes, 'Fulfilled', {'contentType': 'CustomPayload','content': response_string})   


def fallback_intent_handler(intent_request, session_attributes):
    session_attributes['fallbackCount'] = '0'
    fallbackCount = helpers.increment_counter(session_attributes, 'fallbackCount')
    
    try:
        slot_values = helpers.get_latest_slot_values(intent_request, session_attributes)
    except config.SlotError as err:
        return helpers.close(session_attributes, 'Fulfilled', {'contentType': 'CustomPayload','content': str(err)})   

    logger.debug('<<help_desk_bot>> fallback_intent_handler(): slot_values = %s', json.dumps(slot_values))
    # response_string = "Thanks! Have a great day."

    # return helpers.close(session_attributes, 'Fulfilled', {'contentType': 'CustomPayload','content': response_string})   
    query_string = ""
    if intent_request.get('inputTranscript', None) is not None:
        query_string += intent_request['inputTranscript']

    logger.debug('<<help_desk_bot>> fallback_intent_handler(): calling get_kendra_answer(query="%s")', query_string)
        
    kendra_response = helpers.get_kendra_answer(query_string)
    if kendra_response is None:
        response = "Sorry, I was not able to understand your question. Could you please repeat?"
        return helpers.close(session_attributes, 'Fulfilled', {'contentType': 'CustomPayload','content': response})
    else:
        logger.debug('<<help_desk_bot>> "fallback_intent_handler(): kendra_response = %s', kendra_response)
        return helpers.close(session_attributes, 'Fulfilled', {'contentType': 'CustomPayload','content': kendra_response})


# list of intent handler functions for the dispatch proccess
HANDLERS = {
    # 'help_desk_hello':              {'handler': hello_intent_handler},
    # 'help_desk_make_appointment':   {'handler': make_appointment_intent_handler},
    # 'help_desk_check_appointment':  {'handler': check_appointment_intent_handler},
    # 'help_desk_goodbye':            {'handler': goodbye_intent_handler},
    'lex_kendra_hr_fallback':           {'handler': fallback_intent_handler},
    'Fallback':           {'handler': fallback_intent_handler},
    'Fallbacktest':           {'handler': fallback_intent_handler}
}
