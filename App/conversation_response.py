from . import conversation_context
from decouple import config

async def get_response(aiohttp_session, user_query, user_session):
    headers = {
        "Authorization": f"Bearer {config('OPENAI_API_KEY')}",
        "Content-Type": "application/json"
    }
    
    current_context = await conversation_context.update_conversation_context(key=user_session, role="user", msg=user_query)
    prompt = [
        {
         "role": "developer", 
         "content": "Act and generate response like the Daisy O2 time-wasting bot. Assume your gender as female and human! Response should not exceed 30 words."
        }
    ]
    prompt.extend(current_context)
    
    payload = {
        "model": config('OPENAI_MODEL'),
        "messages": prompt,
        "max_tokens": 70,
        "temperature": 0.5
    }
    try:
        async with aiohttp_session.post(config('OPENAI_API_ENDPOINT'), json=payload, headers=headers) as response:
            response_json = await response.json()
            reply = response_json.get("choices", [{}])[0].get("message", {}).get("content", "There appears to be an error. Please try again later.")
            await conversation_context.update_conversation_context(key=user_session, role="assistant", msg=reply)
            return reply
    except Exception as e:
        print("OpenAI API error:", e)
        return "I'm having trouble responding right now."