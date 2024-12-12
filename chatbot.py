from dotenv import load_dotenv
from openai import OpenAI
import os, json, requests, wolframalpha

load_dotenv("api_keys.env")

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
        self.weather_base_url = "https://api.openweathermap.org/data/2.5/weather"
        self.news_base_url = "https://newsdata.io/api/1/latest"
        self.wolfram_base_url="https://www.wolframalpha.com/api/v1/llm-api"

    def get_weather(self, location: str, units: str = "imperial") -> str:
        """
        Retrieves current weather forecast based on a given geographical location. Includes message for error handling 
        Parameters/Args:
            location ("q"): expects string; city and state to get weather for e.g. San Francisco, California. Note the api does not like shortcodes for states ie. NY for New York
            appid: unique API key required to access information;stored in .env file
            units: expects string;  temperature measurement. Default set to imperial for fahrenheit.
        Returns: dictionary containing get current weather updates. Temperature default to Fahrenheit(imperial). Json is then navigated through for a readable result
        """
        params = {
            "q": location, 
            "appid": self.openweather_api_key,
            "units": units 
        }
        
        try:
            response = requests.get(self.weather_base_url, params=params)
            response.raise_for_status()
            weather_data = response.json()
            
            #have AI read through data and choose a response 
            return weather_data
            
        except Exception as e:
            return f"Error retrieving weather for {location}: {str(e)}"

    def get_news(self, category: str , country: str = "us", size = 5) -> str:
        """ 
        Retrieves latest news based on category and location. 
        Parameters/Args:
            category: expects string; News category. Default set to technology for now.
            country: expects string; Country code. Default set to US.
            apiKey: unique API key required to access information;stored in .env file
            size: number of articles in response, limited to 10 for free tier
        Returns: dictionary containing top headlines. JSON info is joined as a string for readability
        """
        params = {
            "apiKey": self.newsdata_api_key,
            "category": category,
            "country": country,
            "size": size,
        }
        
        try:
            response = requests.get(self.news_base_url, params=params)
            response.raise_for_status()
            news_data = response.json()
            
            return news_data
        
        except requests.RequestException as e:
            return f"Could not retrieve {category} news. Error: {str(e)}"

    def wolfram_query(self, query: str, maxchars: int = 500) -> str:
        """
        Receives factual information from Wolfram Alpha's LLM when given an input query. Includes error handling for no result or failure in processing.
        Parameters/Args:
            i: expects string; user input query/ question. 
            appid: unique API key required to access information;stored in .env file
            maxchars: expects integer; character limit on response, set to 500 for simplicity/ time
        Returns: readable information results from the LLM API with a link back to the full Wolfram|Alpha website results."""
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
        "content": "You are an assistant used for three main functions: current weather reporting by a given location, current news for a given region and optional category, and passing a factual question to a wolfram alpha llm."
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
                        "description": "The city and state to get weather for e.g. San Francisco, California. State must be written out"
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
                        "description": "news articles for a specific category (e.g., technology, sports, business)"
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
            "name": "wolfram_query",
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
    Processes user input through Open AI's chatbot model and returns appropriate response using appropriate tool calls as needed. Responses are appended and prompt loops for conversational feel. Added argument parsing and detailed error messages for debugging
    """
    try:
        message_list.append({
            "role":"user",
            "content":user_input,
        })
        # Create chat completion with tool calls
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=message_list,
                tools=tools_dict,
                tool_choice="auto",
                temperature=0.0
            )
        except Exception as api_error:
            return f"OpenAI API Error: {str(api_error)}"
        
        message_list.append(
            response.choices[0].message
        )

        # navigate message content
        response_message = response.choices[0].message
        
        # Check if the model wants to call a function
        if response_message.tool_calls:
            # Process each tool call
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                
                try:
                    # Parse arguments safely
                    function_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    return f"Error: Invalid JSON arguments for function {function_name}"
                
                # Detailed function call error handling
                try:
                    # Check if function exists in available tools
                    if function_name not in available_tools:
                        return f"Error: Function {function_name} not found in available tools"
                    
                    # Call function with arguments
                    function_response = available_tools[function_name](**function_args)
                    
                    # Append tool response to message list
                    message_list.append({
                        "role": "tool",
                        "content": str(function_response),
                        "tool_call_id": tool_call.id
                    })
                
                except TypeError as type_error:
                    return f"Error: Incorrect arguments for {function_name}. Details: {str(type_error)}"
                except Exception as func_error:
                    return f"Error executing {function_name}: {str(func_error)}"
            
            # Generate conversational output
            try:
                completion = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=message_list,
                    temperature=0.0,
                )
                
                message_list.append({
                    "role": "assistant",
                    "content": completion.choices[0].message.content,
                })
                
                return completion.choices[0].message.content
            
            except Exception as completion_error:
                return f"Error generating final response: {str(completion_error)}"
        
        else:
            return response_message.content

    except Exception as unexpected_error:
        return f"Unexpected error processing request: {str(unexpected_error)}"

if __name__ == "__main__":
    # Example user inputs
    test_inputs = [
        "What's the weather like in Albany, New York?",
        "Top technology news",
        "10 densest elemental metals" 
    ]
    
    print("Testing...")
    for input_text in test_inputs:
        print(f"\nUser Input: {input_text}")
        response = process_user_input(input_text)
        print(f"Response: {response}")
