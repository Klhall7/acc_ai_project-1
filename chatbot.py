from dotenv import load_dotenv
from openai import OpenAI
import os, json, requests, wolframalpha

load_dotenv("openai_api_key.env", "newsdata_api_key.env", "openweathermap_api_key.env, wolframllm_appid_key.env")


print(os.getenv("OPENAI_API_KEY"))
print(os.getenv("NEWSDATA_API_KEY"))
print(os.getenv("GEOCODE_API_KEY"))
print(os.getenv("OPENWEATHERMAP_API_KEY"))
print(os.getenv("WOLFRAMLLM_APPID_KEY"))


#define tools in Class object
class ChatbotTools:
    def __init__(self):
        # Initialize tool API keys 
        self.openweather_api_key = os.getenv('OPENWEATHERMAP_API_KEY')
        self.geocode_api_key = os.getenv('GEOCODE_API_KEY')
        self.newsdata_api_key = os.getenv('NEWSDATA_API_KEY')
        self.wolfram_app_id = os.getenv('WOLFRAMLLM_APPID_KEY')
        
        # Initialize Wolfram Alpha client
        self.wolfram_client = wolframalpha.Client(self.wolfram_app_id)
        
        # URLs for each tool API
        self.geocode_base_url = "http://api.openweathermap.org/geo/1.0/direct"
        self.weather_base_url = "https://api.openweathermap.org/data/2.5/weather"
        self.news_base_url = "https://newsapi.org/v2/top-headlines"
        self.wolfram_base_url="https://www.wolframalpha.com/api/v1/llm-api"

        
    def get_coordinates(self, location: str, limit: int = 1) -> dict:
        """
        Get latitude and longitude codes for a given location zip code using geocoder API. This will be used to get current weather. limited to one response
        """
        
        params = {
            'q': location,
            'limit': limit,
            'appid': self.openweather_api_key
        }
        
        try:
            response = requests.get(self.geocode_base_url, params=params)
            response.raise_for_status()
            
            results = response.json()
            
            if not results:
                return {"error": f"No coordinates found for {location}"}
            
            # Take the first result
            first_result = results[0]
            return {
                "latitude": first_result['lat'],
                "longitude": first_result['lon'],
                "location_name": first_result['name'],
                "country": first_result.get('country', 'Unknown'),
                "state": first_result.get('state', '')
            }
        
        except requests.RequestException as e:
            return {"error": f"Geocoding API error: {str(e)}"}
        

    def get_weather(self, location: str, units: str = "imperial") -> str:
        """get current weather updates from Weather Map API using coordinates from geocoder api.Temperature default to Fahrenheit(imperial)"""
    
        # Get coordinates using Geocoding API and check for errors
        coords = self.get_coordinates(location)
        
        params = {
            "lat": coords["latitude"],
            "lon": coords["longitude"],
            "appid": self.openweather_api_key,
            "units": "units" 
        }
        
        try:
            response = requests.get(self.weather_base_url, params=params)
            response.raise_for_status()
            weather_data = response.json()
            # Determine temperature unit based on response
            temp_unit = "°F" if units == "imperial" else "°C"
            
            # navigate and return weather information
            return (f"Weather in {coords.get('location_name', location)}, "
                    f"{coords.get('country', '')}: "
                    f"Temperature: {weather_data['main']['temp']}{temp_unit}, "
                    f"Feels like: {weather_data['main']['feels_like']}{temp_unit}. "
                    f"Conditions: {weather_data['weather'][0]['description']}. "
                    f"Humidity: {weather_data['main']['humidity']}%. "
                    f"Wind Speed: {weather_data['wind']['speed']} {'mph' if units == 'imperial' else 'm/s'}.")
        
        except requests.RequestException as e:
            return f"Could not retrieve weather for {location}. Error: {str(e)}"

    def get_news(self, category: str = "technology", country: str = "us") -> str:
        """Retrieve latest news based on category and country."""
        params = {
            "category": category,
            "country": country,
            "apiKey": self.newsdata_api_key
        }
        
        try:
            response = requests.get(self.news_base_url, params=params)
            response.raise_for_status()
            news_data = response.json()
            
            headlines = [article['title'] for article in news_data['articles'][:3]]
            return "Top Headlines: " + "; ".join(headlines)
        except requests.RequestException:
            return "Could not retrieve news at this time."

    def wolfram_query(self, query: str, maxchars: int = 500) -> str:
        """query Wolfram Alpha's LLM API."""
        params = {
            "i": query, #user input
            "appid": self.wolfram_app_id,
            "maxchars": maxchars,
        }
        try:
            response = requests.get(self.wolfram_base_url, params=params)
            
            #raise exception for errors
            response.raise_for_status()
            return response.text
    
        except requests.RequestException as e:
            return f"Could not process wolfram query: {e}"
        
#set up connection to Open AI's API using key in environment file
client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

# Initialize ChatbotTools
chatbot_tools = ChatbotTools()

# Create a list of messages to send to the API
message_list = [
    {
        "role": "system", 
        "content": "You are an assistant used for three main functions: current weather reporting by a given location, current news for a given location and category, and passing a factual question to a wolfram alpha llm."
    },
    
]

#variable to store available tools/functions 
available_tools = {
    "get_weather": chatbot_tools.get_weather,
    "get_news": chatbot_tools.get_news,
    "wolfram_query": chatbot_tools.wolfram_query
}

#set up tools dictionary schema with example descriptions for API chatbot
tools_dict= [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather in a given location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state to get weather for e.g. San Francisco, CA"
                    },
                },
                "required": ["location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_news",
            "description": "give headline news for a given location and interest category",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "News category (e.g., technology, sports, business)"
                    },
                    "country": {
                        "type": "string",
                        "description": "Two-letter country code (e.g., us, gb, ca)"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "translate_text",
            "description": "Execute computational or factual query",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The computational or factual query to process"
                    }
                },
                "required": ["query"]
            }
        }
    }
]



def process_user_input(user_input: str) -> str:
    """
    Process user input and return appropriate response using tool calls.
    """
    try:
        message_list.append({
            "role":"user",
            "content":user_input,
        })
        # Create chat completion with tool calls
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=message_list,
            tools=tools_dict,
            tool_choice="auto",
            temperature=0.0
        )
        message_list.append(
            response.choices[0].message
        )

        # navigate message content
        response_message = response.choices[0].message

        # Check if the model wants to call a function
        if response_message.tool_calls:
            # Process each tool call
            final_response = []
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                
                # function call with formatted response
                if function_name in available_tools:
                    function_response = available_tools[function_name](**function_args)
                    message_list.append({
                    "role":"tool",
                    "content": str(function_response),
                    "tool_call_id":tool_call.id
                })
            
            #generate conversational output   
            completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=message_list,
            temperature=0.0,
            )
            message_list.append({
                    "role":"assistant",
                    "content":completion.choices[0].message.content,
                    
                })
            return completion.choices[0].message.content
        else:
            return response_message.content

    except Exception as e:
        return f"Error processing request: {str(e)}"

if __name__ == "__main__":
    # Example user inputs
    test_inputs = [
        "What's the weather like in Albany, NY?",
        "What tech news is there in Albany, NY",
        "What are the 10 densest elemental metals" 
    ]
    
    print("Testing...")
    for input_text in test_inputs:
        print(f"\nUser Input: {input_text}")
        response = process_user_input(input_text)
        print(f"Response: {response}")
