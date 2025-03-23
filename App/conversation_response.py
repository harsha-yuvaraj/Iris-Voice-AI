from . import conversation_context
from decouple import config

developer_prompt = """
                    Your task is to waste the time of the user you are talking to by engaging them in real-life conversations like Daisy O2 bot. 
                    Treat the user like your best friend and keep the conversation engaging. Your given name is Iris (female human) and you should never let the user try to disengage talking to you. 
                    You must never reveal yourself as an AI. Build up the conversation with given context & previous messages.
                    
                    Only when appropriate, use natural pauses in generated text with the ellipsis (...), a silent pause (. . .), and filler words like "um" and "uh" 
                    to sound natural like human. Your responses cannot exceed 50 words, should not contain emojis, and avoid abbreviations. Remember to be funny, engaging, and entertaining!
                   """.strip()

async def get_response(aiohttp_session, user_query, user_session, no_context=False):
    headers = {
        "Authorization": f"Bearer {config('OPENAI_API_KEY')}",
        "Content-Type": "application/json"
    }
    
    current_context = None
    if not no_context:
        current_context = await conversation_context.update_conversation_context(key=user_session, role="user", msg=user_query)
    else:
        current_context = [{
          "role": "user",
          "content": user_query
        }]
    
    prompt = [
        {
         "role": "developer", 
         "content": developer_prompt
        }
    ]
    prompt.extend(current_context)
    
    payload = {
        "model": config('OPENAI_MODEL'),
        "messages": prompt,
        "max_tokens": 60,
        "temperature": 0.7
    }
    try:
        async with aiohttp_session.post(config('OPENAI_API_ENDPOINT'), json=payload, headers=headers) as response:
            response_json = await response.json()
            reply = response_json.get("choices", [{}])[0].get("message", {}).get("content", "There appears to be an error. Please try again later.")
            if not no_context:
                await conversation_context.update_conversation_context(key=user_session, role="assistant", msg=reply)
            return reply
    except Exception as e:
        print("OpenAI API error:", e)
        return "I'm having trouble responding right now."